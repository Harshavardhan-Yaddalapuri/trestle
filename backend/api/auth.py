"""Magic-link authentication endpoints.

No passwords. No OAuth. Just:
  POST /auth/magic-link/send   → issues a token, logs "would send email"
  POST /auth/magic-link/verify → validates token, creates session cookie
  GET  /auth/me                → returns current user
  POST /auth/logout            → revokes current session
  POST /auth/logout/all        → revokes all sessions for the user
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
import structlog
from fastapi import APIRouter, Depends, Request, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import Settings, get_settings
from backend.core.errors import AuthenticationError, ConflictError, RateLimitError, UpstreamError, ValidationError
from backend.core.logging import get_logger
from backend.db.models.user import User, UserSession
from backend.db.session import get_db
from backend.middleware.auth import UserCtx
from backend.redis_client import get_redis
from backend.schemas.auth import (
    MagicLinkSendIn,
    MagicLinkSendOut,
    MagicLinkVerifyIn,
    MagicLinkVerifyOut,
    MergeSessionIn,
    MergeSessionOut,
    UserOut,
)
from backend.services.auth.identity import is_user_session_id
from backend.services.auth.merge import merge_anonymous_session
from backend.services.auth.tokens import (
    generate_magic_link_token,
    generate_session_token,
    hash_ip,
    hash_token,
)
from backend.services.email.base import EmailClient
from backend.services.email.dependency import get_email_client
from backend.services.email.templates import render_email

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)

_MAGIC_REDIS_PREFIX = "auth:magic:"
_RATELIMIT_EMAIL_PREFIX = "auth:ratelimit:send:"
_RATELIMIT_IP_PREFIX = "auth:ratelimit:send:ip:"
_RATELIMIT_MERGE_PREFIX = "auth:ratelimit:merge:"


async def require_user(request: Request) -> UserCtx:
    """FastAPI dependency — raises 401 if not authenticated."""
    if request.state.user is None:
        raise AuthenticationError()
    return request.state.user


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        email_verified=user.email_verified_at is not None,
        display_name=user.display_name,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def _check_and_increment_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
) -> tuple[bool, int]:
    """Increment key (creating with 1h TTL on first call). Returns (over_limit, ttl_remaining)."""
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 3600)
    ttl = await redis.ttl(key)
    return current > limit, max(ttl, 0)


@router.post("/magic-link/send", response_model=MagicLinkSendOut)
async def send_magic_link(
    body: MagicLinkSendIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
    email_client: EmailClient = Depends(get_email_client),
) -> MagicLinkSendOut:
    email_normalized = str(body.email).lower().strip()
    client_ip = _get_client_ip(request)
    pepper = settings.AUTH_IP_HASH_PEPPER.get_secret_value()
    ip_hash = hash_ip(client_ip, pepper) if pepper else hash_ip(client_ip, "dev")

    email_key = f"{_RATELIMIT_EMAIL_PREFIX}{email_normalized}"
    ip_key = f"{_RATELIMIT_IP_PREFIX}{ip_hash}"

    over_email, email_ttl = await _check_and_increment_rate_limit(
        redis, email_key, settings.AUTH_MAGIC_LINK_SEND_PER_HOUR
    )
    over_ip, ip_ttl = await _check_and_increment_rate_limit(
        redis, ip_key, settings.AUTH_MAGIC_LINK_SEND_PER_HOUR_PER_IP
    )

    if over_email or over_ip:
        retry_after = email_ttl if over_email else ip_ttl
        raise RateLimitError(
            "Too many magic link requests. Please wait before trying again.",
            code="rate_limited",
            extra={"retry_after": retry_after},
        )

    token, token_hash = generate_magic_link_token()
    anon_session_id = getattr(request.state, "session_id", None)

    magic_payload = json.dumps({
        "email": str(body.email),
        "email_normalized": email_normalized,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "attempts": 0,
        "anon_session_id": anon_session_id,
    })
    await redis.set(
        f"{_MAGIC_REDIS_PREFIX}{token_hash}",
        magic_payload,
        ex=settings.AUTH_MAGIC_LINK_TTL_SECONDS,
    )

    magic_url = (
        f"{settings.AUTH_BASE_URL}{settings.AUTH_MAGIC_LINK_PATH}?token={token}"
    )
    rendered = render_email("magic_link", {
        "magic_url": magic_url,
        "app_name": settings.EMAIL_FROM_NAME,
        "ttl_minutes": settings.AUTH_MAGIC_LINK_TTL_SECONDS // 60,
    })

    try:
        await email_client.send(
            to=str(body.email),
            subject=rendered.subject,
            html=rendered.html,
            text=rendered.text,
            tags=["magic_link"],
        )
    except UpstreamError:
        raise UpstreamError(
            "Email service temporarily unavailable. Please try again later.",
            code="email_unavailable",
            status_code=503,
        )

    logger.info(
        "magic_link_sent",
        email_normalized=email_normalized,
        ttl=settings.AUTH_MAGIC_LINK_TTL_SECONDS,
    )

    return MagicLinkSendOut(
        sent=True,
        expires_in_seconds=settings.AUTH_MAGIC_LINK_TTL_SECONDS,
    )


@router.post("/magic-link/verify", response_model=MagicLinkVerifyOut)
async def verify_magic_link(
    body: MagicLinkVerifyIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> MagicLinkVerifyOut:
    token_hash = hash_token(body.token)
    redis_key = f"{_MAGIC_REDIS_PREFIX}{token_hash}"

    raw = await redis.get(redis_key)
    if raw is None:
        raise AuthenticationError(
            "Invalid or expired token",
            code="invalid_or_expired_token",
        )

    payload = json.loads(raw)

    # Increment attempts for telemetry (does not gate verification in v1).
    attempts = payload.get("attempts", 0) + 1
    payload["attempts"] = attempts
    ttl = await redis.ttl(redis_key)
    if ttl > 0:
        await redis.set(redis_key, json.dumps(payload), ex=ttl)

    email_normalized = payload["email_normalized"]
    email_original = payload.get("email", email_normalized)

    now = datetime.now(timezone.utc)

    # Find or create the user.
    result = await db.execute(
        sa.select(User).where(User.email_normalized == email_normalized)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email_original,
            email_normalized=email_normalized,
            email_verified_at=now,
            created_at=now,
            updated_at=now,
            alert_unsubscribe_token=secrets.token_urlsafe(32),
        )
        db.add(user)
        await db.flush()
        logger.info("user_created", user_id=str(user.id), email_normalized=email_normalized)
    else:
        if user.email_verified_at is None:
            user.email_verified_at = now
        user.last_login_at = now
        user.updated_at = now
        await db.flush()

    if user.disabled_at is not None:
        await db.rollback()
        raise AuthenticationError(
            "This account has been disabled",
            code="user_disabled",
            status_code=403,
        )

    # Single-use: delete the magic link token.
    await redis.delete(redis_key)

    # Issue session.
    session_token, session_hash = generate_session_token()
    expires_at = now + timedelta(days=settings.AUTH_SESSION_TTL_DAYS)

    user_agent = request.headers.get("User-Agent")
    client_ip = _get_client_ip(request)
    pepper = settings.AUTH_IP_HASH_PEPPER.get_secret_value()
    ip_h = hash_ip(client_ip, pepper) if pepper else hash_ip(client_ip, "dev")

    user_session = UserSession(
        user_id=user.id,
        session_token_hash=session_hash,
        issued_at=now,
        expires_at=expires_at,
        last_seen_at=now,
        user_agent=user_agent[:500] if user_agent else None,
        ip_hash=ip_h,
    )
    db.add(user_session)
    await db.commit()
    # No refresh needed: expire_on_commit=False keeps user attributes valid.

    cookie_secure = settings.AUTH_SESSION_COOKIE_SECURE and not settings.is_dev
    response.set_cookie(
        key=settings.AUTH_SESSION_COOKIE_NAME,
        value=session_token,
        max_age=settings.AUTH_SESSION_TTL_DAYS * 86400,
        path="/",
        httponly=True,
        secure=cookie_secure,
        samesite="lax",
    )

    # ── Merge anonymous session if one is associated with this magic link ────
    # Primary source: anon_session_id stored in Redis when /send was called.
    # Fallback: trestle_anon_session cookie present on THIS verify request
    # (handles same-browser flows where the cookie is still live).
    # The Redis-stored value wins — it reflects the browser that initiated the
    # send, preventing cross-browser data leakage (e.g. a link pasted in a
    # different browser carries only the original sender's anon data).
    redis_anon_sid = payload.get("anon_session_id")
    cookie_anon_sid = request.cookies.get(settings.SESSION_COOKIE_NAME)
    anon_sid_to_merge = redis_anon_sid or cookie_anon_sid

    merge_summary = None
    session_merged = False

    if anon_sid_to_merge and not is_user_session_id(anon_sid_to_merge):
        try:
            merge_summary = await merge_anonymous_session(db, anon_sid_to_merge, user.id)
            session_merged = True
        except Exception:
            logger.exception(
                "merge_anonymous_session_failed",
                user_id=str(user.id),
                anon_prefix=anon_sid_to_merge[:8],
            )

    structlog.contextvars.bind_contextvars(user_id=str(user.id))
    logger.info(
        "magic_link_verified",
        user_id=str(user.id),
        email_normalized=email_normalized,
        attempts=attempts,
        session_merged=session_merged,
    )

    return MagicLinkVerifyOut(
        user=_user_out(user),
        session_merged=session_merged,
        merge_summary=merge_summary,
    )


@router.post("/merge-session", response_model=MergeSessionOut)
async def merge_session(
    body: MergeSessionIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
    current_user: UserCtx = Depends(require_user),
) -> MergeSessionOut:
    """Explicitly merge an anonymous session into the authenticated user's account.

    Useful after initial auth when the user accumulates work in a new anon session
    and wants to pull it into their account.
    Rate-limited to AUTH_MERGE_PER_HOUR per user.
    """
    anon_session_id = body.anon_session_id

    if is_user_session_id(anon_session_id):
        raise ValidationError(
            "anon_session_id must not be a user session id (must not start with 'user:')",
            code="invalid_anon_session_id",
        )

    merge_key = f"{_RATELIMIT_MERGE_PREFIX}{current_user.id}"
    over_limit, ttl = await _check_and_increment_rate_limit(
        redis, merge_key, settings.AUTH_MERGE_PER_HOUR
    )
    if over_limit:
        raise RateLimitError(
            "Too many merge requests. Please wait before trying again.",
            code="rate_limited",
            extra={"retry_after": ttl},
        )

    summary = await merge_anonymous_session(db, anon_session_id, current_user.id)
    merged = not summary.no_op

    logger.info(
        "explicit_merge_session",
        user_id=str(current_user.id),
        anon_prefix=anon_session_id[:8],
        merged=merged,
    )

    return MergeSessionOut(merged=merged, summary=summary)


@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: UserCtx = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    result = await db.execute(sa.select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError()
    return _user_out(user)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    current_user: UserCtx = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    token = request.cookies.get(settings.AUTH_SESSION_COOKIE_NAME)
    now = datetime.now(timezone.utc)

    if token:
        token_hash = hash_token(token)
        await db.execute(
            sa.update(UserSession)
            .where(
                UserSession.user_id == current_user.id,
                UserSession.session_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await db.commit()

    response.delete_cookie(settings.AUTH_SESSION_COOKIE_NAME, path="/")
    logger.info("user_logged_out", user_id=str(current_user.id))
    return Response(status_code=204)


@router.post("/logout/all", status_code=204)
async def logout_all(
    response: Response,
    current_user: UserCtx = Depends(require_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    now = datetime.now(timezone.utc)
    await db.execute(
        sa.update(UserSession)
        .where(
            UserSession.user_id == current_user.id,
            UserSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    await db.commit()

    response.delete_cookie(settings.AUTH_SESSION_COOKIE_NAME, path="/")
    logger.info("user_logged_out_all_sessions", user_id=str(current_user.id))
    return Response(status_code=204)
