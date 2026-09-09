from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.config import get_settings
from app.database import (
    Base,
    bootstrap_test_database,
    configure_database,
    normalize_database_url,
)
from app.main import create_app
from app.worker import run_once

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def database_url(path: Path) -> str:
    return f"sqlite:///{path}"


def migration_config(url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.attributes["database_url"] = url
    return config


def current_revisions(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return set(MigrationContext.configure(connection).get_current_heads())
    finally:
        engine.dispose()


def assert_schema_matches_metadata(url: str) -> None:
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) - {"alembic_version"} == set(Base.metadata.tables)

        for table_name, table in Base.metadata.tables.items():
            actual_columns = {
                column["name"]: column for column in inspector.get_columns(table_name)
            }
            assert set(actual_columns) == {column.name for column in table.columns}

            for expected_column in table.columns:
                actual_column = actual_columns[expected_column.name]
                assert actual_column["nullable"] == expected_column.nullable
                assert actual_column["type"].compile(dialect=engine.dialect).upper() == (
                    expected_column.type.compile(dialect=engine.dialect).upper()
                )

            actual_primary_key = set(inspector.get_pk_constraint(table_name)["constrained_columns"])
            expected_primary_key = {column.name for column in table.primary_key.columns}
            assert actual_primary_key == expected_primary_key

            actual_indexes = {
                index["name"]: (tuple(index["column_names"]), bool(index["unique"]))
                for index in inspector.get_indexes(table_name)
            }
            expected_indexes = {
                index.name: (tuple(column.name for column in index.columns), index.unique)
                for index in table.indexes
            }
            assert actual_indexes == expected_indexes

            actual_foreign_keys = {
                (
                    tuple(constraint["constrained_columns"]),
                    constraint["referred_table"],
                    tuple(constraint["referred_columns"]),
                )
                for constraint in inspector.get_foreign_keys(table_name)
            }
            expected_foreign_keys = {
                (
                    tuple(element.parent.name for element in constraint.elements),
                    constraint.referred_table.name,
                    tuple(element.column.name for element in constraint.elements),
                )
                for constraint in table.foreign_key_constraints
            }
            assert actual_foreign_keys == expected_foreign_keys
    finally:
        engine.dispose()


def test_upgrade_empty_database_to_head_matches_model_contract(tmp_path):
    url = database_url(tmp_path / "upgrade.db")
    config = migration_config(url)
    revisions = list(ScriptDirectory.from_config(config).walk_revisions())
    assert [(revision.revision, revision.down_revision) for revision in revisions] == [
        ("20260721_0001", None)
    ]

    command.upgrade(config, "head")

    assert current_revisions(url) == {"20260721_0001"}
    assert_schema_matches_metadata(url)


def test_production_api_and_worker_start_at_head_without_metadata_creation(tmp_path, monkeypatch):
    url = database_url(tmp_path / "production.db")
    command.upgrade(migration_config(url), "head")

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()

    def unexpected_metadata_creation(*args, **kwargs):
        raise AssertionError("runtime startup must not create metadata")

    monkeypatch.setattr(Base.metadata, "create_all", unexpected_metadata_creation)

    with TestClient(create_app()) as client:
        assert client.get("/health").json() == {"status": "ok"}

    assert run_once() == 0
    assert current_revisions(url) == {"20260721_0001"}
    get_settings.cache_clear()


def test_runtime_startup_rejects_an_unmigrated_database(tmp_path, monkeypatch):
    url = database_url(tmp_path / "unmigrated.db")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match=r"current: none; expected: 20260721_0001"):
        with TestClient(create_app()):
            pass

    get_settings.cache_clear()


def test_metadata_bootstrap_is_restricted_to_tests(tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    configure_database(database_url(tmp_path / "bootstrap.db"))

    with pytest.raises(RuntimeError, match="only allowed when ENVIRONMENT=test"):
        bootstrap_test_database()

    get_settings.cache_clear()


def test_downgrade_initial_revision_returns_database_to_base(tmp_path):
    url = database_url(tmp_path / "downgrade.db")
    config = migration_config(url)
    command.upgrade(config, "head")

    command.downgrade(config, "base")

    engine = create_engine(url)
    try:
        assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    finally:
        engine.dispose()
    assert current_revisions(url) == set()


def test_fresh_schema_enforces_alias_ownership(tmp_path):
    url = database_url(tmp_path / "alias-ownership.db")
    config = migration_config(url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    with Session(engine) as db:
        db.add_all([models.Account(id="owner"), models.Account(id="other")])
        db.flush()
        db.add(
            models.Profile(
                id="person", account_id="owner", display_name="Asha", relationship="self"
            )
        )
        db.add(
            models.AuthIdentity(
                id="identity",
                account_id="owner",
                provider="test",
                provider_subject="owner",
                verified_at=models.utcnow(),
            )
        )
        db.commit()
    with engine.connect() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
        with Session(connection) as db:
            assert db.query(models.Profile).one().display_name == "Asha"
            db.add(
                models.ProfileAlias(
                    account_id="owner",
                    profile_id="person",
                    name="Asha Rao",
                    normalized_name="asha rao",
                    created_by_identity_id="identity",
                )
            )
            db.commit()
            db.add(
                models.ProfileAlias(
                    account_id="other",
                    profile_id="person",
                    name="Foreign",
                    normalized_name="foreign",
                    created_by_identity_id="identity",
                )
            )
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
    engine.dispose()


def test_api_and_worker_reject_an_unknown_revision_without_mutating_it(tmp_path, monkeypatch):
    url = database_url(tmp_path / "unknown-revision.db")
    command.upgrade(migration_config(url), "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num = 'unknown_revision'"))
    engine.dispose()
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("ENVIRONMENT", "local")
    get_settings.cache_clear()
    message = "current: unknown_revision; expected: 20260721_0001"
    with pytest.raises(RuntimeError, match=message):
        with TestClient(create_app()):
            pass
    with pytest.raises(RuntimeError, match=message):
        run_once()
    assert current_revisions(url) == {"unknown_revision"}
    get_settings.cache_clear()


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("postgresql://user:pw@host:5432/db", "postgresql+psycopg://user:pw@host:5432/db"),
        ("postgres://user:pw@host:5432/db", "postgresql+psycopg://user:pw@host:5432/db"),
        (
            "postgresql+psycopg://user:pw@host:5432/db",
            "postgresql+psycopg://user:pw@host:5432/db",
        ),
        ("sqlite:///./med_app.db", "sqlite:///./med_app.db"),
    ],
    ids=["postgresql", "postgres", "already-explicit", "sqlite"],
)
def test_normalize_database_url_names_the_declared_postgres_driver(configured, expected):
    """A hosted provider's URL must reach psycopg 3 rather than an absent psycopg2."""

    assert normalize_database_url(configured) == expected
