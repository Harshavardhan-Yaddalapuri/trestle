"""Supabase JWT validation middleware.

Verifies `Authorization: Bearer <jwt>` headers using Supabase's JWKS.
Sets `request.state.user_id` to the Supabase `sub` claim when valid,
and binds a Supabase-shaped `UserCtx` to `request.state.user` so
existing dependencies (require_user) keep working.
Anonymous requests (no header) are allowed through — the session
middleware still provides `request.state.session_id`.
"""
from __future__ import annotations

import dataclasses
import uuid

import jwt
import sqlalchemy as sa
import structlog
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


@dataclasses.dataclass
class UserCtx:
    """Supabase-shaped authenticated user context.

    The `id` field is the Supabase `sub` claim parsed to a UUID when
    possible. Email fields come from the JWT's `email` / `email_verified`
    claims. `display_name` is not part of the standard Supabase token,
    so it is left None here and resolved from the `users` table by
    the calling endpoint if it needs more.

    `email_normalized` is the lowercased email; it is exposed for
    future lookup-by-email flows (e.g. cross-account merge) but is
    not currently persisted on the `users` row (0015 stores raw
    `email`). Callers that need to match by email should normalize
    on the fly until a migration adds the column.
    """

    id: uuid.UUID
    sub: str
    email: str | None
    email_normalized: str | None
    email_verified: bool
    display_name: str | None = None


def _build_user_ctx(payload: dict) -> UserCtx:
    sub = payload.get("sub") or ""
    email = payload.get("email")
    email_verified = bool(payload.get("email_verified"))
    try:
        uid = uuid.UUID(sub)
    except (ValueError, TypeError):
        # Fall back to a deterministic UUIDv5 from the sub so the
        # downstream user table can use it as a stable FK.
        uid = uuid.uuid5(uuid.NAMESPACE_URL, f"supabase:{sub}")
    return UserCtx(
        id=uid,
        sub=sub,
        email=email,
        email_normalized=email.lower() if email else None,
        email_verified=email_verified,
        display_name=None,
    )


class SupabaseAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token:
                try:
                    payload = _verify_token(token)
                    sub = payload.get("sub")
                    if sub:
                        request.state.user_id = sub
                        request.state.user = _build_user_ctx(payload)
                        structlog.contextvars.bind_contextvars(user_id=sub)
                except jwt.ExpiredSignatureError:
                    request.state.auth_error = "expired_token"
                except jwt.InvalidTokenError as exc:
                    logger.warning("invalid_jwt", error=str(exc))
                    request.state.auth_error = "invalid_token"
                except Exception as exc:  # noqa: BLE001
                    logger.warning("jwt_verification_error", error=str(exc))
                    request.state.auth_error = "verification_failed"
        return await call_next(request)


__all__ = [
    "SupabaseAuthMiddleware",
    "UserCtx",
    "get_identity",
    "owner_clause",
]
