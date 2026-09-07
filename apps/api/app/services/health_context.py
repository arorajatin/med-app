from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app import models

# How long a reported value stays fresh. These are recency prompts only: a stale
# value keeps its reported date and is never re-derived, replaced, or judged.
AGE_REFRESH_MONTHS = 12
WEIGHT_REFRESH_MONTHS = 6


@dataclass(frozen=True)
class HealthContextSummary:
    """The latest reported age and weight for one profile, with their freshness."""

    profile_id: str
    reported_age: int | None
    age_reported_at: datetime | None
    age_refresh_due: bool
    entered_weight: Decimal | None
    weight_unit: str | None
    normalized_weight_kg: Decimal | None
    weight_reported_at: datetime | None
    weight_refresh_due: bool


def latest_health_context(
    db: Session, *, profile_id: str, now: datetime | None = None
) -> HealthContextSummary:
    """Read the newest reported age and weight, which may come from different rows."""

    moment = now or datetime.now(UTC)
    age_row = (
        db.query(models.ProfileHealthContext)
        .filter(
            models.ProfileHealthContext.profile_id == profile_id,
            models.ProfileHealthContext.reported_age.isnot(None),
        )
        .order_by(models.ProfileHealthContext.age_reported_at.desc())
        .first()
    )
    weight_row = (
        db.query(models.ProfileHealthContext)
        .filter(
            models.ProfileHealthContext.profile_id == profile_id,
            models.ProfileHealthContext.entered_weight.isnot(None),
        )
        .order_by(models.ProfileHealthContext.weight_reported_at.desc())
        .first()
    )
    return HealthContextSummary(
        profile_id=profile_id,
        reported_age=None if age_row is None else age_row.reported_age,
        age_reported_at=None if age_row is None else age_row.age_reported_at,
        age_refresh_due=refresh_due(
            None if age_row is None else age_row.age_reported_at,
            months=AGE_REFRESH_MONTHS,
            now=moment,
        ),
        entered_weight=None if weight_row is None else weight_row.entered_weight,
        weight_unit=None if weight_row is None else weight_row.weight_unit,
        normalized_weight_kg=None if weight_row is None else weight_row.normalized_weight_kg,
        weight_reported_at=None if weight_row is None else weight_row.weight_reported_at,
        weight_refresh_due=refresh_due(
            None if weight_row is None else weight_row.weight_reported_at,
            months=WEIGHT_REFRESH_MONTHS,
            now=moment,
        ),
    )


def refresh_due(reported_at: datetime | None, *, months: int, now: datetime) -> bool:
    """A value with no reported date is not yet recorded, so nothing is due."""

    if reported_at is None:
        return False
    return now >= _add_calendar_months(_as_utc(reported_at), months)


def _add_calendar_months(moment: datetime, months: int) -> datetime:
    """Advance by calendar months, clamping to the last day of a shorter month."""

    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    day = min(moment.day, monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def _as_utc(moment: datetime) -> datetime:
    """SQLite returns these timestamps without an offset; they were stored as UTC."""

    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)
