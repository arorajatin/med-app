"""Reconcile abandoned source writes using only the constrained cleanup role."""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.config import Settings
from app.data_boundary import validate_data_settings
from app.database import normalize_database_url
from app.supabase_storage import StorageUnavailable, SupabasePrivateStorage


def reconcile_uploads(settings: Settings, *, limit: int = 100) -> tuple[int, int]:
    # Cleanup remains available when new uploads are disabled during rollback.
    if settings.data_backend != "supabase" or not settings.supabase_cleanup_database_url:
        raise RuntimeError("Configure the Supabase cleanup workload connection.")
    validate_data_settings(settings, require_admission=False, database_role="med_app_cleanup")
    url = make_url(normalize_database_url(settings.supabase_cleanup_database_url))
    engine = create_engine(url, hide_parameters=True, connect_args={"prepare_threshold": None})
    completed = failed = 0
    try:
        with engine.begin() as connection:
            status = connection.execute(
                text("SELECT med_app_private.boundary_status()")
            ).scalar_one()
            if not (
                status["login"] == "med_app_cleanup"
                and status["roles_safe"]
                and status["project_ref"] == settings.supabase_project_ref
                and status["region"] == "ap-southeast-1"
                and status["bucket_private"]
            ):
                raise RuntimeError("Cleanup database boundary failed preflight.")
            ids = (
                connection.execute(
                    text("SELECT med_app_private.due_cleanup_ids(:limit)"), {"limit": limit}
                )
                .scalars()
                .all()
            )
        for work_id in ids:
            with engine.begin() as connection:
                claim = connection.execute(
                    text("SELECT med_app_private.claim_cleanup(:id)"), {"id": work_id}
                ).scalar_one()
            if claim is None:
                continue

            def token(operation: str, key: str, claimed=claim) -> str:
                if operation != "delete" or key != claimed["object_key"]:
                    raise PermissionError("Cleanup is restricted to its claimed object.")
                return str(claimed["token"])

            storage = SupabasePrivateStorage(
                settings,
                account_id=claim["account_id"],
                issue_token=token,
                register_cleanup=lambda key: None,
            )
            try:
                if claim["bucket"] != settings.supabase_storage_bucket:
                    raise StorageUnavailable()
                storage.delete_object(claim["object_key"])
            except StorageUnavailable:
                failed += 1
                continue
            with engine.begin() as connection:
                connection.execute(
                    text("SELECT med_app_private.complete_cleanup(:id)"), {"id": work_id}
                )
            completed += 1
    finally:
        engine.dispose()
    return completed, failed


if __name__ == "__main__":
    try:
        # Load only the cleanup process environment, never the API's local .env.
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        done, failures = reconcile_uploads(settings)
    except Exception:
        raise SystemExit(
            "Storage cleanup failed. Check workload configuration and connectivity."
        ) from None
    print(f"cleaned={done} retry_pending={failures}")
    raise SystemExit(1 if failures else 0)
