from collections.abc import Generator
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

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
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, connect_args=connect_args)
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


def get_db() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        configure_database()

    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
