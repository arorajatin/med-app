from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Medical Records Backend"
    environment: str = "local"
    database_url: str = "sqlite:///./med_app.db"
    local_storage_root: str = ".local_storage"
    dev_auth_enabled: bool = True
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_jwks_url: str | None = None
    extraction_provider: str = "mock"
    extraction_run_inline: bool = True
    max_upload_bytes: int = 15_000_000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# decorator to indicate a cached function
@lru_cache
def get_settings() -> Settings:
    return Settings()
