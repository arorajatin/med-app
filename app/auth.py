from functools import lru_cache
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from app.config import Settings, get_settings
from app.schemas import CurrentUser


def _bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def _dev_user(request: Request) -> CurrentUser | None:
    user_id = request.headers.get("x-user-id") or _bearer_token(request)
    if not user_id:
        return None
    return CurrentUser(id=user_id)


def _supabase_issuer(settings: Settings) -> str:
    assert settings.supabase_url is not None
    return f"{settings.supabase_url.rstrip('/')}/auth/v1"


def _supabase_jwks_url(settings: Settings) -> str:
    if settings.supabase_jwks_url:
        return settings.supabase_jwks_url
    return f"{_supabase_issuer(settings)}/.well-known/jwks.json"


@lru_cache(maxsize=8)
def _jwk_client(jwks_url: str):
    from jwt import PyJWKClient

    return PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=600)


def _verify_supabase_jwt(token: str, settings: Settings) -> CurrentUser:
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_URL must be configured when DEV_AUTH_ENABLED=false.",
        )

    try:
        import jwt
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PyJWT with crypto support is required for Supabase JWT verification.",
        ) from exc

    try:
        jwk_client = _jwk_client(_supabase_jwks_url(settings))
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.supabase_jwt_audience,
            issuer=_supabase_issuer(settings),
            options={"require": ["exp", "iss", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Supabase access token.",
        ) from exc

    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supabase access token is missing a subject.",
        )

    try:
        normalized_user_id = str(UUID(user_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supabase access token subject must be a UUID.",
        ) from exc

    return CurrentUser(id=normalized_user_id)


# definitive method
# _bearer_token -> extraction method
# _verify_supbase_jwt -> verification method
# _jwk_client -> jwks_client -> lru cache using supabase JWK URL
# signing_key -> extracted by jwk_client
# claims -> extracted from token, signing_key, audience, issuer, options
def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if settings.dev_auth_enabled:
        user = _dev_user(request)
        if user is not None:
            return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing local auth user. Send Authorization: Bearer <user_id>.",
        )

    token = _bearer_token(request)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Supabase access token. Send Authorization: Bearer <jwt>.",
        )

    return _verify_supabase_jwt(token, settings)
