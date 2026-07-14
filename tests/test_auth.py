from fastapi import FastAPI
from fastapi import Depends
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.schemas import CurrentUser


def make_auth_client(settings: Settings) -> TestClient:
    app = FastAPI()

    @app.get("/current-user")
    def current_user_real(user: CurrentUser = Depends(get_current_user)):
        return {"id": user.id}

    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_dev_auth_accepts_bearer_user_id():
    client = make_auth_client(Settings(dev_auth_enabled=True))

    response = client.get("/current-user", headers={"Authorization": "Bearer user_123"})

    assert response.status_code == 200
    assert response.json() == {"id": "user_123"}


def test_dev_auth_accepts_x_user_id():
    client = make_auth_client(Settings(dev_auth_enabled=True))

    response = client.get("/current-user", headers={"X-User-Id": "user_123"})

    assert response.status_code == 200
    assert response.json() == {"id": "user_123"}


def test_production_auth_requires_bearer_token():
    client = make_auth_client(Settings(dev_auth_enabled=False, supabase_url="https://demo.supabase.co"))

    response = client.get("/current-user")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing Supabase access token. Send Authorization: Bearer <jwt>."


def test_production_auth_requires_supabase_url():
    client = make_auth_client(Settings(dev_auth_enabled=False, supabase_url=None))

    response = client.get("/current-user", headers={"Authorization": "Bearer not-a-real-jwt"})

    assert response.status_code == 500
    assert response.json()["detail"] == "SUPABASE_URL must be configured when DEV_AUTH_ENABLED=false."
