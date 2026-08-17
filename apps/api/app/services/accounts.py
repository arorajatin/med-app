from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app import models


@dataclass(frozen=True)
class AccountContext:
    account: models.Account
    identity: models.AuthIdentity


def resolve_account_context(
    db: Session, *, provider: str, provider_subject: str
) -> AccountContext:
    """Resolve a verified identity, creating its application account idempotently."""

    identity = (
        db.query(models.AuthIdentity)
        .filter(
            models.AuthIdentity.provider == provider,
            models.AuthIdentity.provider_subject == provider_subject,
        )
        .one_or_none()
    )
    if identity is not None:
        account = db.query(models.Account).filter(models.Account.id == identity.account_id).one()
        return AccountContext(account=account, identity=identity)

    account = models.Account()
    db.add(account)
    db.flush()
    identity = models.AuthIdentity(
        account_id=account.id,
        provider=provider,
        provider_subject=provider_subject,
        verified_at=datetime.now(UTC),
    )
    db.add(identity)
    db.commit()
    db.refresh(account)
    db.refresh(identity)
    return AccountContext(account=account, identity=identity)


def latest_consent(db: Session, *, account_id: str) -> models.ConsentEvidence | None:
    return (
        db.query(models.ConsentEvidence)
        .filter(models.ConsentEvidence.account_id == account_id)
        .order_by(models.ConsentEvidence.accepted_at.desc(), models.ConsentEvidence.id.desc())
        .first()
    )
