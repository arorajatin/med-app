from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jwt.exceptions import PyJWKClientError

from app import auth as auth_module
from app.auth import get_current_user
from app.config import Settings, get_settings
from app.schemas import CurrentUser

SUPABASE_URL = "https://demo.supabase.co"
SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1"
INVALID_TOKEN_DETAIL = "Invalid Supabase access token."


@pytest.fixture(autouse=True)
def clear_jwk_client_cache():
    auth_module._jwk_client.cache_clear()
    yield
    auth_module._jwk_client.cache_clear()


@pytest.fixture(scope="module", params=["RS256", "ES256"])
def signing_material(request):
    algorithm = request.param
    if algorithm == "RS256":
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    else:
        private_key = ec.generate_private_key(ec.SECP256R1())
        jwk = jwt.algorithms.ECAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk.update({"alg": algorithm, "kid": f"test-{algorithm.casefold()}", "use": "sig"})
    return algorithm, private_key, jwk


def production_settings(**overrides) -> Settings:
    values = {
        "dev_auth_enabled": False,
        "supabase_url": SUPABASE_URL,
        "supabase_jwt_audience": "authenticated",
        "supabase_jwks_url": None,
    }
    values.update(overrides)
    return Settings(**values)


def token_claims(**overrides) -> dict:
    claims = {
        "sub": "user_123",
        "iss": SUPABASE_ISSUER,
        "aud": "authenticated",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    claims.update(overrides)
    return claims


def sign_token(private_key, algorithm: str, kid: str, **claim_overrides) -> str:
    return jwt.encode(
        token_claims(**claim_overrides),
        private_key,
        algorithm=algorithm,
        headers={"kid": kid},
    )


def install_jwks(monkeypatch, jwk: dict) -> None:
    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", lambda self: {"keys": [jwk]})


def make_auth_client(settings: Settings) -> TestClient:
    app = FastAPI()

    @app.get("/current-user")
    def current_user_real(user: CurrentUser = Depends(get_current_user)):
        return {"id": user.id}

    @app.get("/identity")
    def identity(user: CurrentUser = Depends(get_current_user)):
        return user.model_dump()

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


def test_dev_auth_rejects_missing_credentials():
    client = make_auth_client(Settings(dev_auth_enabled=True))

    response = client.get("/current-user")

    assert response.status_code == 401
    assert (
        response.json()["detail"]
        == "Missing local auth user. Send Authorization: Bearer <user_id>."
    )


def test_dev_auth_rejects_blank_credentials():
    client = make_auth_client(Settings(dev_auth_enabled=True))

    assert client.get("/current-user", headers={"X-User-Id": ""}).status_code == 401
    assert client.get("/current-user", headers={"Authorization": "Bearer "}).status_code == 401


def test_production_auth_requires_bearer_token():
    client = make_auth_client(
        Settings(dev_auth_enabled=False, supabase_url="https://demo.supabase.co")
    )

    response = client.get("/current-user")

    assert response.status_code == 401
    assert (
        response.json()["detail"]
        == "Missing Supabase access token. Send Authorization: Bearer <jwt>."
    )


def test_production_auth_requires_supabase_url():
    client = make_auth_client(Settings(dev_auth_enabled=False, supabase_url=None))

    response = client.get("/current-user", headers={"Authorization": "Bearer not-a-real-jwt"})

    assert response.status_code == 500
    assert (
        response.json()["detail"] == "SUPABASE_URL must be configured when DEV_AUTH_ENABLED=false."
    )


def test_production_auth_accepts_supported_signed_tokens(monkeypatch, signing_material):
    algorithm, private_key, jwk = signing_material
    install_jwks(monkeypatch, jwk)
    token = sign_token(private_key, algorithm, jwk["kid"])

    response = make_auth_client(production_settings()).get(
        "/current-user", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"id": "user_123"}


@pytest.mark.parametrize(
    "claim_overrides",
    [
        {"exp": datetime.now(UTC) - timedelta(minutes=1)},
        {"iss": "https://attacker.example/auth/v1"},
        {"aud": "service_role"},
    ],
    ids=["expired", "wrong-issuer", "wrong-audience"],
)
def test_production_auth_rejects_invalid_registered_claims(
    monkeypatch, signing_material, claim_overrides
):
    algorithm, private_key, jwk = signing_material
    install_jwks(monkeypatch, jwk)
    token = sign_token(private_key, algorithm, jwk["kid"], **claim_overrides)

    response = make_auth_client(production_settings()).get(
        "/current-user", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": INVALID_TOKEN_DETAIL}


def test_production_auth_rejects_token_signed_by_unknown_key(monkeypatch, signing_material):
    algorithm, _, jwk = signing_material
    if algorithm == "RS256":
        unknown_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    else:
        unknown_private_key = ec.generate_private_key(ec.SECP256R1())
    install_jwks(monkeypatch, jwk)
    token = sign_token(unknown_private_key, algorithm, jwk["kid"])

    response = make_auth_client(production_settings()).get(
        "/current-user", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": INVALID_TOKEN_DETAIL}


def test_production_auth_rejects_missing_expiration(monkeypatch, signing_material):
    algorithm, private_key, jwk = signing_material
    install_jwks(monkeypatch, jwk)
    claims = token_claims()
    claims.pop("exp")
    token = jwt.encode(
        claims,
        private_key,
        algorithm=algorithm,
        headers={"kid": jwk["kid"]},
    )

    response = make_auth_client(production_settings()).get(
        "/current-user", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": INVALID_TOKEN_DETAIL}


def test_production_auth_rejects_blank_subject(monkeypatch, signing_material):
    algorithm, private_key, jwk = signing_material
    install_jwks(monkeypatch, jwk)
    token = sign_token(private_key, algorithm, jwk["kid"], sub="")

    response = make_auth_client(production_settings()).get(
        "/current-user", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Supabase access token is missing a subject."}


def test_production_auth_rejects_token_when_jwks_is_unavailable(monkeypatch, signing_material):
    algorithm, private_key, jwk = signing_material

    def fail_fetch(self):
        raise PyJWKClientError("JWKS endpoint unavailable")

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fail_fetch)
    token = sign_token(private_key, algorithm, jwk["kid"])

    response = make_auth_client(production_settings()).get(
        "/current-user", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": INVALID_TOKEN_DETAIL}


def test_production_auth_rejects_malformed_token():
    response = make_auth_client(production_settings()).get(
        "/current-user", headers={"Authorization": "Bearer not-a-jwt"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": INVALID_TOKEN_DETAIL}


def test_production_auth_carries_google_sign_in_provenance(monkeypatch, signing_material):
    """A Google sign-in reports the verified address and the method that proved it."""

    algorithm, private_key, jwk = signing_material
    install_jwks(monkeypatch, jwk)
    token = sign_token(
        private_key,
        algorithm,
        jwk["kid"],
        email="asha@example.com",
        app_metadata={"provider": "google", "providers": ["google"]},
    )

    response = make_auth_client(production_settings()).get(
        "/identity", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "user_123",
        "email": "asha@example.com",
        "upstream_provider": "google",
    }


def test_production_auth_ignores_user_writable_metadata(monkeypatch, signing_material):
    """`user_metadata` is writable by the account holder, so it never proves anything."""

    algorithm, private_key, jwk = signing_material
    install_jwks(monkeypatch, jwk)
    token = sign_token(
        private_key,
        algorithm,
        jwk["kid"],
        user_metadata={"provider": "google", "email": "attacker@example.com"},
    )

    response = make_auth_client(production_settings()).get(
        "/identity", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"id": "user_123", "email": None, "upstream_provider": None}


def test_production_auth_tolerates_a_malformed_app_metadata_claim(monkeypatch, signing_material):
    """A token without the usual claim shapes still authenticates on its subject."""

    algorithm, private_key, jwk = signing_material
    install_jwks(monkeypatch, jwk)
    token = sign_token(private_key, algorithm, jwk["kid"], email="", app_metadata="not-an-object")

    response = make_auth_client(production_settings()).get(
        "/identity", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"id": "user_123", "email": None, "upstream_provider": None}
