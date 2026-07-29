import os
from collections.abc import Generator
from dataclasses import dataclass
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, select, text, update
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from app import database
from app.config import Settings
from app.database import bind_database_identity
from app.models import Profile

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SUPABASE_TEST_DATABASE_URL = os.getenv("SUPABASE_TEST_DATABASE_URL")
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

pytestmark = pytest.mark.skipif(
    not SUPABASE_TEST_DATABASE_URL,
    reason="SUPABASE_TEST_DATABASE_URL is required for Supabase integration tests.",
)


@dataclass(frozen=True)
class SupabaseDatabase:
    admin_engine: Engine
    runtime_engine: Engine
    runtime_role: str
    runtime_url: str


def migration_config(database_url: str) -> Config:
    config = Config(os.path.join(PROJECT_ROOT, "alembic.ini"))
    config.attributes["database_url"] = database_url
    return config


@pytest.fixture(scope="session")
def supabase_database() -> Generator[SupabaseDatabase, None, None]:
    assert SUPABASE_TEST_DATABASE_URL is not None
    command.upgrade(migration_config(SUPABASE_TEST_DATABASE_URL), "head")

    admin_url = make_url(SUPABASE_TEST_DATABASE_URL)
    admin_engine = create_engine(admin_url, pool_pre_ping=True)
    runtime_role = f"med_app_test_{uuid4().hex[:12]}"
    runtime_password = f"test_{uuid4().hex}"

    with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.exec_driver_sql(
            f'CREATE ROLE "{runtime_role}" '
            f"LOGIN PASSWORD '{runtime_password}' "
            "NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
        )
        connection.exec_driver_sql(f'GRANT authenticated TO "{runtime_role}"')

    runtime_url = admin_url.set(username=runtime_role, password=runtime_password)
    runtime_engine = create_engine(
        runtime_url,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )

    try:
        yield SupabaseDatabase(
            admin_engine=admin_engine,
            runtime_engine=runtime_engine,
            runtime_role=runtime_role,
            runtime_url=runtime_url.render_as_string(hide_password=False),
        )
    finally:
        runtime_engine.dispose()
        with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.exec_driver_sql(f'REVOKE authenticated FROM "{runtime_role}"')
            connection.exec_driver_sql(f'DROP ROLE IF EXISTS "{runtime_role}"')
        admin_engine.dispose()


@pytest.fixture(autouse=True)
def clean_user_tables(supabase_database: SupabaseDatabase):
    table_names = ", ".join(f"public.{name}" for name in sorted(USER_OWNED_TABLES))
    with supabase_database.admin_engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {table_names} CASCADE")


def user_session(engine: Engine, user_id: str) -> Session:
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = session_factory()
    bind_database_identity(db, user_id=user_id)
    return db


def test_runtime_role_is_non_privileged_and_can_assume_authenticated(
    supabase_database: SupabaseDatabase,
):
    user_id = str(uuid4())
    with supabase_database.runtime_engine.begin() as connection:
        runtime_role = connection.execute(
            text(
                "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = session_user"
            )
        ).one()
        assert runtime_role.rolname == supabase_database.runtime_role
        assert runtime_role.rolsuper is False
        assert runtime_role.rolbypassrls is False

        connection.exec_driver_sql("SET LOCAL ROLE authenticated")
        connection.execute(
            text(
                "SELECT "
                "set_config('request.jwt.claim.sub', :user_id, true), "
                "set_config('request.jwt.claims', :claims, true)"
            ),
            {
                "user_id": user_id,
                "claims": f'{{"role":"authenticated","sub":"{user_id}"}}',
            },
        )
        assert connection.execute(text("SELECT current_user")).scalar_one() == "authenticated"
        assert connection.execute(text("SELECT auth.uid()::text")).scalar_one() == user_id


def test_production_startup_rejects_bypass_and_accepts_runtime_role(
    supabase_database: SupabaseDatabase,
    monkeypatch,
):
    production_settings = Settings(
        _env_file=None,
        environment="production",
        database_url=supabase_database.runtime_url,
        migration_database_url=SUPABASE_TEST_DATABASE_URL,
        dev_auth_enabled=False,
        supabase_url="https://example.supabase.co",
    )
    test_settings = Settings(
        _env_file=None,
        environment="test",
        database_url=SUPABASE_TEST_DATABASE_URL,
    )
    monkeypatch.setattr(database, "get_settings", lambda: production_settings)

    try:
        database.configure_database(settings=test_settings)
        with pytest.raises(RuntimeError, match="superuser or BYPASSRLS"):
            database.require_safe_production_database_role()

        database.configure_database(
            supabase_database.runtime_url,
            settings=test_settings,
        )
        database.require_safe_production_database_role()
        database.require_current_database_schema()
    finally:
        database.dispose_database()


def test_every_user_owned_table_has_forced_owner_rls(
    supabase_database: SupabaseDatabase,
):
    with supabase_database.admin_engine.connect() as connection:
        protected_tables = {
            row.relname
            for row in connection.execute(
                text(
                    """
                    SELECT c.relname
                    FROM pg_class AS c
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public'
                      AND c.relname = ANY(:table_names)
                      AND c.relrowsecurity
                      AND c.relforcerowsecurity
                    """
                ),
                {"table_names": sorted(USER_OWNED_TABLES)},
            )
        }
        assert protected_tables == USER_OWNED_TABLES

        policies = {
            row.tablename: row
            for row in connection.execute(
                text(
                    """
                    SELECT tablename, policyname, cmd, roles, qual, with_check
                    FROM pg_policies
                    WHERE schemaname = 'public'
                      AND tablename = ANY(:table_names)
                    """
                ),
                {"table_names": sorted(USER_OWNED_TABLES)},
            )
        }

        assert set(policies) == USER_OWNED_TABLES
        for table_name, policy in policies.items():
            assert policy.policyname == f"{table_name}_owner_access"
            assert policy.cmd == "ALL"
            assert policy.roles == ["authenticated"]
            assert "auth.uid()" in policy.qual
            assert "auth.uid()" in policy.with_check


def test_two_users_are_isolated_for_direct_crud_and_commit_boundaries(
    supabase_database: SupabaseDatabase,
):
    owner_id = str(uuid4())
    other_id = str(uuid4())
    profile_id = str(uuid4())

    with user_session(supabase_database.runtime_engine, owner_id) as owner_db:
        profile = Profile(
            id=profile_id,
            user_id=owner_id,
            display_name="Owner profile",
            relationship="self",
        )
        owner_db.add(profile)
        owner_db.commit()
        owner_db.refresh(profile)
        assert profile.display_name == "Owner profile"

        profile.display_name = "Owner profile after commit"
        owner_db.commit()

    with user_session(supabase_database.runtime_engine, other_id) as other_db:
        assert other_db.scalars(select(Profile)).all() == []

        update_result = other_db.execute(
            update(Profile).where(Profile.id == profile_id).values(display_name="Cross-user update")
        )
        assert update_result.rowcount == 0

        delete_result = other_db.execute(delete(Profile).where(Profile.id == profile_id))
        assert delete_result.rowcount == 0
        other_db.commit()

        other_db.add(
            Profile(
                id=str(uuid4()),
                user_id=owner_id,
                display_name="Spoofed owner",
                relationship="self",
            )
        )
        with pytest.raises(DBAPIError):
            other_db.commit()
        other_db.rollback()

    with user_session(supabase_database.runtime_engine, owner_id) as owner_db:
        profile = owner_db.get(Profile, profile_id)
        assert profile is not None
        assert profile.display_name == "Owner profile after commit"

        with pytest.raises(DBAPIError):
            owner_db.execute(
                update(Profile).where(Profile.id == profile_id).values(user_id=other_id)
            )
        owner_db.rollback()

        delete_result = owner_db.execute(delete(Profile).where(Profile.id == profile_id))
        assert delete_result.rowcount == 1
        owner_db.commit()


def test_missing_claims_default_to_no_rows(supabase_database: SupabaseDatabase):
    owner_id = str(uuid4())
    with user_session(supabase_database.runtime_engine, owner_id) as owner_db:
        owner_db.add(
            Profile(
                id=str(uuid4()),
                user_id=owner_id,
                display_name="Private profile",
                relationship="self",
            )
        )
        owner_db.commit()

    with supabase_database.runtime_engine.begin() as connection:
        connection.exec_driver_sql("SET LOCAL ROLE authenticated")
        assert connection.execute(text("SELECT * FROM public.profiles")).all() == []
