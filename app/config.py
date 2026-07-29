from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

PRIVILEGED_DATABASE_USERS = {
    "postgres",
    "service_role",
    "supabase_admin",
}


class Settings(BaseSettings):
    app_name: str = "Medical Records Backend"
    environment: str = "local"
    database_url: str = "sqlite:///./med_app.db"
    migration_database_url: str | None = None
    database_connect_timeout_seconds: int = 10
    database_ssl_mode: str = "require"
    local_storage_root: str = ".local_storage"
    dev_auth_enabled: bool = True
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_jwks_url: str | None = None
    extraction_provider: str = "mock"
    extraction_run_inline: bool = True
    max_upload_bytes: int = 15_000_000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @model_validator(mode="after")
    def validate_production_data_boundary(self) -> "Settings":
        if not self.is_production:
            return self

        if self.dev_auth_enabled:
            raise ValueError("DEV_AUTH_ENABLED must be false in production.")
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL must be configured in production.")

        try:
            database_url = make_url(self.database_url)
        except Exception as exc:
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL in production.") from exc

        if database_url.get_backend_name() != "postgresql":
            raise ValueError(
                "DATABASE_URL must use Supabase PostgreSQL in production; "
                "SQLite fallback is not allowed."
            )
        if database_url.drivername not in {"postgresql", "postgresql+psycopg"}:
            raise ValueError("DATABASE_URL must use the synchronous psycopg driver in production.")

        username = (database_url.username or "").lower()
        privileged_user = username.split(".", 1)[0]
        if not username or privileged_user in PRIVILEGED_DATABASE_USERS:
            raise ValueError(
                "DATABASE_URL must use a dedicated non-privileged runtime database user "
                "in production."
            )

        if self.database_connect_timeout_seconds < 1:
            raise ValueError("DATABASE_CONNECT_TIMEOUT_SECONDS must be at least 1.")
        if self.database_ssl_mode not in {"require", "verify-ca", "verify-full"}:
            raise ValueError(
                "DATABASE_SSL_MODE must be require, verify-ca, or verify-full in production."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
