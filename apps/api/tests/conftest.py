import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import Base, bootstrap_test_database, configure_database, get_engine
from app.main import create_app

DEFAULT_TEST_ENV = {
    "ENVIRONMENT": "test",
    "DEV_AUTH_ENABLED": "true",
    "EXTRACTION_RUN_INLINE": "true",
}


@pytest.fixture()
def make_client(tmp_path, monkeypatch):
    """Build a test client on a fresh database, with overridable settings."""

    started: list[TestClient] = []

    def factory(**overrides: str) -> TestClient:
        get_settings.cache_clear()
        database_url = f"sqlite:///{tmp_path / 'test.db'}"
        environment = {
            **DEFAULT_TEST_ENV,
            "DATABASE_URL": database_url,
            "LOCAL_STORAGE_ROOT": str(tmp_path / "storage"),
            **overrides,
        }
        for key, value in environment.items():
            monkeypatch.setenv(key, value)
        configure_database(database_url)
        Base.metadata.drop_all(bind=get_engine())
        bootstrap_test_database()
        test_client = TestClient(create_app())
        test_client.__enter__()
        started.append(test_client)
        return test_client

    yield factory
    for test_client in started:
        test_client.__exit__(None, None, None)
    get_settings.cache_clear()


@pytest.fixture()
def client(make_client) -> TestClient:
    return make_client()
