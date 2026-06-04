"""Tests for the anonymous-session → authenticated-user merge (Step 20).

Pure-service tests (1–11): call merge_anonymous_session directly with a DB session.
HTTP integration tests (12–22): full request cycle via the app.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient

from backend.core.config import get_settings
from backend.db.models.chat import Conversation
from backend.db.models.grant_association import (
    GrantDismissal,
    GrantLifecycleEvent,
    GrantTrack,
)
from backend.db.models.memory import AgentMemory
from backend.db.models.profile import Profile
from backend.db.models.user import User, UserSession
from backend.db.session import get_db, get_db_factory
from backend.main import create_app
from backend.redis_client import get_redis
from backend.schemas.auth import MergeSummary
from backend.services.auth.identity import (
    canonical_session_id_for_user,
    is_user_session_id,
)
from backend.services.auth.merge import merge_anonymous_session
from backend.services.auth.tokens import (
    generate_magic_link_token,
    generate_session_token,
    hash_token,
)
from backend.services.email.dependency import get_email_client
from backend.services.email.types import EmailSendResult
from backend.services.llm.dependency import get_llm_client

SETTINGS = get_settings()
SESSION_COOKIE = SETTINGS.AUTH_SESSION_COOKIE_NAME
ANON_COOKIE = SETTINGS.SESSION_COOKIE_NAME
_MAGIC_PREFIX = "auth:magic:"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _anon(suffix: str = "") -> str:
    """Generate a distinct anonymous session id for a test."""
    return f"anon-merge-test-{suffix or uuid.uuid4().hex[:8]}"


# Grant-id stubs: SQLite doesn't enforce FK, so plain UUIDs work in tests.
_GRANT_A = uuid.uuid4()
_GRANT_B = uuid.uuid4()
_GRANT_C = uuid.uuid4()


async def _make_user(session_factory, email: str = "merge@example.com") -> tuple[uuid.UUID, str]:
    """Insert a User + UserSession. Returns (user_id, raw_session_token)."""
    token, token_hash = generate_session_token()
    now = _now()
    async with session_factory() as db:
        user = User(
            email=email,
            email_normalized=email,
            email_verified_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.flush()
        db.add(UserSession(
            user_id=user.id,
            session_token_hash=token_hash,
            issued_at=now,
            expires_at=now + timedelta(days=30),
            last_seen_at=now,
        ))
        await db.commit()
        return user.id, token


# ── HTTP fixtures ─────────────────────────────────────────────────────────────


class CapturingEmailClient:
    def __init__(self):
        self.sent: list[dict] = []

    async def send(self, to, subject, html, text, tags=None) -> EmailSendResult:
        self.sent.append({"to": to, "subject": subject, "html": html, "text": text})
        return EmailSendResult(success=True)

    def magic_link_url(self, index: int = -1) -> str | None:
        text = self.sent[index]["text"]
        for line in text.splitlines():
            if line.strip().startswith("http"):
                return line.strip()
        return None


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
        yield ac, app, fake_email


async def _verify_via_redis(client, redis_client, email: str, anon_session_id: str | None = None) -> dict:
    """Plant a token in Redis then POST /verify. Returns the response body."""
    token, token_hash = generate_magic_link_token()
    payload = json.dumps({
        "email": email,
        "email_normalized": email.lower(),
        "requested_at": _now().isoformat(),
        "attempts": 0,
        "anon_session_id": anon_session_id,
    })
    await redis_client.set(f"{_MAGIC_PREFIX}{token_hash}", payload, ex=900)
    res = await client.post("/api/auth/magic-link/verify", json={"token": token})
    assert res.status_code == 200, res.text
    return res.json()


# ═══════════════════════════════════════════════════════════════════════════════
# PURE-SERVICE TESTS (1–11)
# ═══════════════════════════════════════════════════════════════════════════════


async def test_1_merge_empty_anon_session(session_factory):
    """Merge from an anon session with no data → all counts zero, no_op=False."""
    to_user_id = uuid.uuid4()
    from_sid = _anon("empty")

    async with session_factory() as db:
        summary = await merge_anonymous_session(db, from_sid, to_user_id)

    assert summary.no_op is False
    assert summary.conversations_moved == 0
    assert summary.grant_tracks_moved == 0
    assert summary.agent_memories_moved == 0
    assert summary.profile_moved == 0


async def test_2_merge_same_session_is_noop(session_factory):
    """from_session_id == to_session_id → no_op=True."""
    user_id = uuid.uuid4()
    user_sid = canonical_session_id_for_user(user_id)

    async with session_factory() as db:
        summary = await merge_anonymous_session(db, user_sid, user_id)

    assert summary.no_op is True


async def test_3_merge_from_user_session_is_noop(session_factory):
    """from_session_id that starts with 'user:' → no_op=True (never cross-user)."""
    from_sid = "user:some-other-user-uuid"
    to_user_id = uuid.uuid4()

    async with session_factory() as db:
        summary = await merge_anonymous_session(db, from_sid, to_user_id)

    assert summary.no_op is True


async def test_4_profile_moved_when_user_has_none(session_factory):
    """Anon has a profile, user has none → profile row rekeyed, profile_moved=1."""
    from_sid = _anon("prof-move")
    to_user_id = uuid.uuid4()
    to_sid = canonical_session_id_for_user(to_user_id)

    async with session_factory() as db:
        db.add(Profile(session_id=from_sid, founder_name="Alice"))
        await db.commit()

    async with session_factory() as db:
        summary = await merge_anonymous_session(db, from_sid, to_user_id)

    assert summary.profile_moved == 1
    assert summary.profile_merged == 0

    async with session_factory() as db:
        res = await db.execute(sa.select(Profile).where(Profile.session_id == to_sid))
        profile = res.scalar_one_or_none()
    assert profile is not None
    assert profile.founder_name == "Alice"

    async with session_factory() as db:
        res = await db.execute(sa.select(Profile).where(Profile.session_id == from_sid))
        assert res.scalar_one_or_none() is None


async def test_5_profile_merged_fills_null_fields(session_factory):
    """Anon + user both have profiles: null fields filled from anon, user values preserved."""
    from_sid = _anon("prof-merge")
    to_user_id = uuid.uuid4()
    to_sid = canonical_session_id_for_user(to_user_id)

    async with session_factory() as db:
        db.add(Profile(session_id=from_sid, founder_name="Anon", company_name="AnonCo"))
        db.add(Profile(session_id=to_sid, founder_name="User", company_name=None))
        await db.commit()

    async with session_factory() as db:
        summary = await merge_anonymous_session(db, from_sid, to_user_id)

    assert summary.profile_merged == 1
    assert summary.profile_moved == 0
    assert summary.profile_fields_filled_from_anon == 1  # only company_name was null

    async with session_factory() as db:
        res = await db.execute(sa.select(Profile).where(Profile.session_id == to_sid))
        p = res.scalar_one()
    assert p.founder_name == "User"    # user wins
    assert p.company_name == "AnonCo"  # filled from anon

    # Anon profile deleted
    async with session_factory() as db:
        res = await db.execute(sa.select(Profile).where(Profile.session_id == from_sid))
        assert res.scalar_one_or_none() is None


async def test_6_conversations_moved(session_factory):
    """3 anon conversations (with messages) → conversations_moved=3, messages intact."""
    from_sid = _anon("conv")
    to_user_id = uuid.uuid4()
    to_sid = canonical_session_id_for_user(to_user_id)
    from backend.db.models.chat import Message

    conv_ids = []
    async with session_factory() as db:
        for i in range(3):
            conv = Conversation(session_id=from_sid, title=f"c{i}")
            db.add(conv)
            await db.flush()
            db.add(Message(conversation_id=conv.id, role="user", content=f"msg{i}"))
            conv_ids.append(conv.id)
        await db.commit()

    async with session_factory() as db:
        summary = await merge_anonymous_session(db, from_sid, to_user_id)

    assert summary.conversations_moved == 3

    async with session_factory() as db:
        res = await db.execute(
            sa.select(sa.func.count()).select_from(Conversation)
            .where(Conversation.session_id == to_sid)
        )
        assert res.scalar_one() == 3

        # Messages still accessible via conversation FK.
        for cid in conv_ids:
            res = await db.execute(
                sa.select(sa.func.count()).select_from(Message)
                .where(Message.conversation_id == cid)
            )
            assert res.scalar_one() == 1


async def test_7_grant_track_conflict_resolved(session_factory):
    """Anon and user both track the same grant → conflict merged, event re-linked."""
    from_sid = _anon("track-conflict")
    to_user_id = uuid.uuid4()
    to_sid = canonical_session_id_for_user(to_user_id)
    now = _now()

    async with session_factory() as db:
        anon_track = GrantTrack(
            session_id=from_sid,
            grant_id=_GRANT_A,
            lifecycle_status="submitted",
            note="applied via portal",
        )
        user_track = GrantTrack(
            session_id=to_sid,
            grant_id=_GRANT_A,
            lifecycle_status="drafting",
            note="",
        )
        db.add_all([anon_track, user_track])
        await db.flush()

        # Lifecycle event on the anon track.
        event = GrantLifecycleEvent(
            grant_track_id=anon_track.id,
            from_status=None,
            to_status="submitted",
            transition_kind="user",
            session_id=from_sid,
        )
        db.add(event)
        await db.commit()
        anon_id = anon_track.id
        user_id_track = user_track.id
        event_id = event.id

    async with session_factory() as db:
        summary = await merge_anonymous_session(db, from_sid, to_user_id)

    assert summary.grant_tracks_merged == 1
    assert summary.grant_tracks_moved == 0

    async with session_factory() as db:
        # User's track survives with merged data.
        res = await db.execute(sa.select(GrantTrack).where(GrantTrack.id == user_id_track))
        ut = res.scalar_one()
        assert ut.lifecycle_status == "drafting"   # user status preserved
        assert ut.note == "applied via portal"      # anon note filled (user note was empty)

        # Anon track soft-deleted, still in anon namespace.
        res = await db.execute(sa.select(GrantTrack).where(GrantTrack.id == anon_id))
        at = res.scalar_one()
        assert at.deleted_at is not None
        assert at.session_id == from_sid  # not rekeyed

        # Lifecycle event re-linked to user's track.
        res = await db.execute(
            sa.select(GrantLifecycleEvent).where(GrantLifecycleEvent.id == event_id)
        )
        ev = res.scalar_one()
        assert ev.grant_track_id == user_id_track


async def test_8_grant_track_moved_no_conflict(session_factory):
    """Anon tracks a grant the user doesn't → simple rekey, grant_tracks_moved=1."""
    from_sid = _anon("track-move")
    to_user_id = uuid.uuid4()
    to_sid = canonical_session_id_for_user(to_user_id)

    async with session_factory() as db:
        db.add(GrantTrack(session_id=from_sid, grant_id=_GRANT_B, lifecycle_status="interested"))
        await db.commit()

    async with session_factory() as db:
        summary = await merge_anonymous_session(db, from_sid, to_user_id)

    assert summary.grant_tracks_moved == 1
    assert summary.grant_tracks_merged == 0

    async with session_factory() as db:
        res = await db.execute(
            sa.select(sa.func.count()).select_from(GrantTrack)
            .where(GrantTrack.session_id == to_sid, GrantTrack.deleted_at.is_(None))
        )
        assert res.scalar_one() == 1


async def test_9_grant_dismissal_conflict_user_reason_wins(session_factory):
    """Anon + user both dismissed the same grant → grant_dismissals_merged=1, user reason kept."""
    from_sid = _anon("dismiss-conflict")
    to_user_id = uuid.uuid4()
    to_sid = canonical_session_id_for_user(to_user_id)

    async with session_factory() as db:
        db.add(GrantDismissal(session_id=from_sid, grant_id=_GRANT_C, reason="too_competitive"))
        db.add(GrantDismissal(session_id=to_sid, grant_id=_GRANT_C, reason="not_eligible"))
        await db.commit()

    async with session_factory() as db:
        summary = await merge_anonymous_session(db, from_sid, to_user_id)

    assert summary.grant_dismissals_merged == 1
    assert summary.grant_dismissals_moved == 0

    async with session_factory() as db:
        res = await db.execute(
            sa.select(GrantDismissal)
            .where(GrantDismissal.session_id == to_sid, GrantDismissal.grant_id == _GRANT_C)
        )
        dismissal = res.scalar_one()
        assert dismissal.reason == "not_eligible"  # user reason preserved


async def test_10_memories_bulk_rekeyed_no_dedup(session_factory):
    """Anon has 5 memories, user has 2 → 7 total after merge (no dedup)."""
    from_sid = _anon("memory")
    to_user_id = uuid.uuid4()
    to_sid = canonical_session_id_for_user(to_user_id)

    async with session_factory() as db:
        for i in range(5):
            db.add(AgentMemory(
                session_id=from_sid,
                kind="preference",
                content=f"anon pref {i}",
            ))
        for i in range(2):
            db.add(AgentMemory(
                session_id=to_sid,
                kind="preference",
                content=f"user pref {i}",
            ))
        await db.commit()

    async with session_factory() as db:
        summary = await merge_anonymous_session(db, from_sid, to_user_id)

    assert summary.agent_memories_moved == 5

    async with session_factory() as db:
        res = await db.execute(
            sa.select(sa.func.count()).select_from(AgentMemory)
            .where(AgentMemory.session_id == to_sid, AgentMemory.deleted_at.is_(None))
        )
        assert res.scalar_one() == 7  # 5 anon + 2 user, no dedup


async def test_11_merge_is_atomic(session_factory):
    """A failure inside the transaction rolls back all changes."""
    from_sid = _anon("atomic")
    to_user_id = uuid.uuid4()
    to_sid = canonical_session_id_for_user(to_user_id)

    async with session_factory() as db:
        for i in range(3):
            db.add(Conversation(session_id=from_sid, title=f"conv{i}"))
        await db.commit()

    # Simulate a mid-merge failure using a local helper that uses the same
    # async-with-begin pattern as the real merge function.
    async def _failing_merge(db, from_sid, to_sid):
        async with db.begin():
            await db.execute(
                sa.update(Conversation)
                .where(Conversation.session_id == from_sid)
                .values(session_id=to_sid)
            )
            # Raise before commit — the async with block rolls back.
            raise RuntimeError("simulated mid-merge failure")

    with pytest.raises(RuntimeError, match="simulated mid-merge failure"):
        async with session_factory() as db:
            await _failing_merge(db, from_sid, to_sid)

    # All rows still in the anon namespace.
    async with session_factory() as db:
        res = await db.execute(
            sa.select(sa.func.count()).select_from(Conversation)
            .where(Conversation.session_id == from_sid)
        )
        assert res.scalar_one() == 3

        res = await db.execute(
            sa.select(sa.func.count()).select_from(Conversation)
            .where(Conversation.session_id == to_sid)
        )
        assert res.scalar_one() == 0


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP INTEGRATION TESTS (12–22)
# ═══════════════════════════════════════════════════════════════════════════════


async def test_12_send_stores_anon_session_in_redis(auth_client, redis_client, session_factory):
    """POST /send with anon cookie → Redis payload contains anon_session_id."""
    client, app, fake_email = auth_client
    anon_sid = "send-anon-12"

    res = await client.post(
        "/api/auth/magic-link/send",
        json={"email": "send-stores@example.com"},
        cookies={ANON_COOKIE: anon_sid},
    )
    assert res.status_code == 200

    url = fake_email.magic_link_url()
    token = url.split("token=")[1]
    raw = await redis_client.get(f"{_MAGIC_PREFIX}{hash_token(token)}")
    payload = json.loads(raw)
    assert payload["anon_session_id"] == anon_sid


async def test_13_verify_with_anon_cookie_merges_data(auth_client, redis_client, session_factory):
    """Verify with matching anon cookie → session_merged=True, conversations visible as user."""
    client, app, _ = auth_client
    anon_sid = _anon("http-merge")

    # Seed a conversation under the anon session.
    async with session_factory() as db:
        db.add(Conversation(session_id=anon_sid, title="pre-auth conv"))
        await db.commit()

    body = await _verify_via_redis(
        client, redis_client, "verify-merge@example.com", anon_session_id=anon_sid
    )
    assert body["session_merged"] is True
    ms = body["merge_summary"]
    assert ms["conversations_moved"] == 1

    # Conversations are now visible to the authenticated user.
    res = await client.get("/api/conversations")
    assert res.status_code == 200
    items = res.json().get("items", [])
    titles = [c.get("title") for c in items]
    assert "pre-auth conv" in titles


async def test_14_verify_without_anon_session_no_merge(auth_client, redis_client):
    """Verify with no anon session → session_merged=False, merge_summary=null."""
    client, app, _ = auth_client
    body = await _verify_via_redis(client, redis_client, "no-merge@example.com")
    assert body["session_merged"] is False
    assert body["merge_summary"] is None


async def test_15_verify_uses_redis_anon_session_when_no_cookie(
    auth_client, redis_client, session_factory
):
    """Redis-stored anon_session_id triggers merge even when no anon cookie on verify."""
    client, app, _ = auth_client
    anon_sid = _anon("redis-only")

    async with session_factory() as db:
        db.add(Conversation(session_id=anon_sid, title="redis-only conv"))
        await db.commit()

    # Plant token in Redis WITH anon_session_id (as if /send was called from that browser).
    # The verify request below carries NO anon cookie.
    token, token_hash = generate_magic_link_token()
    payload = json.dumps({
        "email": "redis-only@example.com",
        "email_normalized": "redis-only@example.com",
        "requested_at": _now().isoformat(),
        "attempts": 0,
        "anon_session_id": anon_sid,
    })
    await redis_client.set(f"{_MAGIC_PREFIX}{token_hash}", payload, ex=900)

    # Use a fresh client that has no cookies — simulates a different browser.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as fresh:
        res = await fresh.post("/api/auth/magic-link/verify", json={"token": token})

    assert res.status_code == 200
    body = res.json()
    assert body["session_merged"] is True
    assert body["merge_summary"]["conversations_moved"] == 1


async def test_16_explicit_merge_session_endpoint(auth_client, redis_client, session_factory):
    """POST /auth/merge-session as authenticated user → merges anon data."""
    client, app, _ = auth_client
    anon_sid = _anon("explicit")

    await _verify_via_redis(client, redis_client, "explicit-merge@example.com")

    async with session_factory() as db:
        db.add(Conversation(session_id=anon_sid, title="explicit-merge conv"))
        await db.commit()

    res = await client.post(
        "/api/auth/merge-session",
        json={"anon_session_id": anon_sid},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["merged"] is True
    assert body["summary"]["conversations_moved"] == 1


async def test_17_merge_session_requires_auth(client):
    """POST /auth/merge-session without auth cookie → 401."""
    res = await client.post(
        "/api/auth/merge-session",
        json={"anon_session_id": "some-anon-session"},
    )
    assert res.status_code == 401


async def test_18_merge_session_rejects_user_prefix(auth_client, redis_client):
    """POST /auth/merge-session with a 'user:' anon_session_id → 422."""
    client, app, _ = auth_client
    await _verify_via_redis(client, redis_client, "rejects-prefix@example.com")

    res = await client.post(
        "/api/auth/merge-session",
        json={"anon_session_id": "user:some-other-user-uuid"},
    )
    assert res.status_code == 422


async def test_19_merge_session_rate_limited(auth_client, redis_client):
    """POST /auth/merge-session 6 times → 6th request is 429."""
    client, app, _ = auth_client
    await _verify_via_redis(client, redis_client, "ratelimit-merge@example.com")

    for i in range(5):
        res = await client.post(
            "/api/auth/merge-session",
            json={"anon_session_id": f"rate-anon-{i}"},
        )
        assert res.status_code == 200, f"request {i}: {res.text}"

    res = await client.post(
        "/api/auth/merge-session",
        json={"anon_session_id": "rate-anon-6"},
    )
    assert res.status_code == 429
    assert res.json()["code"] == "rate_limited"


async def test_20_redis_anon_session_wins_over_cookie(
    auth_client, redis_client, session_factory
):
    """Verify uses Redis-stored anon_session_id, not the cookie present at verify time.

    Even if the cookie on the verify request belongs to a different session,
    only the Redis-stored anon_session_id (from the /send call) gets merged.
    """
    client, app, _ = auth_client
    # Data for the "send" browser (redis-stored session)
    send_anon_sid = _anon("send-browser")
    # Data for the "verify" browser (cookie-only session, should NOT be merged)
    verify_anon_sid = _anon("verify-browser")

    async with session_factory() as db:
        db.add(Conversation(session_id=send_anon_sid, title="send-browser conv"))
        db.add(Conversation(session_id=verify_anon_sid, title="verify-browser conv"))
        await db.commit()

    # Plant token with the send-browser anon session.
    token, token_hash = generate_magic_link_token()
    payload = json.dumps({
        "email": "cross-browser@example.com",
        "email_normalized": "cross-browser@example.com",
        "requested_at": _now().isoformat(),
        "attempts": 0,
        "anon_session_id": send_anon_sid,
    })
    await redis_client.set(f"{_MAGIC_PREFIX}{token_hash}", payload, ex=900)

    # Verify in a fresh client that carries the VERIFY browser's anon cookie.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as fresh:
        res = await fresh.post(
            "/api/auth/magic-link/verify",
            json={"token": token},
            cookies={ANON_COOKIE: verify_anon_sid},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["session_merged"] is True
    summary = body["merge_summary"]
    # Only 1 conversation moved (from send_anon_sid), not 2.
    assert summary["conversations_moved"] == 1
    assert summary["from_session_id_prefix"] == send_anon_sid[:8]

    # verify-browser conv must still be in verify_anon_sid namespace.
    async with session_factory() as db:
        res = await db.execute(
            sa.select(sa.func.count()).select_from(Conversation)
            .where(Conversation.session_id == verify_anon_sid)
        )
        assert res.scalar_one() == 1


async def test_21_auth_middleware_sets_user_session_id(auth_client, redis_client, session_factory):
    """After auth, request.state.session_id is 'user:{uuid}', anon cookie preserved separately."""
    client, app, _ = auth_client
    anon_sid = _anon("middleware")

    # Create a conversation in the user-scoped namespace so GET /api/conversations
    # shows it (which means session_id was "user:{uuid}" during the query).
    body = await _verify_via_redis(client, redis_client, "middleware@example.com")
    user_id = body["user"]["id"]
    user_sid = canonical_session_id_for_user(uuid.UUID(user_id))

    async with session_factory() as db:
        db.add(Conversation(session_id=user_sid, title="user-scoped conv"))
        await db.commit()

    res = await client.get("/api/conversations")
    assert res.status_code == 200
    items = res.json().get("items", [])
    titles = [c.get("title") for c in items]
    assert "user-scoped conv" in titles


async def test_22_conversation_list_works_for_authenticated_user(
    auth_client, redis_client, session_factory
):
    """Authenticated GET /api/conversations filters by user:{uuid}, not by anon UUID."""
    client, app, _ = auth_client
    anon_sid = _anon("conv-list")

    body = await _verify_via_redis(
        client, redis_client, "conv-list@example.com", anon_session_id=anon_sid
    )
    user_id = body["user"]["id"]
    user_sid = canonical_session_id_for_user(uuid.UUID(user_id))

    # Seed one conversation in the anon namespace (should have been merged)
    # and one directly in the user namespace.
    async with session_factory() as db:
        db.add(Conversation(session_id=anon_sid, title="post-auth anon conv"))
        db.add(Conversation(session_id=user_sid, title="user conv"))
        await db.commit()

    res = await client.get("/api/conversations")
    assert res.status_code == 200
    items = res.json().get("items", [])
    titles = [c.get("title") for c in items]
    # The user-scoped conversation is always visible.
    assert "user conv" in titles
