from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Medical Records Backend"
    environment: str = "local"
    database_url: str = Field(default="sqlite:///./med_app.db", repr=False)
    local_storage_root: str = ".local_storage"
    dev_auth_enabled: bool = True
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_jwks_url: str | None = None
    extraction_provider: str = "mock"
    extraction_run_inline: bool = True
    max_upload_bytes: int = 15_000_000
    data_backend: str = "local"
    supabase_project_ref: str | None = None
    supabase_region: str | None = None
    supabase_anon_key: str | None = None
    supabase_storage_bucket: str = "medical-records"
    supabase_attestation_path: str | None = None
    supabase_cleanup_database_url: str | None = Field(default=None, repr=False)
    production_data_enabled: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# decorator to indicate a cached function
@lru_cache
def get_settings() -> Settings:
    return Settings()
