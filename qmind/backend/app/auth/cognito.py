"""Cognito OIDC JWT validation (ADR-006)."""

from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

from app.config import Settings, get_settings
from app.errors import AppError

_jwks_client: PyJWKClient | None = None
_jwks_loaded_at: float = 0.0
_JWKS_TTL_SEC = 3600.0


def _get_jwks_client(settings: Settings) -> PyJWKClient:
    global _jwks_client, _jwks_loaded_at
    now = time.time()
    if _jwks_client is None or (now - _jwks_loaded_at) > _JWKS_TTL_SEC:
        # Warm check — fail fast if pool misconfigured
        with httpx.Client(timeout=5.0) as client:
            r = client.get(settings.cognito_jwks_url)
            r.raise_for_status()
        _jwks_client = PyJWKClient(settings.cognito_jwks_url)
        _jwks_loaded_at = now
    return _jwks_client


def decode_cognito_access_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    if not settings.cognito_user_pool_id or not settings.cognito_app_client_id:
        raise AppError(
            "auth_misconfigured",
            "Cognito is not configured",
            status_code=500,
        )
    try:
        jwks = _get_jwks_client(settings)
        key = jwks.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            audience=settings.cognito_app_client_id,
            issuer=settings.cognito_issuer,
            options={"require": ["exp", "iss", "sub"]},
        )
    except AppError:
        raise
    except Exception as exc:
        raise AppError("invalid_token", "Invalid or expired access token", status_code=401) from exc
