import json
from datetime import UTC, datetime, timedelta

import pytest

from app.config import Settings
from app.data_boundary import BOUNDARY_VERSION, READINESS_CHECKS, validate_data_settings

PROJECT = "abcdefghijklmnopqrst"


@pytest.fixture()
def hosted_settings(tmp_path):
    evidence = {
        "project_ref": PROJECT,
        "region": "ap-southeast-1",
        "database_host": f"db.{PROJECT}.supabase.co",
        "boundary_version": BOUNDARY_VERSION,
        "schema_revision": "20260721_0001",
        "verified_at": datetime.now(UTC).isoformat(),
        "checks": dict.fromkeys(READINESS_CHECKS, "pass"),
    }
    path = tmp_path / "attestation.json"
    path.write_text(json.dumps(evidence))
    return (
        Settings(
            _env_file=None,
            environment="production",
            data_backend="supabase",
            dev_auth_enabled=False,
            database_url=f"postgresql://med_app_api:password@db.{PROJECT}.supabase.co/postgres?sslmode=verify-full",
            supabase_url=f"https://{PROJECT}.supabase.co",
            supabase_project_ref=PROJECT,
            supabase_region="ap-southeast-1",
            supabase_anon_key="sb_publishable_test",
            supabase_attestation_path=str(path),
            production_data_enabled=True,
            extraction_provider="disabled",
            extraction_run_inline=False,
        ),
        path,
        evidence,
    )


def test_valid_hosted_configuration_and_local_default(hosted_settings):
    settings, _, _ = hosted_settings
    validate_data_settings(settings)
    validate_data_settings(Settings(_env_file=None))


@pytest.mark.parametrize(
    "change",
    [
        {"data_backend": "local"},
        {"data_backend": "unknown"},
        {"dev_auth_enabled": True},
        {"extraction_run_inline": True},
        {"extraction_provider": "mock"},
        {"supabase_region": "us-east-1"},
        {"supabase_region": "ap-south-1"},
        {"supabase_project_ref": None},
        {"supabase_url": "https://other.supabase.co"},
        {"supabase_storage_bucket": "public"},
        {"supabase_anon_key": "sb_secret_forbidden"},
        {"database_url": "sqlite:///local.db"},
        {
            "database_url": f"postgresql://postgres:password@db.{PROJECT}.supabase.co/postgres?sslmode=verify-full"
        },
        {
            "database_url": f"postgresql://med_app_api:password@db.{PROJECT}.supabase.co/postgres?sslmode=require"
        },
        {"production_data_enabled": False},
        {"supabase_attestation_path": None},
    ],
)
def test_hosted_settings_fail_closed(hosted_settings, change):
    settings, _, _ = hosted_settings
    with pytest.raises(RuntimeError):
        validate_data_settings(settings.model_copy(update=change))


@pytest.mark.parametrize(
    "change",
    [
        {"region": "us-east-1"},
        {"project_ref": "different"},
        {"checks": {}},
        {"schema_revision": "old"},
        {"boundary_version": "old"},
        {"verified_at": (datetime.now(UTC) - timedelta(days=8)).isoformat()},
        {"verified_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()},
        {"verified_at": "invalid"},
    ],
)
def test_missing_or_stale_attestation_blocks_startup(hosted_settings, change):
    settings, path, evidence = hosted_settings
    path.write_text(json.dumps({**evidence, **change}))
    with pytest.raises(RuntimeError, match="attestation"):
        validate_data_settings(settings)


@pytest.mark.parametrize(
    "key",
    [
        "not-a-key",
        "a.W10.b",
        "a.b.c",
        "a.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.b",
    ],
)
def test_hosted_runtime_rejects_invalid_and_privileged_legacy_keys(hosted_settings, key):
    settings, _, _ = hosted_settings
    with pytest.raises(RuntimeError, match="API key"):
        validate_data_settings(settings.model_copy(update={"supabase_anon_key": key}))


def test_hosted_auth_must_use_the_attested_projects_jwks(hosted_settings):
    settings, _, _ = hosted_settings
    with pytest.raises(RuntimeError, match="signing keys"):
        validate_data_settings(
            settings.model_copy(update={"supabase_jwks_url": "https://untrusted.example/jwks"})
        )


def test_connection_query_cannot_override_the_attested_host(hosted_settings):
    settings, _, _ = hosted_settings
    with pytest.raises(RuntimeError, match="attested Supabase"):
        validate_data_settings(
            settings.model_copy(
                update={"database_url": settings.database_url + "&host=foreign.example"}
            )
        )
