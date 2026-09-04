from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app import models
from app.ai.condition_safety import USER_ATTESTED_PROVENANCE

# The order the account manager works through, so a resumed session can name the
# first step that is still outstanding.
ONBOARDING_STEPS = ("self_profile", "health_context", "conditions", "medications")
ATTESTED_CATEGORIES = ("condition", "medication")


@dataclass(frozen=True)
class OnboardingState:
    status: str
    next_step: str | None
    completed_steps: tuple[str, ...]
    self_profile: models.Profile | None


def self_profile(db: Session, *, account_id: str) -> models.Profile | None:
    return (
        db.query(models.Profile)
        .filter(models.Profile.account_id == account_id, models.Profile.relationship == "self")
        .one_or_none()
    )


def evaluate_onboarding(db: Session, *, account: models.Account) -> OnboardingState:
    """Derive onboarding progress from the rows each step leaves behind."""

    profile = self_profile(db, account_id=account.id)
    completed = []
    if profile is not None:
        completed.append("self_profile")
        if _has_health_context(db, profile=profile):
            completed.append("health_context")
        if profile.conditions_declared_at is not None:
            completed.append("conditions")
        if profile.medications_declared_at is not None:
            completed.append("medications")

    outstanding = [step for step in ONBOARDING_STEPS if step not in completed]
    if not outstanding:
        status = "completed"
    elif not completed:
        status = "not_started"
    else:
        status = "in_progress"
    return OnboardingState(
        status=status,
        next_step=outstanding[0] if outstanding else None,
        completed_steps=tuple(step for step in ONBOARDING_STEPS if step in completed),
        self_profile=profile,
    )


def refresh_onboarding_status(db: Session, *, account: models.Account) -> OnboardingState:
    """Recompute and persist onboarding status after a step changes."""

    state = evaluate_onboarding(db, account=account)
    if account.onboarding_status != state.status:
        account.onboarding_status = state.status
        db.commit()
        db.refresh(account)
    return state


def ensure_self_profile(
    db: Session, *, account_id: str, display_name: str, sex: str | None
) -> models.Profile:
    """Create the account's one `self` profile, or update the existing one."""

    profile = self_profile(db, account_id=account_id)
    if profile is None:
        profile = models.Profile(
            account_id=account_id,
            display_name=display_name,
            relationship="self",
            sex=sex,
        )
        db.add(profile)
    else:
        profile.display_name = display_name
        profile.sex = sex
    db.commit()
    db.refresh(profile)
    return profile


def declare_attested_memory(
    db: Session,
    *,
    account_id: str,
    profile: models.Profile,
    category: str,
    entries: list[tuple[str, dict]],
    attested_by_identity_id: str,
) -> datetime:
    """Replace a profile's attested facts for one category with the declared set.

    An empty declaration is meaningful: it records that the account manager
    reported no current conditions or medications rather than skipping the step.
    Returns the declaration time.
    """

    declared_at = datetime.now(UTC)
    prior = (
        db.query(models.MemoryFact)
        .filter(
            models.MemoryFact.account_id == account_id,
            models.MemoryFact.profile_id == profile.id,
            models.MemoryFact.provenance == USER_ATTESTED_PROVENANCE,
            models.MemoryFact.category == category,
            models.MemoryFact.is_active.is_(True),
        )
        .all()
    )
    for fact in prior:
        fact.is_active = False
        fact.superseded_at = declared_at

    facts = [
        models.MemoryFact(
            account_id=account_id,
            profile_id=profile.id,
            attested_by_identity_id=attested_by_identity_id,
            provenance=USER_ATTESTED_PROVENANCE,
            category=category,
            title=title,
            details=details,
        )
        for title, details in entries
    ]
    for fact in facts:
        db.add(fact)

    if category == "condition":
        profile.conditions_declared_at = declared_at
    else:
        profile.medications_declared_at = declared_at
    db.commit()
    return declared_at


def attested_facts(
    db: Session, *, account_id: str, profile_id: str, category: str
) -> list[models.MemoryFact]:
    return (
        db.query(models.MemoryFact)
        .filter(
            models.MemoryFact.account_id == account_id,
            models.MemoryFact.profile_id == profile_id,
            models.MemoryFact.provenance == USER_ATTESTED_PROVENANCE,
            models.MemoryFact.category == category,
            models.MemoryFact.is_active.is_(True),
        )
        .order_by(models.MemoryFact.created_at.asc())
        .all()
    )


def _has_health_context(db: Session, *, profile: models.Profile) -> bool:
    """Onboarding needs both an age and a weight, which may arrive separately."""

    rows = (
        db.query(
            models.ProfileHealthContext.reported_age, models.ProfileHealthContext.entered_weight
        )
        .filter(models.ProfileHealthContext.profile_id == profile.id)
        .all()
    )
    return any(age is not None for age, _ in rows) and any(weight is not None for _, weight in rows)
