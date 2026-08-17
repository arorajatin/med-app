from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from app import models  # noqa: F401
from app.config import get_settings
from app.database import Base, bootstrap_test_database, configure_database
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

    command.upgrade(migration_config(url), "head")

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
