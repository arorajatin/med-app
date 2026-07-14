from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.database import configure_database, init_db


def create_app() -> FastAPI:
    settings = get_settings()
    configure_database(settings.database_url)

    # Decorator syntax to wrap the following function into asynccontextmanager
    # FastAPI knows how to work with the asynccontextmanager and will call it on startup and shutdown
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db()
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
