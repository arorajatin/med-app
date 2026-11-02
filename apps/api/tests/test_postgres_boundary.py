"""Real PostgreSQL checks. Use a disposable loopback server, never the target project."""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from document_fixtures import image_bytes, pdf_bytes
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, Numeric, create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from test_supabase_storage import StorageTransport

from app import models
from app.auth import get_current_user
from app.config import Settings, get_settings
from app.data_boundary import verify_database_boundary
from app.database import Base
from app.main import create_app
from app.schemas import CurrentUser
from app.services.accounts import resolve_account_context
from app.storage_cleanup import reconcile_uploads

ROOT = Path(__file__).resolve().parents[3]
SECRET = "only-for-disposable-policy-tests-0000000000"


@pytest.fixture(scope="module")
def boundary_database():
    configured = os.environ.get("BOUNDARY_TEST_ADMIN_URL")
    if not configured:
        pytest.skip("Set BOUNDARY_TEST_ADMIN_URL to a disposable loopback PostgreSQL server.")
    url = make_url(configured)
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("Policy tests create a disposable database and require a loopback server.")
    database = "boundary_test_" + uuid4().hex
    admin = create_engine(url, isolation_level="AUTOCOMMIT", hide_parameters=True)
    with admin.connect() as connection:
        connection.exec_driver_sql(f'CREATE DATABASE "{database}"')
    test_url = url.set(database=database)
    config = Config(str(ROOT / "apps/api/alembic.ini"))
    config.attributes["database_url"] = test_url.render_as_string(hide_password=False)
    command.upgrade(config, "head")
    owner = create_engine(test_url, hide_parameters=True)
    with owner.begin() as connection:
        connection.execute(text("ALTER ROLE med_app_api LOGIN PASSWORD 'boundary-test-only'"))
        connection.execute(text("ALTER ROLE med_app_cleanup LOGIN PASSWORD 'boundary-test-only'"))
        connection.execute(
            text("""
            CREATE SCHEMA storage;
            CREATE TABLE storage.buckets(id text PRIMARY KEY, name text, public boolean,
                file_size_limit bigint, allowed_mime_types text[]);
            CREATE TABLE storage.objects(id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
                bucket_id text REFERENCES storage.buckets(id), name text UNIQUE);
            ALTER TABLE storage.buckets ENABLE ROW LEVEL SECURITY;
            ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;
            DO $roles$ DECLARE name text; BEGIN
                FOREACH name IN ARRAY ARRAY['authenticator', 'anon', 'authenticated'] LOOP
                    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = name) THEN
                        EXECUTE format('CREATE ROLE %I NOLOGIN NOBYPASSRLS', name);
                    END IF;
                END LOOP;
            END $roles$;
            GRANT USAGE ON SCHEMA storage TO authenticated, anon;
            GRANT ALL ON storage.objects, storage.buckets TO authenticated, anon;
            CREATE POLICY unrelated_broad_policy ON storage.objects TO PUBLIC USING(true) WITH CHECK(true);
        """)
        )
        connection.execute(text((ROOT / "infra/supabase/storage.sql").read_text()))
        connection.execute(
            text("INSERT INTO med_app_private.configuration(key, value) VALUES (:key, :value)"),
            [
                {"key": "storage_jwt_secret", "value": SECRET},
                {"key": "supabase_url", "value": "https://abcdefghijklmnopqrst.supabase.co"},
                {"key": "project_ref", "value": "abcdefghijklmnopqrst"},
                {"key": "region", "value": "ap-southeast-1"},
            ],
        )
    api = create_engine(
        test_url.set(username="med_app_api", password="boundary-test-only"),
        pool_size=1,
        max_overflow=0,
        hide_parameters=True,
    )
    cleanup = create_engine(
        test_url.set(username="med_app_cleanup", password="boundary-test-only"),
        hide_parameters=True,
    )
    yield owner, api, cleanup
    api.dispose()
    cleanup.dispose()
    owner.dispose()
    with admin.connect() as connection:
        connection.exec_driver_sql(f'DROP DATABASE "{database}" WITH (FORCE)')
    admin.dispose()


def session(api, subject):
    return Session(api, info={"supabase_rls": True, "verified_subject": subject})


def account(api, subject):
    with session(api, subject) as db:
        context = resolve_account_context(db, provider="supabase", provider_subject=subject)
        return context.account.id, context.identity.id


def seed_graph(owner, account_id, identity_id):
    """One valid row in every private policy family, with shared owned parents."""
    rows = {"accounts": {"id": account_id}, "auth_identities": {"id": identity_id}}
    with owner.begin() as connection:
        for table in Base.metadata.sorted_tables:
            if table.name in rows:
                continue
            values = {"id": str(uuid4()), "account_id": account_id}
            for column in table.c:
                if column.name in values:
                    continue
                if column.nullable:
                    values[column.name] = None
                elif column.foreign_keys:
                    parent = next(iter(column.foreign_keys)).column.table.name
                    values[column.name] = rows[parent]["id"]
                elif column.default is not None:
                    values[column.name] = (
                        column.default.arg(None)
                        if column.default.is_callable
                        else column.default.arg
                    )
                elif isinstance(column.type, (DateTime, Date)):
                    values[column.name] = datetime.now(UTC)
                elif isinstance(column.type, Boolean):
                    values[column.name] = False
                elif isinstance(column.type, (Integer, Numeric)):
                    values[column.name] = 1
                elif isinstance(column.type, JSON):
                    values[column.name] = {}
                else:
                    values[column.name] = "fixture"
            if table.name == "profile_health_context":
                values["reported_age"] = 30
            if table.name == "ingestions":
                values.update(source_channel="direct_file", upload_state="receiving")
            if table.name == "ingestion_assignments":
                values["method"] = "manual"
            if table.name == "source_references":
                values["patient_evidence_id"] = rows["patient_evidence"]["id"]
            if table.name == "storage_cleanup_intents":
                values["object_key"] = (
                    f"accounts/{account_id}/ingestions/{uuid4()}/parts/{uuid4()}/{uuid4()}"
                )
                values["reconcile_after"] = datetime.now(UTC) + timedelta(hours=1)
            connection.execute(table.insert().values(**values))
            rows[table.name] = values
    return rows


def test_every_policy_family_denies_cross_account_reads_and_mutations(boundary_database):
    owner, api, _ = boundary_database
    subject_a, subject_b = str(uuid4()), str(uuid4())
    account_a, identity_a = account(api, subject_a)
    account_b, _ = account(api, subject_b)
    rows = seed_graph(owner, account_a, identity_a)
    for table in Base.metadata.sorted_tables:
        with session(api, subject_b) as db:
            assert (
                db.execute(select(table).where(table.c.id == rows[table.name]["id"])).first()
                is None
            )
            if table.name in {"accounts", "auth_identities"}:
                with pytest.raises(DBAPIError):
                    db.execute(table.delete().where(table.c.id == rows[table.name]["id"]))
                continue
            assert (
                db.execute(table.delete().where(table.c.id == rows[table.name]["id"])).rowcount == 0
            )
            assert (
                db.execute(
                    table.update()
                    .where(table.c.id == rows[table.name]["id"])
                    .values(account_id=account_b)
                ).rowcount
                == 0
            )
            with pytest.raises(DBAPIError) as error:
                db.execute(table.insert().values(**{**rows[table.name], "id": str(uuid4())}))
            assert error.value.orig.sqlstate == "42501"
        with session(api, subject_a) as db:
            assert (
                db.execute(select(table).where(table.c.id == rows[table.name]["id"])).first()
                is not None
            )
            if table.name not in {"accounts", "auth_identities"}:
                with pytest.raises(DBAPIError) as error:
                    db.execute(
                        table.update()
                        .where(table.c.id == rows[table.name]["id"])
                        .values(account_id=account_b)
                    )
                assert error.value.orig.sqlstate == "42501"


def test_pool_reuse_and_commit_reestablish_identity(boundary_database):
    _, api, _ = boundary_database
    first, second = str(uuid4()), str(uuid4())
    first_id, _ = account(api, first)
    second_id, _ = account(api, second)
    for subject, expected in ((first, first_id), (second, second_id), (first, first_id)):
        with session(api, subject) as db:
            for _ in range(2):
                assert db.scalars(select(models.Account.id)).all() == [expected]
                assert db.execute(text("SELECT current_user")).scalar_one() == "med_app_request"
                db.commit()
    with api.connect() as connection:
        assert connection.execute(text("SELECT current_user")).scalar_one() == "med_app_api"
        assert not connection.execute(
            text("SELECT current_setting('request.jwt.claims', true)")
        ).scalar_one()
        with pytest.raises(DBAPIError):
            connection.execute(text("SELECT * FROM profiles"))


def test_owned_child_cannot_point_at_another_accounts_profile(boundary_database):
    _, api, _ = boundary_database
    first, second = str(uuid4()), str(uuid4())
    first_id, _ = account(api, first)
    second_id, _ = account(api, second)
    with session(api, second) as db:
        profile = models.Profile(account_id=second_id, display_name="Fixture")
        db.add(profile)
        db.commit()
        profile_id = profile.id
    with session(api, first) as db:
        db.add(
            models.Ingestion(
                account_id=first_id, source_channel="direct_file", provisional_profile_id=profile_id
            )
        )
        with pytest.raises(IntegrityError) as error:
            db.commit()
        assert error.value.orig.sqlstate == "23503"


def test_single_object_tokens_and_direct_client_denial(boundary_database):
    owner, api, _ = boundary_database
    subject = str(uuid4())
    account_id, _ = account(api, subject)
    with session(api, subject) as db:
        ingestion = models.Ingestion(account_id=account_id, source_channel="direct_file")
        db.add(ingestion)
        db.flush()
        key = f"accounts/{account_id}/ingestions/{ingestion.id}/parts/{uuid4()}/{uuid4()}"
        token = db.execute(
            text("SELECT med_app_private.issue_storage_token('upload', :key)"), {"key": key}
        ).scalar_one()
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
        assert claims["role"] == "med_app_storage"
        assert claims["object_key"] == key
        assert claims["exp"] - claims["iat"] <= 60
        with pytest.raises(DBAPIError):
            db.execute(text("SELECT value FROM med_app_private.configuration"))
    with owner.begin() as connection:
        connection.execute(text("SET LOCAL ROLE med_app_storage"))
        connection.execute(
            text("SELECT set_config('request.jwt.claims', :claims, true)"),
            {"claims": json.dumps(claims)},
        )
        connection.execute(
            text("INSERT INTO storage.objects(bucket_id, name) VALUES ('medical-records', :key)"),
            {"key": key},
        )
    for role in ("anon", "authenticated", "med_app_storage"):
        with owner.begin() as connection:
            connection.execute(text(f"SET LOCAL ROLE {role}"))
            connection.execute(
                text("SELECT set_config('request.jwt.claims', :claims, true)"),
                {
                    "claims": json.dumps(
                        {**claims, "operation": "read", "object_key": key + "other"}
                    )
                },
            )
            assert (
                connection.execute(
                    text("SELECT name FROM storage.objects WHERE name = :key"), {"key": key}
                ).all()
                == []
            )
            assert (
                connection.execute(
                    text("DELETE FROM storage.objects WHERE name = :key"), {"key": key}
                ).rowcount
                == 0
            )
            with pytest.raises(DBAPIError):
                connection.execute(
                    text(
                        "INSERT INTO storage.objects(bucket_id, name) VALUES ('medical-records', :key)"
                    ),
                    {"key": key + "blocked"},
                )
    with owner.begin() as connection:
        connection.execute(text("SET LOCAL ROLE med_app_storage"))
        connection.execute(
            text("SELECT set_config('request.jwt.claims', :claims, true)"),
            {"claims": json.dumps({**claims, "operation": "read"})},
        )
        assert (
            connection.execute(
                text("SELECT name FROM storage.objects WHERE name = :key"), {"key": key}
            ).scalar_one()
            == key
        )
        assert (
            connection.execute(
                text("DELETE FROM storage.objects WHERE name = :key"), {"key": key}
            ).rowcount
            == 0
        )


def test_cleanup_derives_scope_from_due_work_and_cannot_query_private_rows(boundary_database):
    owner, api, cleanup = boundary_database
    subject = str(uuid4())
    account_id, _ = account(api, subject)
    key = f"accounts/{account_id}/ingestions/{uuid4()}/parts/{uuid4()}/{uuid4()}"
    work_id = str(uuid4())
    with session(api, subject) as db:
        db.add(
            models.StorageCleanupIntent(
                id=work_id,
                account_id=account_id,
                object_key=key,
                storage_bucket="medical-records",
                reconcile_after=datetime.now(UTC) - timedelta(seconds=1),
            )
        )
        db.commit()
    with cleanup.begin() as connection:
        assert (
            connection.execute(
                text("SELECT med_app_private.claim_cleanup(:id)"), {"id": str(uuid4())}
            ).scalar_one()
            is None
        )
        claim = connection.execute(
            text("SELECT med_app_private.claim_cleanup(:id)"), {"id": work_id}
        ).scalar_one()
        claims = jwt.decode(claim["token"], SECRET, algorithms=["HS256"])
        assert claims["account_id"] == account_id
        assert claims["object_key"] == key
        assert claims["operation"] == "delete"
    with cleanup.begin() as connection:
        with pytest.raises(DBAPIError):
            connection.execute(text("SELECT * FROM ingestion_parts"))
    with cleanup.begin() as connection:
        connection.execute(text("SELECT med_app_private.complete_cleanup(:id)"), {"id": work_id})
    with owner.connect() as connection:
        assert (
            connection.execute(
                text("SELECT id FROM storage_cleanup_intents WHERE id = :id"), {"id": work_id}
            ).first()
            is None
        )


@pytest.fixture()
def hosted_client(boundary_database, monkeypatch):
    _, api, _ = boundary_database
    for key, value in {
        "DATABASE_URL": api.url.render_as_string(hide_password=False),
        "DATA_BACKEND": "supabase",
        "ENVIRONMENT": "test",
        "DEV_AUTH_ENABLED": "false",
        "EXTRACTION_PROVIDER": "disabled",
        "EXTRACTION_RUN_INLINE": "false",
        "SUPABASE_URL": "https://abcdefghijklmnopqrst.supabase.co",
        "SUPABASE_PROJECT_REF": "abcdefghijklmnopqrst",
        "SUPABASE_REGION": "ap-southeast-1",
        "SUPABASE_ANON_KEY": "sb_publishable_test",
    }.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    # Only this disposable loopback test bypasses hosted DNS/TLS admission.
    # Real role/policy startup verification and all request transactions still run.
    monkeypatch.setattr("app.main.validate_data_settings", lambda settings: None)
    transport = StorageTransport()
    monkeypatch.setattr("app.supabase_storage.build_opener", lambda *args: transport)
    app = create_app()

    def verified_identity(request: Request):
        return CurrentUser(id=request.headers["x-test-subject"], upstream_provider="google")

    app.dependency_overrides[get_current_user] = verified_identity
    with TestClient(app) as client:
        yield client, transport
    get_settings.cache_clear()


def test_hosted_upload_persists_verified_bytes_and_queued_feed(hosted_client, boundary_database):
    client, transport = hosted_client
    owner, api, _ = boundary_database
    subject = str(uuid4())
    headers = {"x-test-subject": subject}
    profile = client.post(
        "/profiles", headers=headers, json={"display_name": "Fixture", "relationship": "self"}
    )
    assert profile.status_code == 201, profile.text
    payload = pdf_bytes()
    response = client.post(
        "/ingestions/direct-file",
        headers=headers,
        data={"provisional_profile_id": profile.json()["id"]},
        files=[("uploads", ("fixture.pdf", payload))],
    )
    assert response.status_code == 201, response.text
    receipt = response.json()
    with session(api, subject) as db:
        part = (
            db.query(models.IngestionPart).filter_by(ingestion_id=receipt["ingestion"]["id"]).one()
        )
        assert part.storage_bucket == "medical-records"
        assert transport.objects[part.object_key] == payload
        assert db.query(models.StorageCleanupIntent).count() == 0
        claims = jwt.decode(
            transport.calls[0].get_header("Authorization").removeprefix("Bearer "),
            SECRET,
            algorithms=["HS256"],
        )
        assert claims["object_key"] == part.object_key
        assert claims["operation"] == "upload"
    feed = client.get("/feed", headers=headers)
    item = feed.json()["items"][0]
    assert item["id"] == receipt["ingestion"]["id"]
    assert item["extraction_state"] == "queued"
    assert item["assignment_state"] == "provisional"
    assert "object_key" not in feed.text and "storage_bucket" not in feed.text
    assert (
        client.get("/feed", headers=headers, params={"profile_id": profile.json()["id"]}).json()[
            "items"
        ]
        == []
    )
    assert client.get("/feed", headers={"x-test-subject": str(uuid4())}).json()["items"] == []
    assert (
        client.post(
            f"/extraction/jobs/{receipt['extraction_job']['id']}/run", headers=headers
        ).status_code
        == 503
    )
    with owner.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM extraction_attempts WHERE job_id = :id"),
                {"id": receipt["extraction_job"]["id"]},
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize("failure", ["checksum", "second_part", "metadata"])
def test_hosted_failed_receipt_rolls_back_rows_and_preserves_cleanup(
    hosted_client, boundary_database, monkeypatch, failure
):
    client, transport = hosted_client
    _, api, _ = boundary_database
    subject = str(uuid4())
    if failure == "checksum":
        transport.corrupt = True
    if failure == "metadata":

        def failed_save(*args, **kwargs):
            raise RuntimeError("synthetic database failure")

        monkeypatch.setattr("app.api.routes.create_extraction_job", failed_save)
    files = [("uploads", ("page.png", image_bytes()))]
    if failure == "second_part":
        files.append(("uploads", ("broken.png", b"invalid")))
    response = client.post(
        "/ingestions/direct-file", headers={"x-test-subject": subject}, files=files
    )
    assert response.status_code in {415, 503}, response.text
    assert transport.objects == {}
    with session(api, subject) as db:
        assert db.query(models.Ingestion).count() == 0
        assert db.query(models.IngestionPart).count() == 0
        assert db.query(models.StorageCleanupIntent).count() == 1
    assert client.get("/feed", headers={"x-test-subject": subject}).json()["items"] == []


def test_cleanup_retries_and_runs_with_new_uploads_disabled(boundary_database, monkeypatch):
    owner, api, cleanup = boundary_database
    subject = str(uuid4())
    account_id, _ = account(api, subject)
    key = f"accounts/{account_id}/ingestions/{uuid4()}/parts/{uuid4()}/{uuid4()}"
    work_id = str(uuid4())
    with session(api, subject) as db:
        db.add(
            models.StorageCleanupIntent(
                id=work_id,
                account_id=account_id,
                object_key=key,
                storage_bucket="medical-records",
                reconcile_after=datetime.now(UTC) - timedelta(seconds=1),
            )
        )
        db.commit()
    settings = Settings(
        _env_file=None,
        data_backend="supabase",
        environment="production",
        dev_auth_enabled=False,
        database_url="",
        supabase_cleanup_database_url="postgresql://med_app_cleanup:password@db.abcdefghijklmnopqrst.supabase.co/postgres?sslmode=verify-full",
        supabase_url="https://abcdefghijklmnopqrst.supabase.co",
        supabase_project_ref="abcdefghijklmnopqrst",
        supabase_region="ap-southeast-1",
        supabase_anon_key="sb_publishable_test",
        production_data_enabled=False,
        extraction_provider="disabled",
        extraction_run_inline=False,
    )
    # Connect the validated role to our isolated database instead of a hosted project.
    monkeypatch.setattr("app.storage_cleanup.create_engine", lambda *args, **kwargs: cleanup)
    transport = StorageTransport()
    transport.objects[key] = b"synthetic orphan"
    transport.fail = True
    monkeypatch.setattr("app.supabase_storage.build_opener", lambda *args: transport)
    assert reconcile_uploads(settings) == (0, 1)
    with session(api, subject) as db:
        work = db.get(models.StorageCleanupIntent, work_id)
        assert work.state == "cleaning"
        assert work.reconcile_after > datetime.now(UTC)
        work.reconcile_after = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    transport.fail = False
    assert reconcile_uploads(settings) == (1, 0)
    assert reconcile_uploads(settings) == (0, 0)
    assert key not in transport.objects
    assert (
        jwt.decode(
            transport.calls[-1].get_header("Authorization").removeprefix("Bearer "),
            SECRET,
            algorithms=["HS256"],
        )["object_key"]
        == key
    )
    with owner.connect() as connection:
        assert (
            connection.execute(
                text("SELECT id FROM storage_cleanup_intents WHERE id = :id"), {"id": work_id}
            ).first()
            is None
        )


def test_cleanup_keeps_a_committed_source_and_fences_stalled_upload(
    hosted_client, boundary_database, monkeypatch
):
    client, transport = hosted_client
    _, api, cleanup = boundary_database
    subject = str(uuid4())
    headers = {"x-test-subject": subject}
    receipt = client.post(
        "/ingestions/direct-file",
        headers=headers,
        files=[("uploads", ("fixture.pdf", pdf_bytes()))],
    ).json()
    with session(api, subject) as db:
        part = (
            db.query(models.IngestionPart).filter_by(ingestion_id=receipt["ingestion"]["id"]).one()
        )
        key = part.object_key
        intent = models.StorageCleanupIntent(
            account_id=part.account_id,
            object_key=key,
            storage_bucket="medical-records",
            reconcile_after=datetime.now(UTC) - timedelta(seconds=1),
        )
        db.add(intent)
        db.commit()
        work_id = intent.id
    with cleanup.begin() as connection:
        assert (
            connection.execute(
                text("SELECT med_app_private.claim_cleanup(:id)"), {"id": work_id}
            ).scalar_one()
            is None
        )
    assert key in transport.objects

    # A cleanup claim racing the metadata commit must stop receipt, not resurrect a file.
    from app.services.extraction import create_extraction_job

    def claim_before_metadata_commit(db, *, ingestion):
        with session(api, subject) as other:
            intent = (
                other.query(models.StorageCleanupIntent)
                .filter_by(account_id=ingestion.account_id)
                .one()
            )
            intent.reconcile_after = datetime.now(UTC) - timedelta(seconds=1)
            other.commit()
            intent_id = intent.id
        with cleanup.begin() as connection:
            assert (
                connection.execute(
                    text("SELECT med_app_private.claim_cleanup(:id)"), {"id": intent_id}
                ).scalar_one()
                is not None
            )
        return create_extraction_job(db, ingestion=ingestion)

    monkeypatch.setattr("app.api.routes.create_extraction_job", claim_before_metadata_commit)
    failed = client.post(
        "/ingestions/direct-file",
        headers=headers,
        files=[("uploads", ("stalled.pdf", pdf_bytes()))],
    )
    assert failed.status_code == 503
    assert list(transport.objects) == [key]
    assert len(client.get("/feed", headers=headers).json()["items"]) == 1


def test_boundary_preflight_rejects_policy_drift(boundary_database):
    owner, api, _ = boundary_database
    settings = Settings(
        _env_file=None,
        data_backend="supabase",
        supabase_project_ref="abcdefghijklmnopqrst",
        supabase_region="ap-southeast-1",
    )
    verify_database_boundary(api, settings)
    with owner.begin() as connection:
        connection.execute(text("ALTER TABLE profiles DISABLE ROW LEVEL SECURITY"))
    try:
        with pytest.raises(RuntimeError, match="preflight"):
            verify_database_boundary(api, settings)
    finally:
        with owner.begin() as connection:
            connection.execute(text("ALTER TABLE profiles ENABLE ROW LEVEL SECURITY"))
