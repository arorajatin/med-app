import json
from collections.abc import Generator
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import DeclarativeBase, Session, SessionTransaction, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_CONFIG_PATH = PROJECT_ROOT / "alembic.ini"


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


# Hosted providers hand out `postgresql://` and `postgres://` connection strings.
# SQLAlchemy maps both to psycopg2, which this project does not depend on, so name
# the declared psycopg 3 driver instead of failing on an uninstalled one.
_POSTGRES_PREFIXES = ("postgresql://", "postgres://")


def normalize_database_url(url: str) -> str:
    for prefix in _POSTGRES_PREFIXES:
        if url.startswith(prefix):
            return f"postgresql+psycopg://{url.removeprefix(prefix)}"
    return url


def configure_database(database_url: str | None = None) -> None:
    global _engine, _SessionLocal

    url = normalize_database_url(database_url or get_settings().database_url)
    connect_args = (
        {"check_same_thread": False} if url.startswith("sqlite") else {"prepare_threshold": None}
    )
    if _engine is not None:
        _engine.dispose()
    _engine = create_engine(
        url, connect_args=connect_args, hide_parameters=True, pool_pre_ping=True
    )
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def get_engine() -> Engine:
    if _engine is None:
        configure_database()
    assert _engine is not None
    return _engine


def bootstrap_test_database() -> None:
    if get_settings().environment != "test":
        raise RuntimeError("Metadata schema bootstrap is only allowed when ENVIRONMENT=test.")

    from app import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def require_current_database_schema() -> None:
    alembic_config = Config(str(ALEMBIC_CONFIG_PATH))
    expected_revisions = set(ScriptDirectory.from_config(alembic_config).get_heads())

    with get_engine().connect() as connection:
        current_revisions = set(MigrationContext.configure(connection).get_current_heads())

    if current_revisions != expected_revisions:
        current = ", ".join(sorted(current_revisions)) or "none"
        expected = ", ".join(sorted(expected_revisions)) or "none"
        raise RuntimeError(
            "Database schema is not at the expected Alembic revision "
            f"(current: {current}; expected: {expected}). "
            "Run `uv run alembic upgrade head` before starting the service."
        )


@event.listens_for(Session, "after_begin")
def establish_request_identity(
    session: Session, transaction: SessionTransaction, connection: Connection
) -> None:
    if not session.info.get("supabase_rls"):
        return
    subject = session.info.get("verified_subject")
    if not subject:
        raise RuntimeError("Supabase database access requires a verified identity.")
    connection.execute(text("SET LOCAL ROLE med_app_request"))
    connection.execute(
        text("SELECT set_config('request.jwt.claims', :claims, true)"),
        {"claims": json.dumps({"sub": subject, "role": "med_app_request"})},
    )


def get_db(*, verified_subject: str | None = None) -> Generator[Session, None, None]:
    if _SessionLocal is None:
        configure_database()

    assert _SessionLocal is not None
    db = _SessionLocal()
    if get_settings().data_backend == "supabase":
        if not verified_subject:
            db.close()
            raise RuntimeError("Supabase database access requires a verified identity.")
        db.info.update(supabase_rls=True, verified_subject=verified_subject)
    try:
        yield db
    finally:
        db.close()
