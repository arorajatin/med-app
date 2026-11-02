import runpy
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.data_boundary import validate_data_settings
from app.storage_cleanup import reconcile_uploads

PROJECT = "abcdefghijklmnopqrst"


@pytest.fixture()
def cleanup_settings():
    return Settings(
        _env_file=None,
        data_backend="supabase",
        environment="production",
        dev_auth_enabled=False,
        database_url="",
        supabase_cleanup_database_url=(
            f"postgresql://med_app_cleanup:cleanup-password@db.{PROJECT}.supabase.co"
            "/postgres?sslmode=verify-full"
        ),
        supabase_url=f"https://{PROJECT}.supabase.co",
        supabase_project_ref=PROJECT,
        supabase_region="ap-southeast-1",
        supabase_anon_key="sb_publishable_test",
        production_data_enabled=False,
        extraction_provider="disabled",
        extraction_run_inline=False,
    )


def idle_cleanup_engine():
    engine = MagicMock()
    result = engine.begin.return_value.__enter__.return_value.execute.return_value
    result.scalar_one.return_value = {
        "login": "med_app_cleanup",
        "roles_safe": True,
        "project_ref": PROJECT,
        "region": "ap-southeast-1",
        "bucket_private": True,
    }
    result.scalars.return_value.all.return_value = []
    return engine


@pytest.mark.parametrize("pooled", [False, True])
def test_cleanup_connects_without_api_credentials(cleanup_settings, monkeypatch, pooled):
    if pooled:
        cleanup_settings.supabase_cleanup_database_url = (
            f"postgresql://med_app_cleanup.{PROJECT}:cleanup-password"
            "@aws-0-ap-southeast-1.pooler.supabase.com/postgres?sslmode=verify-full"
        )
    connect = MagicMock(return_value=idle_cleanup_engine())
    monkeypatch.setattr("app.storage_cleanup.create_engine", connect)
    assert reconcile_uploads(cleanup_settings) == (0, 0)
    url = connect.call_args.args[0]
    assert url.username == "med_app_cleanup" + (f".{PROJECT}" if pooled else "")
    assert url.password == "cleanup-password"


@pytest.mark.parametrize(
    "url",
    [
        None,
        "sqlite:///cleanup.db",
        f"postgresql://med_app_api:password@db.{PROJECT}.supabase.co/postgres?sslmode=verify-full",
        "postgresql://med_app_cleanup:password@db.zyxwvutsrqponmlkjihg.supabase.co/postgres?sslmode=verify-full",
        f"postgresql://med_app_cleanup.{PROJECT}:password@aws-0-us-east-1.pooler.supabase.com/postgres?sslmode=verify-full",
        "postgresql://med_app_cleanup.zyxwvutsrqponmlkjihg:password@aws-0-ap-southeast-1.pooler.supabase.com/postgres?sslmode=verify-full",
        f"postgresql://med_app_cleanup:password@db.{PROJECT}.supabase.co/other?sslmode=verify-full",
        f"postgresql://med_app_cleanup@db.{PROJECT}.supabase.co/postgres?sslmode=verify-full",
        f"postgresql://med_app_cleanup:password@db.{PROJECT}.supabase.co/postgres?sslmode=require",
        f"postgresql://med_app_cleanup:password@db.{PROJECT}.supabase.co/postgres?sslmode=verify-full&host=foreign.example",
    ],
)
def test_cleanup_rejects_invalid_connection_before_connecting(cleanup_settings, monkeypatch, url):
    connect = MagicMock()
    monkeypatch.setattr("app.storage_cleanup.create_engine", connect)
    cleanup_settings.supabase_cleanup_database_url = url
    with pytest.raises(RuntimeError):
        reconcile_uploads(cleanup_settings)
    connect.assert_not_called()


def test_api_validation_still_rejects_cleanup_credentials(cleanup_settings):
    cleanup_settings.database_url = cleanup_settings.supabase_cleanup_database_url
    with pytest.raises(RuntimeError, match="med_app_api"):
        validate_data_settings(cleanup_settings, require_admission=False)


def test_cleanup_command_does_not_load_api_dotenv(tmp_path, monkeypatch):
    script = Path(__file__).resolve().parents[1] / "app/storage_cleanup.py"
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    (tmp_path / ".env").write_text("DATABASE_URL=api-secret-from-local-env\n")
    for key, value in {
        "DATA_BACKEND": "supabase",
        "DEV_AUTH_ENABLED": "false",
        "SUPABASE_CLEANUP_DATABASE_URL": (
            f"postgresql://med_app_cleanup:password@db.{PROJECT}.supabase.co"
            "/postgres?sslmode=verify-full"
        ),
        "SUPABASE_URL": f"https://{PROJECT}.supabase.co",
        "SUPABASE_PROJECT_REF": PROJECT,
        "SUPABASE_REGION": "ap-southeast-1",
        "SUPABASE_ANON_KEY": "sb_publishable_test",
        "EXTRACTION_PROVIDER": "disabled",
        "EXTRACTION_RUN_INLINE": "false",
    }.items():
        monkeypatch.setenv(key, value)
    loaded = []

    def load_settings(**kwargs):
        settings = Settings(**kwargs)
        loaded.append(settings)
        return settings

    monkeypatch.setattr("app.config.Settings", load_settings)
    monkeypatch.setattr("sqlalchemy.create_engine", lambda *args, **kwargs: idle_cleanup_engine())
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(script), run_name="__main__")
    assert exit_info.value.code == 0
    assert len(loaded) == 1
    assert loaded[0].database_url == "sqlite:///./med_app.db"
