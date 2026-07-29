import json
from collections.abc import Generator
from pathlib import Path
from uuid import UUID

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import Depends
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.schemas import CurrentUser


class Base(DeclarativeBase):
    pass


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_CONFIG_PATH = PROJECT_ROOT / "alembic.ini"


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None

AUTHENTICATED_DATABASE_ROLE = "authenticated"
SESSION_USER_ID_KEY = "supabase_user_id"
SESSION_DATABASE_ROLE_KEY = "supabase_database_role"
USER_OWNED_TABLES = {
    "profiles",
    "medical_records",
    "record_files",
    "extraction_jobs",
    "extracted_fields",
    "memory_facts",
    "appointments",
    "appointment_checklist_items",
    "appointment_reviews",
}


def _engine_url(database_url: str):
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+psycopg")
    return url


def configure_database(
    database_url: str | None = None,
    *,
    settings: Settings | None = None,
) -> None:
    global _engine, _SessionLocal

    settings = settings or get_settings()
    url = _engine_url(database_url or settings.database_url)
    connect_args: dict[str, object] = {}
    if url.get_backend_name() == "sqlite":
        connect_args["check_same_thread"] = False
    elif settings.is_production:
        connect_args.update(
            connect_timeout=settings.database_connect_timeout_seconds,
            sslmode=settings.database_ssl_mode,
        )

    if _engine is not None:
        _engine.dispose()

    _engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def dispose_database() -> None:
    global _engine, _SessionLocal

    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_engine() -> Engine:
    if _engine is None:
        configure_database()
    return _engine


def bootstrap_test_database() -> None:
    if get_settings().environment != "test":
        raise RuntimeError("Metadata schema bootstrap is only allowed when ENVIRONMENT=test.")

    from app import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def _set_local_authenticated_role(connection: Connection) -> None:
    connection.exec_driver_sql(f"SET LOCAL ROLE {AUTHENTICATED_DATABASE_ROLE}")


def _apply_supabase_identity(
    session: Session,
    transaction,
    connection: Connection,
) -> None:
    user_id = session.info.get(SESSION_USER_ID_KEY)
    if user_id is None or connection.dialect.name != "postgresql":
        return

    database_role = session.info.get(
        SESSION_DATABASE_ROLE_KEY,
        AUTHENTICATED_DATABASE_ROLE,
    )
    if database_role != AUTHENTICATED_DATABASE_ROLE:
        raise RuntimeError("Only the authenticated Supabase database role is allowed.")

    _set_local_authenticated_role(connection)
    claims = json.dumps(
        {"role": AUTHENTICATED_DATABASE_ROLE, "sub": user_id},
        separators=(",", ":"),
    )
    connection.execute(
        text(
            "SELECT "
            "set_config('request.jwt.claim.sub', :user_id, true), "
            "set_config('request.jwt.claims', :claims, true)"
        ),
        {"user_id": user_id, "claims": claims},
    )


event.listen(Session, "after_begin", _apply_supabase_identity)


def bind_database_identity(db: Session, *, user_id: str) -> None:
    try:
        normalized_user_id = str(UUID(user_id))
    except ValueError as exc:
        raise RuntimeError("Supabase database identity must be a valid UUID.") from exc

    if db.in_transaction():
        raise RuntimeError("Database identity must be bound before a transaction begins.")

    db.info[SESSION_USER_ID_KEY] = normalized_user_id
    db.info[SESSION_DATABASE_ROLE_KEY] = AUTHENTICATED_DATABASE_ROLE


def require_safe_production_database_role() -> None:
    settings = get_settings()
    if not settings.is_production:
        return

    engine = get_engine()
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Production persistence must use PostgreSQL.")

    with engine.begin() as connection:
        session_role = connection.execute(
            text(
                "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = session_user"
            )
        ).one_or_none()
        if session_role is None:
            raise RuntimeError("Unable to validate the production database role.")
        if session_role.rolsuper or session_role.rolbypassrls:
            raise RuntimeError(
                "Production DATABASE_URL must not use a superuser or BYPASSRLS role."
            )

        table_security = {
            row.relname: row
            for row in connection.execute(
                text(
                    """
                    SELECT
                        c.relname,
                        pg_get_userbyid(c.relowner) AS owner_name,
                        c.relrowsecurity,
                        c.relforcerowsecurity
                    FROM pg_class AS c
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public'
                      AND c.relname = ANY(CAST(:table_names AS text[]))
                    """
                ),
                {"table_names": sorted(USER_OWNED_TABLES)},
            )
        }
        if set(table_security) != USER_OWNED_TABLES:
            raise RuntimeError("Production database is missing an expected user-owned table.")
        if any(row.owner_name == session_role.rolname for row in table_security.values()):
            raise RuntimeError("Production runtime database role must not own user-owned tables.")
        if any(
            not row.relrowsecurity or not row.relforcerowsecurity for row in table_security.values()
        ):
            raise RuntimeError("Production user-owned tables must have forced row-level security.")

        try:
            _set_local_authenticated_role(connection)
        except Exception as exc:
            raise RuntimeError(
                "Production database user must be allowed to SET ROLE authenticated."
            ) from exc

        effective_role = connection.execute(
            text(
                "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
            )
        ).one()
        if (
            effective_role.rolname != AUTHENTICATED_DATABASE_ROLE
            or effective_role.rolsuper
            or effective_role.rolbypassrls
        ):
            raise RuntimeError(
                "Production request transactions must use the non-privileged authenticated role."
            )

        sentinel_user_id = "00000000-0000-0000-0000-000000000000"
        sentinel_claims = json.dumps(
            {"role": AUTHENTICATED_DATABASE_ROLE, "sub": sentinel_user_id},
            separators=(",", ":"),
        )
        connection.execute(
            text(
                "SELECT "
                "set_config('request.jwt.claim.sub', :user_id, true), "
                "set_config('request.jwt.claims', :claims, true)"
            ),
            {"user_id": sentinel_user_id, "claims": sentinel_claims},
        )
        resolved_user_id = connection.execute(text("SELECT auth.uid()::text")).scalar_one()
        if resolved_user_id != sentinel_user_id:
            raise RuntimeError("Supabase auth.uid() is not available to request transactions.")


def require_current_database_schema() -> None:
    alembic_config = Config(str(ALEMBIC_CONFIG_PATH))
    expected_revisions = set(ScriptDirectory.from_config(alembic_config).get_heads())

    with get_engine().begin() as connection:
        if get_settings().is_production:
            _set_local_authenticated_role(connection)
        current_revisions = set(MigrationContext.configure(connection).get_current_heads())

    if current_revisions != expected_revisions:
        current = ", ".join(sorted(current_revisions)) or "none"
        expected = ", ".join(sorted(expected_revisions)) or "none"
        raise RuntimeError(
            "Database schema is not at the expected Alembic revision "
            f"(current: {current}; expected: {expected}). "
            "Run `uv run alembic upgrade head` before starting the service."
        )


def new_database_session() -> Session:
    if _SessionLocal is None:
        configure_database()

    assert _SessionLocal is not None
    return _SessionLocal()


def get_db(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Generator[Session, None, None]:
    db = new_database_session()
    if settings.is_production:
        bind_database_identity(db, user_id=user.id)

    try:
        yield db
    finally:
        db.close()
