from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai.base import Extractor
from app.ai.mock_provider import MockExtractor
from app.auth import get_current_user
from app.config import Settings, get_settings
from app.database import get_db
from app.models import StorageCleanupIntent
from app.schemas import CurrentUser
from app.services.accounts import resolve_account_context
from app.storage import LocalPrivateStorage, PrivateStorage
from app.supabase_storage import SupabasePrivateStorage


def get_request_db(user: CurrentUser = Depends(get_current_user)) -> Generator[Session, None, None]:
    yield from get_db(verified_subject=user.id)


def get_storage(
    settings: Settings = Depends(get_settings),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_request_db),
) -> PrivateStorage:
    if settings.data_backend == "local":
        return LocalPrivateStorage(settings)
    if settings.data_backend != "supabase":
        raise RuntimeError("Unknown data backend.")
    context = resolve_account_context(
        db,
        provider="supabase",
        provider_subject=user.id,
        upstream_provider=user.upstream_provider,
        email=user.email,
    )
    account_id = context.account.id

    def issue_token(operation: str, object_key: str) -> str:
        return db.execute(
            text("SELECT med_app_private.issue_storage_token(:operation, :object_key)"),
            {"operation": operation, "object_key": object_key},
        ).scalar_one()

    def register_cleanup(object_key: str) -> None:
        # This transaction survives rollback of the upload metadata transaction.
        with contextmanager(get_db)(verified_subject=user.id) as cleanup_db:
            cleanup_db.add(
                StorageCleanupIntent(
                    account_id=account_id,
                    object_key=object_key,
                    storage_bucket=settings.supabase_storage_bucket,
                    reconcile_after=datetime.now(UTC) + timedelta(hours=1),
                )
            )
            cleanup_db.commit()

    return SupabasePrivateStorage(
        settings,
        account_id=account_id,
        issue_token=issue_token,
        register_cleanup=register_cleanup,
    )


def get_extractor(settings: Settings = Depends(get_settings)) -> Extractor | None:
    if settings.data_backend == "supabase":
        return None
    if settings.extraction_provider == "mock":
        return MockExtractor()
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Extraction provider is not implemented: {settings.extraction_provider}",
    )
