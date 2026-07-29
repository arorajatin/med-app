import pytest
from pydantic import ValidationError

from app.config import Settings


def production_settings(**overrides) -> Settings:
    values = {
        "environment": "production",
        "database_url": (
            "postgresql+psycopg://med_app_api:runtime-secret@db.example.test:5432/postgres"
        ),
        "migration_database_url": (
            "postgresql+psycopg://postgres:migration-secret@db.example.test:5432/postgres"
        ),
        "dev_auth_enabled": False,
        "supabase_url": "https://example.supabase.co",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_accepts_a_dedicated_postgres_runtime_user():
    settings = production_settings()

    assert settings.is_production
    assert settings.database_url.startswith("postgresql+psycopg://med_app_api:")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"database_url": "sqlite:///./med_app.db"}, "SQLite fallback is not allowed"),
        ({"dev_auth_enabled": True}, "DEV_AUTH_ENABLED must be false"),
        ({"supabase_url": None}, "SUPABASE_URL must be configured"),
        (
            {"database_url": ("postgresql+asyncpg://med_app_api:secret@db.example.test/postgres")},
            "synchronous psycopg driver",
        ),
        (
            {
                "database_url": (
                    "postgresql+psycopg://postgres.project-ref:secret@db.example.test/postgres"
                )
            },
            "dedicated non-privileged runtime database user",
        ),
        (
            {"database_ssl_mode": "disable"},
            "DATABASE_SSL_MODE must be require, verify-ca, or verify-full",
        ),
    ],
)
def test_production_rejects_unsafe_database_configuration(overrides, message):
    with pytest.raises(ValidationError, match=message):
        production_settings(**overrides)
