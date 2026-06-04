"""Tests for the alert delivery system (Step 17).

Scan functions and send functions are tested independently without going
through arq's actual queue. Time-sensitive tests use freezegun.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest
import pytest_asyncio
import sqlalchemy as sa
from freezegun import freeze_time
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.db.models.alert_delivery import AlertDelivery
from backend.db.models.grant import Grant
from backend.db.models.grant_association import GrantTrack
from backend.db.models.profile import Profile
from backend.db.models.user import User
from backend.db.session import get_db, get_db_factory
from backend.main import create_app
from backend.redis_client import get_redis
from backend.schemas.auth import UserOut
from backend.services.auth.identity import canonical_session_id_for_user
from backend.services.auth.tokens import generate_session_token, hash_token
from backend.services.email.types import EmailSendResult
from backend.services.jobs.checkin_alerts import enqueue_checkin_alerts, send_checkin_alert
from backend.services.jobs.deadline_alerts import enqueue_deadline_alerts, send_deadline_alert
from backend.services.jobs.new_grant_alerts import enqueue_new_grant_alerts, send_new_grant_alert
from backend.services.llm.dependency import get_llm_client

SETTINGS = get_settings()


# ── Helpers ───────────────────────────────────────────────────────────────────


class MockArqRedis:
    def __init__(self):
        self.enqueued: list[tuple[str, str]] = []

    async def enqueue_job(self, func_name: str, delivery_id: str) -> None:
        self.enqueued.append((func_name, delivery_id))


class CapturingEmailClient:
    def __init__(self):
        self.sent: list[dict] = []

    async def send(
        self,
        to: str,
        subject: str,
        html: str,
        text: str,
        tags: list[str] | None = None,
        template_id: str | None = None,
    ) -> EmailSendResult:
        self.sent.append({"to": to, "subject": subject, "tags": tags, "text": text})
        return EmailSendResult(success=True)

    @property
    def last(self) -> dict:
        return self.sent[-1]


class FailingEmailClient:
    async def send(self, *args, **kwargs) -> EmailSendResult:
        raise RuntimeError("SMTP unreachable")


def _make_ctx(session_factory, email_client=None, redis=None, settings=None) -> dict:
    return {
        "session_factory": session_factory,
        "email_client": email_client or CapturingEmailClient(),
        "redis": redis or MockArqRedis(),
        "settings": settings or SETTINGS,
    }


async def _make_user(
    session_factory,
    *,
    email: str = "test@example.com",
    verified: bool = True,
    disabled: bool = False,
    alert_preferences: dict | None = None,
) -> User:
    async with session_factory() as db:
        async with db.begin():
            user = User(
                email=email,
                email_normalized=email.lower(),
                email_verified_at=datetime.now(timezone.utc) if verified else None,
                disabled_at=datetime.now(timezone.utc) if disabled else None,
                alert_preferences=alert_preferences or {},
                alert_unsubscribe_token=f"tok-{uuid.uuid4().hex[:16]}",
            )
            db.add(user)
            await db.flush()
            uid = user.id
    async with session_factory() as db:
        result = await db.execute(sa.select(User).where(User.id == uid))
        return result.scalar_one()


async def _make_grant(
    session_factory,
    *,
    deadline: date | None = None,
    status: str = "active",
    created_at: datetime | None = None,
    last_alerted_to_users_at: datetime | None = None,
) -> Grant:
    async with session_factory() as db:
        async with db.begin():
            g = Grant(
                source_id=f"src-{uuid.uuid4().hex[:8]}",
                name=f"Test Grant {uuid.uuid4().hex[:4]}",
                type="grant",
                description="A test grant",
                url="https://example.com/grant",
                provider_name="Test Foundation",
                status=status,
                deadline=deadline,
                created_at=created_at or datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_alerted_to_users_at=last_alerted_to_users_at,
            )
            db.add(g)
            await db.flush()
            gid = g.id
    async with session_factory() as db:
        result = await db.execute(sa.select(Grant).where(Grant.id == gid))
        return result.scalar_one()


async def _make_track(
    session_factory,
    *,
    user: User,
    grant: Grant,
    lifecycle_status: str = "interested",
    lifecycle_updated_at: datetime | None = None,
) -> GrantTrack:
    session_id = canonical_session_id_for_user(user.id)
    async with session_factory() as db:
        async with db.begin():
            track = GrantTrack(
                session_id=session_id,
                grant_id=grant.id,
                lifecycle_status=lifecycle_status,
                lifecycle_updated_at=lifecycle_updated_at or datetime.now(timezone.utc),
            )
            db.add(track)
            await db.flush()
            tid = track.id
    async with session_factory() as db:
        result = await db.execute(sa.select(GrantTrack).where(GrantTrack.id == tid))
        return result.scalar_one()


async def _make_profile(
    session_factory,
    *,
    user: User,
    company_stage: str = "seed",
    location: str = "US",
    industry: list | None = None,
    incorporation_country: str = "US",
) -> Profile:
    session_id = canonical_session_id_for_user(user.id)
    async with session_factory() as db:
        async with db.begin():
            p = Profile(
                session_id=session_id,
                company_name="Acme Corp",
                company_stage=company_stage,
                location=location,
                industry=industry or ["technology"],
                incorporation_country=incorporation_country,
            )
            db.add(p)
            await db.flush()
            pid = p.id
    async with session_factory() as db:
        result = await db.execute(sa.select(Profile).where(Profile.id == pid))
        return result.scalar_one()


async def _count_deliveries(session_factory, **filters) -> int:
    async with session_factory() as db:
        stmt = sa.select(sa.func.count()).select_from(AlertDelivery)
        for k, v in filters.items():
            stmt = stmt.where(getattr(AlertDelivery, k) == v)
        result = await db.execute(stmt)
        return result.scalar_one()


async def _get_delivery(session_factory, delivery_id: str) -> AlertDelivery:
    async with session_factory() as db:
        result = await db.execute(
            sa.select(AlertDelivery).where(AlertDelivery.id == uuid.UUID(delivery_id))
        )
        return result.scalar_one()


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def auth_client(session_factory, redis_client):
    from backend.services.llm.fake import FakeLLMClient

    app = create_app()

    async def _override_db():
        async with session_factory() as session:
            yield session

    async def _override_redis():
        yield redis_client

    def _override_factory():
        return session_factory

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_db_factory] = _override_factory
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


async def _create_and_login_user(client: AsyncClient, session_factory, redis_client, email: str) -> str:
    """Create a verified user and return a session cookie value."""
    from backend.services.auth.tokens import generate_session_token, hash_token
    from datetime import timedelta

    user = await _make_user(session_factory, email=email, verified=True)
    token, token_hash = generate_session_token()
    now = datetime.now(timezone.utc)
    from backend.db.models.user import UserSession
    async with session_factory() as db:
        async with db.begin():
            db.add(UserSession(
                user_id=user.id,
                session_token_hash=token_hash,
                issued_at=now,
                expires_at=now + timedelta(days=30),
                last_seen_at=now,
            ))
    return token


# ── Deadline scan tests (1–6) ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deadline_scan_enqueues_for_tracked_users(session_factory):
    """Scan with one grant deadline in 14 days tracked by 2 users → 2 rows queued."""
    target_date = date.today() + timedelta(days=14)
    grant = await _make_grant(session_factory, deadline=target_date)
    user1 = await _make_user(session_factory, email="u1@example.com")
    user2 = await _make_user(session_factory, email="u2@example.com")
    await _make_track(session_factory, user=user1, grant=grant)
    await _make_track(session_factory, user=user2, grant=grant)

    ctx = _make_ctx(session_factory)
    await enqueue_deadline_alerts(ctx)

    assert await _count_deliveries(session_factory, alert_kind="deadline_reminder") == 2
    mock_redis = ctx["redis"]
    assert len(mock_redis.enqueued) == 2
    assert all(fn == "send_deadline_alert" for fn, _ in mock_redis.enqueued)


@pytest.mark.asyncio
async def test_deadline_scan_idempotent(session_factory):
    """Running the scan twice for the same window does not create duplicates."""
    target_date = date.today() + timedelta(days=14)
    grant = await _make_grant(session_factory, deadline=target_date)
    user = await _make_user(session_factory, email="u@example.com")
    await _make_track(session_factory, user=user, grant=grant)

    ctx = _make_ctx(session_factory)
    await enqueue_deadline_alerts(ctx)
    await enqueue_deadline_alerts(ctx)

    assert await _count_deliveries(session_factory, alert_kind="deadline_reminder") == 1


@pytest.mark.asyncio
async def test_deadline_scan_respects_deadline_reminders_false(session_factory):
    """Skip users with deadline_reminders=false in alert_preferences."""
    target_date = date.today() + timedelta(days=7)
    grant = await _make_grant(session_factory, deadline=target_date)
    user = await _make_user(
        session_factory,
        email="quiet@example.com",
        alert_preferences={"deadline_reminders": False},
    )
    await _make_track(session_factory, user=user, grant=grant)

    ctx = _make_ctx(session_factory)
    await enqueue_deadline_alerts(ctx)

    assert await _count_deliveries(session_factory, alert_kind="deadline_reminder") == 0


@pytest.mark.asyncio
async def test_deadline_scan_skips_unverified_email(session_factory):
    """Skip users without email_verified_at."""
    target_date = date.today() + timedelta(days=1)
    grant = await _make_grant(session_factory, deadline=target_date)
    user = await _make_user(session_factory, email="unverified@example.com", verified=False)
    await _make_track(session_factory, user=user, grant=grant)

    ctx = _make_ctx(session_factory)
    await enqueue_deadline_alerts(ctx)

    assert await _count_deliveries(session_factory, alert_kind="deadline_reminder") == 0


@pytest.mark.asyncio
async def test_deadline_scan_skips_disabled_users(session_factory):
    """Skip disabled users."""
    target_date = date.today() + timedelta(days=14)
    grant = await _make_grant(session_factory, deadline=target_date)
    user = await _make_user(session_factory, email="disabled@example.com", disabled=True)
    await _make_track(session_factory, user=user, grant=grant)

    ctx = _make_ctx(session_factory)
    await enqueue_deadline_alerts(ctx)

    assert await _count_deliveries(session_factory, alert_kind="deadline_reminder") == 0


@pytest.mark.asyncio
async def test_deadline_scan_skips_terminal_lifecycle(session_factory):
    """Skip tracks in terminal lifecycle states."""
    target_date = date.today() + timedelta(days=14)
    grant = await _make_grant(session_factory, deadline=target_date)
    user = await _make_user(session_factory, email="awarded@example.com")
    await _make_track(
        session_factory, user=user, grant=grant, lifecycle_status="awarded"
    )

    ctx = _make_ctx(session_factory)
    await enqueue_deadline_alerts(ctx)

    assert await _count_deliveries(session_factory, alert_kind="deadline_reminder") == 0


# ── New grant scan tests (7–10) ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_new_grant_scan_matches_eligible_user(session_factory):
    """Fresh grant + matching user → row created with score in payload."""
    fresh_grant = await _make_grant(
        session_factory,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        last_alerted_to_users_at=None,
    )
    # Update grant to have stage/industry/location that will match
    async with session_factory() as db:
        async with db.begin():
            await db.execute(
                sa.update(Grant)
                .where(Grant.id == fresh_grant.id)
                .values(stage=["seed", "series-a"], industry=["technology"], location=["US"])
            )

    user = await _make_user(session_factory, email="match@example.com")
    await _make_profile(
        session_factory,
        user=user,
        company_stage="seed",
        location="US",
        industry=["technology"],
        incorporation_country="US",
    )

    ctx = _make_ctx(session_factory)
    await enqueue_new_grant_alerts(ctx)

    count = await _count_deliveries(session_factory, alert_kind="new_grant_match")
    assert count >= 1

    # Verify payload has score
    async with session_factory() as db:
        result = await db.execute(
            sa.select(AlertDelivery).where(AlertDelivery.alert_kind == "new_grant_match")
        )
        delivery = result.scalar_one()
    assert "score" in delivery.payload
    assert delivery.payload["score"] > 0


@pytest.mark.asyncio
async def test_new_grant_scan_skips_empty_profile(session_factory):
    """Skip users with empty/incomplete profiles."""
    fresh_grant = await _make_grant(
        session_factory,
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    user = await _make_user(session_factory, email="empty@example.com")
    # Profile with missing stage — should be skipped
    async with session_factory() as db:
        async with db.begin():
            p = Profile(
                session_id=canonical_session_id_for_user(user.id),
                company_stage=None,  # no stage
                location=None,
                incorporation_country=None,
            )
            db.add(p)

    ctx = _make_ctx(session_factory)
    await enqueue_new_grant_alerts(ctx)

    assert await _count_deliveries(session_factory, alert_kind="new_grant_match") == 0


@pytest.mark.asyncio
async def test_new_grant_scan_skips_already_alerted(session_factory):
    """Grants where last_alerted_to_users_at is not null are skipped."""
    already_alerted = await _make_grant(
        session_factory,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        last_alerted_to_users_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    user = await _make_user(session_factory, email="skip@example.com")
    await _make_profile(session_factory, user=user)

    ctx = _make_ctx(session_factory)
    await enqueue_new_grant_alerts(ctx)

    assert await _count_deliveries(session_factory, alert_kind="new_grant_match") == 0


@pytest.mark.asyncio
async def test_new_grant_scan_sets_last_alerted_at(session_factory):
    """After scan, last_alerted_to_users_at is set on the grant."""
    fresh_grant = await _make_grant(
        session_factory,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    # No users — grant should still be marked as processed
    ctx = _make_ctx(session_factory)
    await enqueue_new_grant_alerts(ctx)

    async with session_factory() as db:
        result = await db.execute(
            sa.select(Grant).where(Grant.id == fresh_grant.id)
        )
        grant = result.scalar_one()
    assert grant.last_alerted_to_users_at is not None


# ── Check-in scan tests (11–12) ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_checkin_scan_enqueues_for_stale_track(session_factory):
    """Stale tracked grant (15 days) → check-in row created with ISO week key."""
    stale_at = datetime.now(timezone.utc) - timedelta(days=15)
    user = await _make_user(session_factory, email="stale@example.com")
    grant = await _make_grant(session_factory)
    await _make_track(
        session_factory, user=user, grant=grant, lifecycle_updated_at=stale_at
    )

    ctx = _make_ctx(session_factory)
    await enqueue_checkin_alerts(ctx)

    count = await _count_deliveries(session_factory, alert_kind="check_in")
    assert count == 1

    async with session_factory() as db:
        result = await db.execute(
            sa.select(AlertDelivery).where(AlertDelivery.alert_kind == "check_in")
        )
        delivery = result.scalar_one()
    today = date.today()
    iso_year, iso_week, _ = today.isocalendar()
    expected_key = f"checkin:{iso_year}-W{iso_week:02d}"
    assert delivery.key == expected_key


@pytest.mark.asyncio
async def test_checkin_scan_idempotent_same_week(session_factory):
    """Running check-in scan twice in the same week → no duplicates."""
    stale_at = datetime.now(timezone.utc) - timedelta(days=20)
    user = await _make_user(session_factory, email="idempotent@example.com")
    grant = await _make_grant(session_factory)
    await _make_track(
        session_factory, user=user, grant=grant, lifecycle_updated_at=stale_at
    )

    ctx = _make_ctx(session_factory)
    await enqueue_checkin_alerts(ctx)
    await enqueue_checkin_alerts(ctx)

    assert await _count_deliveries(session_factory, alert_kind="check_in") == 1


# ── Send function tests (13–16) ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_deadline_alert_success(session_factory):
    """send_deadline_alert: status→sent, sent_at populated, email sent with correct tag."""
    target_date = date.today() + timedelta(days=14)
    grant = await _make_grant(session_factory, deadline=target_date)
    user = await _make_user(session_factory, email="send@example.com")
    track = await _make_track(session_factory, user=user, grant=grant)

    # Create a queued delivery
    async with session_factory() as db:
        async with db.begin():
            delivery = AlertDelivery(
                user_id=user.id,
                alert_kind="deadline_reminder",
                grant_id=grant.id,
                key=f"deadline:{grant.id}:14",
                status="queued",
                payload={"deadline": target_date.isoformat(), "window_days": 14},
            )
            db.add(delivery)
            await db.flush()
            delivery_id = str(delivery.id)

    email_client = CapturingEmailClient()
    ctx = _make_ctx(session_factory, email_client=email_client)
    await send_deadline_alert(ctx, delivery_id)

    fetched = await _get_delivery(session_factory, delivery_id)
    assert fetched.status == "sent"
    assert fetched.sent_at is not None

    assert len(email_client.sent) == 1
    sent = email_client.last
    assert "days" in sent["subject"]  # e.g. "14 days: {grant_name} deadline"
    assert sent["tags"] == ["deadline_reminder"]
    assert sent["to"] == user.email_normalized


@pytest.mark.asyncio
async def test_send_deadline_alert_noop_if_not_queued(session_factory):
    """send_deadline_alert with an already-sent row → no-op, no email."""
    grant = await _make_grant(session_factory)
    user = await _make_user(session_factory, email="noop@example.com")

    async with session_factory() as db:
        async with db.begin():
            delivery = AlertDelivery(
                user_id=user.id,
                alert_kind="deadline_reminder",
                grant_id=grant.id,
                key=f"deadline:{grant.id}:7",
                status="sent",  # already sent
                payload={},
            )
            db.add(delivery)
            await db.flush()
            delivery_id = str(delivery.id)

    email_client = CapturingEmailClient()
    ctx = _make_ctx(session_factory, email_client=email_client)
    await send_deadline_alert(ctx, delivery_id)

    assert len(email_client.sent) == 0


@pytest.mark.asyncio
async def test_send_deadline_alert_failure_sets_status_and_reraises(session_factory):
    """send_deadline_alert with failing email client → status=failed, raises."""
    target_date = date.today() + timedelta(days=1)
    grant = await _make_grant(session_factory, deadline=target_date)
    user = await _make_user(session_factory, email="fail@example.com")

    async with session_factory() as db:
        async with db.begin():
            delivery = AlertDelivery(
                user_id=user.id,
                alert_kind="deadline_reminder",
                grant_id=grant.id,
                key=f"deadline:{grant.id}:1",
                status="queued",
                payload={"deadline": target_date.isoformat(), "window_days": 1},
            )
            db.add(delivery)
            await db.flush()
            delivery_id = str(delivery.id)

    ctx = _make_ctx(session_factory, email_client=FailingEmailClient())
    with pytest.raises(RuntimeError, match="SMTP unreachable"):
        await send_deadline_alert(ctx, delivery_id)

    fetched = await _get_delivery(session_factory, delivery_id)
    assert fetched.status == "failed"
    assert "SMTP unreachable" in (fetched.failure_reason or "")


@pytest.mark.asyncio
async def test_send_checkin_and_new_grant_parity(session_factory):
    """send_checkin_alert and send_new_grant_alert: shape parity with deadline variant."""
    grant = await _make_grant(session_factory)
    user = await _make_user(session_factory, email="parity@example.com")

    # Check-in delivery
    async with session_factory() as db:
        async with db.begin():
            checkin_delivery = AlertDelivery(
                user_id=user.id,
                alert_kind="check_in",
                grant_id=None,
                key="checkin:2026-W23",
                status="queued",
                payload={"track_count": 2, "oldest_track_age_days": 20},
            )
            db.add(checkin_delivery)
            await db.flush()
            checkin_id = str(checkin_delivery.id)

    email_client = CapturingEmailClient()
    ctx = _make_ctx(session_factory, email_client=email_client)
    await send_checkin_alert(ctx, checkin_id)

    fetched = await _get_delivery(session_factory, checkin_id)
    assert fetched.status == "sent"
    assert fetched.sent_at is not None
    assert email_client.last["tags"] == ["check_in"]

    # New grant delivery
    async with session_factory() as db:
        async with db.begin():
            ng_delivery = AlertDelivery(
                user_id=user.id,
                alert_kind="new_grant_match",
                grant_id=grant.id,
                key=f"new_grant:{grant.id}",
                status="queued",
                payload={"score": 0.78, "tier": "strong", "matched_on": ["stage"]},
            )
            db.add(ng_delivery)
            await db.flush()
            ng_id = str(ng_delivery.id)

    email_client2 = CapturingEmailClient()
    ctx2 = _make_ctx(session_factory, email_client=email_client2)
    await send_new_grant_alert(ctx2, ng_id)

    fetched2 = await _get_delivery(session_factory, ng_id)
    assert fetched2.status == "sent"
    assert fetched2.sent_at is not None
    assert email_client2.last["tags"] == ["new_grant_match"]


# ── API: alert-preferences (17–18) ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_alert_preferences_get_and_put(session_factory, redis_client):
    """PUT /api/users/alert-preferences updates JSONB, GET returns it."""
    app = create_app()
    from backend.services.llm.fake import FakeLLMClient

    async def _override_db():
        async with session_factory() as session:
            yield session

    async def _override_redis():
        yield redis_client

    def _override_factory():
        return session_factory

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_db_factory] = _override_factory
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        session_token = await _create_and_login_user(
            client, session_factory, redis_client, "prefs@example.com"
        )
        cookies = {SETTINGS.AUTH_SESSION_COOKIE_NAME: session_token}

        # GET — defaults returned
        resp = await client.get("/api/users/alert-preferences", cookies=cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert data["deadline_reminders"] is True
        assert data["new_grant_matches"] is True
        assert data["check_ins"] is True

        # PUT partial update
        resp = await client.put(
            "/api/users/alert-preferences",
            json={"deadline_reminders": False},
            cookies=cookies,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["deadline_reminders"] is False
        assert data["new_grant_matches"] is True  # unchanged

        # GET confirms persistence
        resp = await client.get("/api/users/alert-preferences", cookies=cookies)
        assert resp.status_code == 200
        assert resp.json()["deadline_reminders"] is False


@pytest.mark.asyncio
async def test_alert_preferences_unauthenticated(session_factory, redis_client):
    """PUT /api/users/alert-preferences without auth → 401."""
    app = create_app()
    from backend.services.llm.fake import FakeLLMClient

    async def _override_db():
        async with session_factory() as session:
            yield session

    async def _override_redis():
        yield redis_client

    def _override_factory():
        return session_factory

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_db_factory] = _override_factory
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.put(
            "/api/users/alert-preferences", json={"deadline_reminders": False}
        )
        assert resp.status_code == 401


# ── Polymorphic session ID helper tests (20) ─────────────────────────────────


@pytest.mark.asyncio
async def test_user_session_id_roundtrip(session_factory):
    """canonical_session_id_for_user produces a session_id that tracks store
    and that can be parsed back to the original user UUID."""
    from backend.services.auth.identity import (
        canonical_session_id_for_user,
        is_user_session_id,
    )
    from backend.services.jobs.deadline_alerts import _user_id_from_session

    user = await _make_user(session_factory, email="join@example.com")
    grant = await _make_grant(session_factory)
    track = await _make_track(session_factory, user=user, grant=grant)

    # The track's session_id must be the canonical form
    assert track.session_id == canonical_session_id_for_user(user.id)
    assert is_user_session_id(track.session_id)

    # Parsing the UUID back must recover the original user.id
    parsed = _user_id_from_session(track.session_id)
    assert parsed == user.id

    # Scan logic: loading the user by the parsed ID must find the right user
    async with session_factory() as db:
        result = await db.execute(sa.select(User).where(User.id == parsed))
        found = result.scalar_one()
    assert found.id == user.id
    assert found.email_normalized == user.email_normalized
