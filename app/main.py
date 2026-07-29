from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.database import (
    configure_database,
    dispose_database,
    require_current_database_schema,
    require_safe_production_database_role,
)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_database(settings=settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            if settings.environment != "test":
                require_safe_production_database_role()
                require_current_database_schema()
            yield
        finally:
            dispose_database()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
