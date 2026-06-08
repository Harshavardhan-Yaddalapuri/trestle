"""Auth endpoints.

The Trestle backend delegates authentication to Supabase (JWT in the
`Authorization: Bearer` header). `SupabaseAuthMiddleware` validates the
token and binds a `UserCtx` to `request.state.user`. This router exposes
the current authenticated user via `GET /auth/me`.

There is no signup / login / logout / magic-link / merge-session / anonymous-session
endpoints here — those flows live in Supabase (and the frontend talks to
Supabase directly for them). The backend's job is to read the JWT and
return what we know about the user from our own tables.
"""
from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import AuthenticationError
from backend.core.logging import get_logger
from backend.db.models.user import User
from backend.db.session import get_db
from backend.middleware.auth import UserCtx

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


def _require_user(request: Request) -> UserCtx:
    """Dependency: returns the UserCtx bound by SupabaseAuthMiddleware.

    Raises 401 if no authenticated user is on the request.
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthenticationError("Authentication required")
    return user


@router.get("/me")
async def get_me(
    request: Request,
    current_user: UserCtx = Depends(_require_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the currently authenticated user.

    Provisions a `users` row on first read (idempotent) so downstream
    endpoints can assume the row exists. This is the only place we
    create a user implicitly; the alert-prefs PUT also provisions
    if a user hits that endpoint before /me, so the two paths stay
    consistent.
    """
    result = await db.execute(sa.select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if user is None:
        # Provisioning-on-read: create the users row so downstream endpoints
        # can assume it exists.
        user = User(
            id=current_user.id,
            sub=current_user.sub,
            email=current_user.email,
            alert_prefs={},
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("user_provisioned", sub=current_user.sub)

    return {
        "id": str(user.id),
        "sub": user.sub,
        "email": user.email,
        "email_verified": current_user.email_verified,
        "alert_prefs": user.alert_prefs,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }
