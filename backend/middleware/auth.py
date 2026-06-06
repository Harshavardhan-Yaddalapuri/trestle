"""Supabase JWT validation middleware.

Verifies `Authorization: Bearer *** headers using Supabase's JWKS.
Sets `request.state.user_id` to the Supabase `sub` claim when valid.
Anonymous requests (no header) are allowed through — session cookie still
provides `request.state.session_id` from SessionMiddleware.
"""
from __future__ import annotations

import jwt
import sqlalchemy as sa
from jwt import PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.core.config import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

# Lazy-loaded JWKS client (cached per process).
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        # Supabase exposes JWKS at /auth/v1/.well-known/jwks.json
        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True, cache_jwk_set=True)
    return _jwks_client


def get_identity(request: Request) -> tuple[str | None, str]:
    """Return (user_id, session_id) from request state."""
    user_id = getattr(request.state, "user_id", None)
    session_id = getattr(request.state, "session_id", "")
    return user_id, session_id


def owner_clause(column_user_id, column_session_id, request: Request):
    """Return a SQLAlchemy clause that matches either user_id (if authenticated)
    or session_id (anonymous fallback)."""
    user_id, session_id = get_identity(request)
    if user_id:
        return sa.or_(column_user_id == user_id, column_session_id == session_id)
    return column_session_id == session_id


def _verify_token(token: str) -> dict:
    """Verify a Supabase JWT and return its payload dict.

    Raises jwt.ExpiredSignatureError, jwt.InvalidTokenError, etc.
    """
    jwks_client = _get_jwks_client()
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience="authenticated",
        options={"require": ["exp", "iat", "sub"]},
    )
    return payload


class SupabaseAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token:
                try:
                    payload = _verify_token(token)
                    user_id = payload.get("sub")
                    if user_id:
                        request.state.user_id = user_id
                except jwt.ExpiredSignatureError:
                    request.state.auth_error = "expired_token"
                except jwt.InvalidTokenError as exc:
                    logger.warning("invalid_jwt", error=str(exc))
                    request.state.auth_error = "invalid_token"
                except Exception as exc:  # noqa: BLE001
                    logger.warning("jwt_verification_error", error=str(exc))
                    request.state.auth_error = "verification_failed"
        return await call_next(request)
