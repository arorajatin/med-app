from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app import models


@dataclass(frozen=True)
class AccountContext:
    account: models.Account
    identity: models.AuthIdentity


def resolve_account_context(
    db: Session,
    *,
    provider: str,
    provider_subject: str,
    upstream_provider: str | None = None,
    email: str | None = None,
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
        _refresh_identity_provenance(
            db, identity=identity, upstream_provider=upstream_provider, email=email
        )
        return AccountContext(account=account, identity=identity)

    account = models.Account()
    db.add(account)
    db.flush()
    identity = models.AuthIdentity(
        account_id=account.id,
        provider=provider,
        provider_subject=provider_subject,
        upstream_provider=upstream_provider,
        email=email,
        verified_at=datetime.now(UTC),
    )
    db.add(identity)
    db.commit()
    db.refresh(account)
    db.refresh(identity)
    return AccountContext(account=account, identity=identity)


def _refresh_identity_provenance(
    db: Session,
    *,
    identity: models.AuthIdentity,
    upstream_provider: str | None,
    email: str | None,
) -> None:
    """Keep the latest verified sign-in method and address on a known identity."""

    changed = False
    if upstream_provider is not None and identity.upstream_provider != upstream_provider:
        identity.upstream_provider = upstream_provider
        changed = True
    if email is not None and identity.email != email:
        identity.email = email
        changed = True
    if changed:
        db.commit()
        db.refresh(identity)


def latest_consent(db: Session, *, account_id: str) -> models.ConsentEvidence | None:
    return (
        db.query(models.ConsentEvidence)
        .filter(models.ConsentEvidence.account_id == account_id)
        .order_by(models.ConsentEvidence.accepted_at.desc(), models.ConsentEvidence.id.desc())
        .first()
    )
