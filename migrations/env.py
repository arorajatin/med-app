from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

from app import models  # noqa: F401
from app.config import get_settings
from app.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def normalize_database_url(database_url: str) -> str:
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    elif url.get_backend_name() == "postgresql" and url.drivername != "postgresql+psycopg":
        raise RuntimeError("PostgreSQL migrations must use the synchronous psycopg driver.")
    return url.render_as_string(hide_password=False)


def get_database_url() -> str:
    configured_url = config.attributes.get("database_url")
    if configured_url is not None:
        return normalize_database_url(str(configured_url))

    settings = get_settings()
    if settings.is_production:
        if not settings.migration_database_url:
            raise RuntimeError(
                "MIGRATION_DATABASE_URL is required to run migrations in production."
            )
        return normalize_database_url(settings.migration_database_url)
    return normalize_database_url(settings.migration_database_url or settings.database_url)


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
