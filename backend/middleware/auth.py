"""Auth middleware: resolves the trestle_session cookie to request.state.user.

Anonymous users continue to work — request.state.user is None for them.
Authenticated users get a UserCtx bound to request.state.user, and user_id
is added to the structlog context for downstream logging.
"""
from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.core.config import get_settings
from backend.db.models.user import User, UserSession
from backend.db.session import get_db_factory
from backend.services.auth.identity import canonical_session_id_for_user
from backend.services.auth.tokens import hash_token


@dataclasses.dataclass
class UserCtx:
    id: uuid.UUID
    email: str
    email_normalized: str
    display_name: str | None


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        token = request.cookies.get(settings.AUTH_SESSION_COOKIE_NAME)
        request.state.user = None
        should_clear_cookie = False

        if token:
            try:
                token_hash = hash_token(token)
                now = datetime.now(timezone.utc)

                # Respect dep overrides so tests use the SQLite test DB.
                factory_dep = request.app.dependency_overrides.get(
                    get_db_factory, get_db_factory
                )
                factory = factory_dep()

                async with factory() as session:
                    result = await session.execute(
                        sa.select(UserSession, User)
                        .join(User, UserSession.user_id == User.id)
                        .where(
                            UserSession.session_token_hash == token_hash,
                            UserSession.revoked_at.is_(None),
                            UserSession.expires_at > now,
                        )
                    )
                    row = result.one_or_none()

                    if row is None:
                        should_clear_cookie = True
                    else:
                        user_session, user = row
                        request.state.user = UserCtx(
                            id=user.id,
                            email=user.email,
                            email_normalized=user.email_normalized,
                            display_name=user.display_name,
                        )
                        # Override session_id to the stable user-scoped identifier so
                        # all downstream queries work without branching on user-vs-anon.
                        # Preserve the original anon cookie value for the merge endpoint.
                        request.state.anon_session_id = getattr(
                            request.state, "session_id", None
                        )
                        request.state.session_id = canonical_session_id_for_user(user.id)
                        structlog.contextvars.bind_contextvars(user_id=str(user.id))

                        # Best-effort last_seen bump — stale by seconds is fine.
                        try:
                            user_session.last_seen_at = now
                            await session.commit()
                        except Exception:
                            pass

            except Exception:
                structlog.get_logger(__name__).exception("auth_middleware_error")
                should_clear_cookie = True

        response = await call_next(request)

        if should_clear_cookie:
            response.delete_cookie(
                settings.AUTH_SESSION_COOKIE_NAME,
                path="/",
                httponly=True,
                samesite="lax",
            )

        return response
