from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.data_boundary import validate_data_settings, verify_database_boundary
from app.database import configure_database, get_engine, require_current_database_schema


def create_app() -> FastAPI:
    settings = get_settings()

    # Decorator syntax to wrap the following function into asynccontextmanager
    # FastAPI knows how to work with the asynccontextmanager and will call it on startup and shutdown
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        validate_data_settings(settings)
        configure_database(settings.database_url)
        if settings.environment != "test":
            require_current_database_schema()
        verify_database_boundary(get_engine(), settings)
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
