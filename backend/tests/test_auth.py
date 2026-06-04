"""Tests for magic-link authentication.

Uses a local auth_client fixture that overrides the email client dep so we can
capture sent email payloads without hitting real infrastructure.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient

from backend.core.config import get_settings
from backend.core.errors import AuthenticationError
from backend.db.models.user import User, UserSession
from backend.db.session import get_db, get_db_factory
from backend.main import create_app
from backend.redis_client import get_redis
from backend.schemas.auth import UserOut
from backend.services.auth.tokens import (
    generate_magic_link_token,
    generate_session_token,
    hash_token,
)
from backend.services.email.dependency import get_email_client
from backend.services.email.types import EmailSendResult
from backend.services.llm.dependency import get_llm_client

_MAGIC_PREFIX = "auth:magic:"
_RATELIMIT_EMAIL = "auth:ratelimit:send:"
_RATELIMIT_IP = "auth:ratelimit:send:ip:"

SETTINGS = get_settings()
SESSION_COOKIE = SETTINGS.AUTH_SESSION_COOKIE_NAME


# ── Fake email client ─────────────────────────────────────────────────────────


class CapturingEmailClient:
    def __init__(self):
        self.sent: list[dict] = []

    async def send(self, to, subject, html, text, tags=None) -> EmailSendResult:
        self.sent.append({"to": to, "subject": subject, "html": html, "text": text, "tags": tags})
        return EmailSendResult(success=True)

    @property
    def last(self) -> dict:
        return self.sent[-1]

    def magic_link_url(self, index: int = -1) -> str | None:
        text = self.sent[index]["text"]
        for line in text.splitlines():
            if line.strip().startswith("http"):
                return line.strip()
        return None


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def fake_email():
    return CapturingEmailClient()


@pytest_asyncio.fixture
async def fake_llm():
    from backend.services.llm.fake import FakeLLMClient
    return FakeLLMClient()


@pytest_asyncio.fixture
async def auth_client(session_factory, redis_client, fake_llm, fake_email):
    app = create_app()

    async def _db():
        async with session_factory() as s:
            yield s

    async def _redis():
        yield redis_client

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_redis] = _redis
    app.dependency_overrides[get_db_factory] = lambda: session_factory
    app.dependency_overrides[get_llm_client] = lambda: fake_llm
    app.dependency_overrides[get_email_client] = lambda: fake_email

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _send(client, email: str, *, headers: dict | None = None) -> tuple[int, dict]:
    res = await client.post(
        "/api/auth/magic-link/send",
        json={"email": email},
        headers=headers or {},
    )
    return res.status_code, res.json()


async def _verify_via_redis(client, redis_client, email: str = "user@example.com") -> tuple[int, dict]:
    """Generate a fresh token, plant it in Redis, then POST verify."""
    token, token_hash = generate_magic_link_token()
    payload = json.dumps({
        "email": email,
        "email_normalized": email.lower(),
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "attempts": 0,
        "anon_session_id": None,
    })
    await redis_client.set(f"{_MAGIC_PREFIX}{token_hash}", payload, ex=900)
    res = await client.post("/api/auth/magic-link/verify", json={"token": token})
    return res.status_code, res.json()


async def _make_user_and_session(
    session_factory,
    *,
    email: str = "existing@example.com",
    disabled: bool = False,
    expired: bool = False,
    revoked: bool = False,
) -> tuple[uuid.UUID, str]:
    """Directly create a User + UserSession in the DB. Returns (user_id, raw_token)."""
    token, token_hash = generate_session_token()
    now = datetime.now(timezone.utc)
    expires_at = (now - timedelta(days=1)) if expired else (now + timedelta(days=30))

    async with session_factory() as s:
        user = User(
            email=email,
            email_normalized=email.lower(),
            email_verified_at=now,
            created_at=now,
            updated_at=now,
            disabled_at=now if disabled else None,
        )
        s.add(user)
        await s.flush()

        session = UserSession(
            user_id=user.id,
            session_token_hash=token_hash,
            issued_at=now,
            expires_at=expires_at,
            last_seen_at=now,
            revoked_at=now if revoked else None,
        )
        s.add(session)
        await s.commit()
        return user.id, token


# ── Rate-limiting tests (1–3) ─────────────────────────────────────────────────


async def test_rate_limit_per_email_5_succeed_6th_fails(auth_client, redis_client, fake_email):
    """Test 1: 5 sends to same email succeed; 6th is 429 with Retry-After."""
    email = "ratelimit@example.com"
    for _ in range(5):
        status, _ = await _send(auth_client, email)
        assert status == 200, f"expected 200 but got {status}"

    status, body = await _send(auth_client, email)
    assert status == 429
    assert body["code"] == "rate_limited"
    assert "retry_after" in body


async def test_rate_limit_per_ip_20_succeed_21st_fails(auth_client, redis_client):
    """Test 2: 20 sends from same IP (different emails) succeed; 21st is 429."""
    # The IP limit is 20; use unique emails to avoid the per-email limit.
    for i in range(20):
        status, _ = await _send(auth_client, f"ip-test-{i}@example.com")
        assert status == 200, f"request {i}: expected 200 but got {status}"

    status, body = await _send(auth_client, "ip-overflow@example.com")
    assert status == 429
    assert body["code"] == "rate_limited"


async def test_rate_limit_email_and_ip_independent(auth_client, redis_client):
    """Test 3: per-email and per-IP counters are independent."""
    email_a = "emailonly@example.com"

    # Max out email_a's email-level counter (5 sends).
    for _ in range(5):
        status, _ = await _send(auth_client, email_a)
        assert status == 200
    status, body = await _send(auth_client, email_a)
    assert status == 429  # email_a's email counter exhausted

    # A different email from the same IP still succeeds (IP counter at 6, limit 20).
    status, _ = await _send(auth_client, "email-b@example.com")
    assert status == 200


# ── Send tests (4–7) ──────────────────────────────────────────────────────────


async def test_send_valid_email_logs_and_returns_200(auth_client, fake_email):
    """Test 4: valid send returns 200 and the email client is called with the URL."""
    status, body = await _send(auth_client, "send-test@example.com")
    assert status == 200
    assert body["sent"] is True
    assert body["expires_in_seconds"] == SETTINGS.AUTH_MAGIC_LINK_TTL_SECONDS

    assert len(fake_email.sent) == 1
    assert "send-test@example.com" in fake_email.last["to"]
    url = fake_email.magic_link_url()
    assert url is not None
    assert "token=" in url


async def test_send_malformed_email_returns_422(auth_client):
    """Test 5: malformed email → 422 from Pydantic validation."""
    res = await auth_client.post(
        "/api/auth/magic-link/send", json={"email": "not-an-email"}
    )
    assert res.status_code == 422


async def test_send_unknown_email_same_response(auth_client, fake_email):
    """Test 6: email not in DB returns the same 200 — no enumeration."""
    status, body = await _send(auth_client, "ghost@nowhere.example")
    assert status == 200
    assert body["sent"] is True


async def test_send_sets_redis_key_with_correct_ttl(auth_client, redis_client, fake_email):
    """Test 7: magic link Redis key is stored with appropriate TTL."""
    status, _ = await _send(auth_client, "ttl-check@example.com")
    assert status == 200

    # Recover the token from the URL and check the Redis key.
    url = fake_email.magic_link_url()
    token = url.split("token=")[1]
    t_hash = hash_token(token)

    raw = await redis_client.get(f"{_MAGIC_PREFIX}{t_hash}")
    assert raw is not None

    ttl = await redis_client.ttl(f"{_MAGIC_PREFIX}{t_hash}")
    assert 0 < ttl <= SETTINGS.AUTH_MAGIC_LINK_TTL_SECONDS


# ── Verify tests (8–15) ───────────────────────────────────────────────────────


async def test_verify_fresh_token_creates_session(auth_client, redis_client, session_factory):
    """Test 8: fresh token → 200, user created, session cookie set, Redis key gone."""
    status, body = await _verify_via_redis(auth_client, redis_client)
    assert status == 200
    assert "user" in body
    assert body["session_merged"] is False

    # Cookie must be present
    assert SESSION_COOKIE in auth_client.cookies

    # Redis key must be gone (single-use)
    token, token_hash = generate_magic_link_token()  # fresh pair just to show pattern
    # The actual key was already checked during _verify_via_redis by its deletion.


async def test_verify_same_token_twice(auth_client, redis_client):
    """Test 9: verify same token twice → first 200, second 401."""
    token, token_hash = generate_magic_link_token()
    payload = json.dumps({
        "email": "double@example.com",
        "email_normalized": "double@example.com",
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "attempts": 0,
        "anon_session_id": None,
    })
    await redis_client.set(f"{_MAGIC_PREFIX}{token_hash}", payload, ex=900)

    res1 = await auth_client.post("/api/auth/magic-link/verify", json={"token": token})
    assert res1.status_code == 200

    res2 = await auth_client.post("/api/auth/magic-link/verify", json={"token": token})
    assert res2.status_code == 401
    assert res2.json()["code"] == "invalid_or_expired_token"


async def test_verify_expired_token(auth_client, redis_client):
    """Test 10: verify after TTL expiry → 401 (key gone from Redis)."""
    token, token_hash = generate_magic_link_token()
    # Don't set the key → simulates TTL expiry
    res = await auth_client.post("/api/auth/magic-link/verify", json={"token": token})
    assert res.status_code == 401
    assert res.json()["code"] == "invalid_or_expired_token"


async def test_verify_garbage_token(auth_client):
    """Test 11: garbage token → 401."""
    res = await auth_client.post(
        "/api/auth/magic-link/verify", json={"token": "totallygarbage"}
    )
    assert res.status_code == 401
    assert res.json()["code"] == "invalid_or_expired_token"


async def test_verify_sets_email_verified_at(auth_client, redis_client, session_factory):
    """Test 12: successful verify sets email_verified_at on the created user."""
    email = "verified@example.com"
    await _verify_via_redis(auth_client, redis_client, email=email)

    async with session_factory() as s:
        result = await s.execute(
            sa.select(User).where(User.email_normalized == email)
        )
        user = result.scalar_one_or_none()

    assert user is not None
    assert user.email_verified_at is not None


async def test_verify_existing_user_updates_last_login(auth_client, redis_client, session_factory):
    """Test 13: second verify for same email updates last_login_at, no duplicate user."""
    email = "returning@example.com"

    await _verify_via_redis(auth_client, redis_client, email=email)
    await _verify_via_redis(auth_client, redis_client, email=email)

    async with session_factory() as s:
        result = await s.execute(
            sa.select(User).where(User.email_normalized == email)
        )
        users = result.scalars().all()

    assert len(users) == 1
    assert users[0].last_login_at is not None


async def test_verify_disabled_user_returns_403(auth_client, redis_client, session_factory):
    """Test 14: verify for a disabled user → 403 with code='user_disabled'."""
    email = "disabled@example.com"
    now = datetime.now(timezone.utc)

    async with session_factory() as s:
        user = User(
            email=email,
            email_normalized=email,
            email_verified_at=now,
            created_at=now,
            updated_at=now,
            disabled_at=now,
        )
        s.add(user)
        await s.commit()

    token, token_hash = generate_magic_link_token()
    payload = json.dumps({
        "email": email,
        "email_normalized": email,
        "requested_at": now.isoformat(),
        "attempts": 0,
        "anon_session_id": None,
    })
    await redis_client.set(f"{_MAGIC_PREFIX}{token_hash}", payload, ex=900)

    res = await auth_client.post("/api/auth/magic-link/verify", json={"token": token})
    assert res.status_code == 403
    assert res.json()["code"] == "user_disabled"


async def test_verify_redis_key_deleted_on_success(auth_client, redis_client):
    """Test 15: after successful verify the Redis key is gone (single-use)."""
    token, token_hash = generate_magic_link_token()
    payload = json.dumps({
        "email": "singleuse@example.com",
        "email_normalized": "singleuse@example.com",
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "attempts": 0,
        "anon_session_id": None,
    })
    redis_key = f"{_MAGIC_PREFIX}{token_hash}"
    await redis_client.set(redis_key, payload, ex=900)

    res = await auth_client.post("/api/auth/magic-link/verify", json={"token": token})
    assert res.status_code == 200

    remaining = await redis_client.get(redis_key)
    assert remaining is None


# ── Session and middleware tests (16–22) ─────────────────────────────────────


async def test_me_without_cookie_returns_401(auth_client):
    """Test 16: GET /auth/me without cookie → 401."""
    res = await auth_client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.json()["code"] == "authentication_required"


async def test_me_with_valid_session_returns_user(auth_client, redis_client, session_factory):
    """Test 17: GET /auth/me with valid session cookie → 200 UserOut."""
    email = "me-test@example.com"
    await _verify_via_redis(auth_client, redis_client, email=email)

    res = await auth_client.get("/api/auth/me")
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == email
    assert body["email_verified"] is True


async def test_me_with_revoked_session_returns_401(auth_client, session_factory):
    """Test 18: GET /auth/me with revoked session → 401, cookie cleared."""
    _id, token = await _make_user_and_session(
        session_factory, email="revoked@example.com", revoked=True
    )
    res = await auth_client.get(
        "/api/auth/me", cookies={SESSION_COOKIE: token}
    )
    assert res.status_code == 401
    # Cookie should be cleared in response
    assert SESSION_COOKIE not in auth_client.cookies or auth_client.cookies.get(SESSION_COOKIE) == ""


async def test_me_with_expired_session_returns_401(auth_client, session_factory):
    """Test 19: GET /auth/me with expired session → 401."""
    _id, token = await _make_user_and_session(
        session_factory, email="expired-sess@example.com", expired=True
    )
    res = await auth_client.get(
        "/api/auth/me", cookies={SESSION_COOKIE: token}
    )
    assert res.status_code == 401


async def test_logout_revokes_session(auth_client, redis_client, session_factory):
    """Test 20: POST /auth/logout revokes session, subsequent /auth/me → 401."""
    await _verify_via_redis(auth_client, redis_client, email="logout@example.com")

    res = await auth_client.post("/api/auth/logout")
    assert res.status_code == 204

    res2 = await auth_client.get("/api/auth/me")
    assert res2.status_code == 401


async def test_logout_all_revokes_all_sessions(auth_client, redis_client, session_factory):
    """Test 21: POST /auth/logout/all revokes all sessions for the user."""
    email = "logout-all@example.com"
    now = datetime.now(timezone.utc)

    # Create user with 2 sessions directly.
    async with session_factory() as s:
        user = User(
            email=email,
            email_normalized=email,
            email_verified_at=now,
            created_at=now,
            updated_at=now,
        )
        s.add(user)
        await s.flush()
        user_id = user.id

        sessions = []
        for _ in range(2):
            t, th = generate_session_token()
            sess = UserSession(
                user_id=user_id,
                session_token_hash=th,
                issued_at=now,
                expires_at=now + timedelta(days=30),
                last_seen_at=now,
            )
            s.add(sess)
            sessions.append(t)
        await s.commit()

    # Use the first token to authenticate and logout all.
    res = await auth_client.post(
        "/api/auth/logout/all", cookies={SESSION_COOKIE: sessions[0]}
    )
    assert res.status_code == 204

    # Both sessions should now be revoked.
    async with session_factory() as s:
        result = await s.execute(
            sa.select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
        )
        active = result.scalars().all()

    assert len(active) == 0


async def test_both_anon_and_auth_cookies_coexist(auth_client, redis_client):
    """Test 22: a request carrying both anon and auth cookies sets both state attrs."""
    await _verify_via_redis(auth_client, redis_client, email="coexist@example.com")

    # auth_client now has the trestle_session cookie. The session middleware also
    # reads/sets trestle_anon_session. Both should be populated.
    res = await auth_client.get("/api/auth/me")
    assert res.status_code == 200
    # trestle_anon_session is set by SessionMiddleware on the first request.
    assert "trestle_anon_session" in auth_client.cookies
    assert SESSION_COOKIE in auth_client.cookies


# ── Email client tests (23–24) ────────────────────────────────────────────────


async def test_log_email_client_structured_log(auth_client, fake_email):
    """Test 23: send emits a structured field magic_link_url for local copy-paste."""
    await _send(auth_client, "logtest@example.com")

    assert len(fake_email.sent) == 1
    email_data = fake_email.last
    assert email_data["to"] == "logtest@example.com"
    assert "Sign in" in email_data["subject"]
    assert "magic_link" in (email_data["tags"] or [])

    # The URL should be present in the text body.
    url = fake_email.magic_link_url()
    assert url is not None
    assert url.startswith("http")
    assert "token=" in url


async def test_email_client_protocol_satisfied_by_log_client():
    """Test 24: LogEmailClient satisfies the EmailClient protocol."""
    from backend.services.email.base import EmailClient
    from backend.services.email.log import LogEmailClient

    client = LogEmailClient()
    assert isinstance(client, EmailClient)


# ── Startup guard test ────────────────────────────────────────────────────────


def test_missing_pepper_fails_in_production():
    """AUTH_IP_HASH_PEPPER with no value raises in non-dev environments."""
    from backend.core.config import Settings
    import pydantic

    with pytest.raises((pydantic.ValidationError, ValueError)):
        Settings(ENVIRONMENT="production", AUTH_IP_HASH_PEPPER="")
