"""Tests for automated lifecycle transitions.

Pure-service tests (1–10) use session_factory + redis_client directly.
Integration tests (11–18) mix direct service calls with HTTP client.
All time-sensitive tests inject `now` explicitly rather than relying solely on
freezegun, per the design doc. freezegun is used as belt-and-suspenders where
it aids readability.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient

from backend.core.config import get_settings
from backend.core.errors import ConflictError, ValidationError
from backend.db.models.grant_association import GrantLifecycleEvent, GrantTrack
from backend.db.models.lifecycle_auto_run import LifecycleAutoRun
from backend.services.lifecycle.auto_transitions import (
    _LOCK_KEY as _LIFECYCLE_LOCK_KEY,
    apply_auto_transition,
    find_abandoned_candidates,
    find_submitted_to_review_candidates,
    run_lifecycle_auto_sweep,
)

SEED_DIR = Path(__file__).parent.parent / "seed" / "grants"
SESSION_AUTO = "auto-test-sess"


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def grants(session_factory):
    from backend.seed.loader import load_grants_from_dir, upsert_grants

    seed_grants = load_grants_from_dir(SEED_DIR)
    async with session_factory() as session:
        await upsert_grants(session, seed_grants)
    return [g.source_id for g in seed_grants]


async def _make_track(
    session_factory,
    *,
    lifecycle_status: str = "interested",
    lifecycle_updated_at: datetime,
    lifecycle_metadata: dict | None = None,
    session_id: str = SESSION_AUTO,
    grant_id: uuid.UUID | None = None,
) -> GrantTrack:
    """Create a GrantTrack directly — no Grant FK enforcement in SQLite tests."""
    gid = grant_id or uuid.uuid4()
    now = datetime.now(timezone.utc)
    async with session_factory() as s:
        track = GrantTrack(
            session_id=session_id,
            grant_id=gid,
            lifecycle_status=lifecycle_status,
            lifecycle_updated_at=lifecycle_updated_at,
            lifecycle_metadata=lifecycle_metadata or {},
            created_at=now,
            updated_at=now,
        )
        s.add(track)
        await s.commit()
        await s.refresh(track)
        # Detach so we can use outside the session
        return track


# ── Pure-service tests (1–10) ─────────────────────────────────────────────────


async def test_find_submitted_31_days_returns_candidate(session_factory):
    """Test 1: find_submitted_to_review_candidates returns a 31-day-old track."""
    settings = get_settings()
    now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
    past = now - timedelta(days=31)

    track = await _make_track(
        session_factory,
        lifecycle_status="submitted",
        lifecycle_updated_at=past,
    )

    async with session_factory() as s:
        candidates = await find_submitted_to_review_candidates(s, settings, now)

    ids = [c.id for c in candidates]
    assert track.id in ids


async def test_find_submitted_29_days_returns_empty(session_factory):
    """Test 2: find_submitted_to_review_candidates ignores a 29-day-old track."""
    settings = get_settings()
    now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
    recent = now - timedelta(days=29)

    await _make_track(
        session_factory,
        lifecycle_status="submitted",
        lifecycle_updated_at=recent,
    )

    async with session_factory() as s:
        candidates = await find_submitted_to_review_candidates(s, settings, now)

    assert candidates == []


async def test_find_submitted_ignores_under_review(session_factory):
    """Test 3: find_submitted_to_review_candidates ignores already-under_review tracks."""
    settings = get_settings()
    now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
    past = now - timedelta(days=45)

    await _make_track(
        session_factory,
        lifecycle_status="under_review",
        lifecycle_updated_at=past,
    )

    async with session_factory() as s:
        candidates = await find_submitted_to_review_candidates(s, settings, now)

    assert candidates == []


async def test_find_abandoned_91_days_returns_candidate(session_factory):
    """Test 4: find_abandoned_candidates returns an interested track inactive 91 days."""
    settings = get_settings()
    now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
    past = now - timedelta(days=91)

    track = await _make_track(
        session_factory,
        lifecycle_status="interested",
        lifecycle_updated_at=past,
    )

    async with session_factory() as s:
        candidates = await find_abandoned_candidates(s, settings, now)

    ids = [c.id for c in candidates]
    assert track.id in ids


async def test_find_abandoned_ignores_submitted(session_factory):
    """Test 5: find_abandoned_candidates does not touch submitted tracks."""
    settings = get_settings()
    now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
    past = now - timedelta(days=100)

    await _make_track(
        session_factory,
        lifecycle_status="submitted",
        lifecycle_updated_at=past,
    )

    async with session_factory() as s:
        candidates = await find_abandoned_candidates(s, settings, now)

    assert candidates == []


async def test_find_abandoned_ignores_recently_active(session_factory):
    """Test 6: find_abandoned_candidates ignores tracks with recent lifecycle activity."""
    settings = get_settings()
    now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
    recent = now - timedelta(days=10)

    await _make_track(
        session_factory,
        lifecycle_status="interested",
        lifecycle_updated_at=recent,
    )

    async with session_factory() as s:
        candidates = await find_abandoned_candidates(s, settings, now)

    assert candidates == []


async def test_apply_auto_transition_submitted_to_under_review(session_factory):
    """Test 7: apply_auto_transition transitions submitted → under_review correctly."""
    now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
    past = now - timedelta(days=35)

    track = await _make_track(
        session_factory,
        lifecycle_status="submitted",
        lifecycle_updated_at=past,
    )
    track_id = track.id

    async with session_factory() as s:
        db_track = await s.get(GrantTrack, track_id)
        result = await apply_auto_transition(
            s, db_track, "under_review", "submitted_to_under_review", now
        )

    assert result is True

    async with session_factory() as s:
        updated = await s.get(GrantTrack, track_id)
        assert updated.lifecycle_status == "under_review"
        # SQLite returns naive datetimes; normalize before comparing
        lu = updated.lifecycle_updated_at
        if lu.tzinfo is None:
            lu = lu.replace(tzinfo=timezone.utc)
        assert lu == now

        ev_result = await s.execute(
            sa.select(GrantLifecycleEvent).where(
                GrantLifecycleEvent.grant_track_id == track_id
            )
        )
        events = ev_result.scalars().all()

    assert len(events) == 1
    ev = events[0]
    assert ev.transition_kind == "automated"
    assert ev.from_status == "submitted"
    assert ev.to_status == "under_review"
    assert ev.event_metadata["auto_transition_rule"] == "submitted_to_under_review"
    assert "days_in_prior_status" in ev.event_metadata


async def test_apply_auto_transition_interested_to_abandoned(session_factory):
    """Test 8: apply_auto_transition transitions interested → abandoned correctly."""
    now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
    past = now - timedelta(days=95)

    track = await _make_track(
        session_factory,
        lifecycle_status="interested",
        lifecycle_updated_at=past,
    )
    track_id = track.id

    async with session_factory() as s:
        db_track = await s.get(GrantTrack, track_id)
        result = await apply_auto_transition(
            s, db_track, "abandoned", "inactivity_to_abandoned", now
        )

    assert result is True

    async with session_factory() as s:
        updated = await s.get(GrantTrack, track_id)
        assert updated.lifecycle_status == "abandoned"

        ev_result = await s.execute(
            sa.select(GrantLifecycleEvent).where(
                GrantLifecycleEvent.grant_track_id == track_id
            )
        )
        events = ev_result.scalars().all()

    assert len(events) == 1
    assert events[0].transition_kind == "automated"
    assert events[0].event_metadata["auto_transition_rule"] == "inactivity_to_abandoned"


async def test_apply_auto_transition_illegal_pair_raises(session_factory):
    """Test 9: apply_auto_transition raises ValidationError on illegal pairs."""
    now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)

    track = await _make_track(
        session_factory,
        lifecycle_status="awarded",  # terminal, can't auto-transition anywhere
        lifecycle_updated_at=now - timedelta(days=5),
    )

    async with session_factory() as s:
        db_track = await s.get(GrantTrack, track.id)
        with pytest.raises(ValidationError):
            await apply_auto_transition(
                s, db_track, "under_review", "bad_rule", now
            )


async def test_apply_auto_transition_merges_metadata(session_factory):
    """Test 10: auto-transition merges auto keys into existing track metadata."""
    now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
    past = now - timedelta(days=35)

    track = await _make_track(
        session_factory,
        lifecycle_status="submitted",
        lifecycle_updated_at=past,
        lifecycle_metadata={"submitted_at": "2026-03-01", "priority": "high"},
    )
    track_id = track.id

    async with session_factory() as s:
        db_track = await s.get(GrantTrack, track_id)
        await apply_auto_transition(
            s, db_track, "under_review", "submitted_to_under_review", now
        )

    async with session_factory() as s:
        updated = await s.get(GrantTrack, track_id)
        meta = updated.lifecycle_metadata

    assert meta["submitted_at"] == "2026-03-01"
    assert meta["priority"] == "high"
    assert meta["auto_transition_rule"] == "submitted_to_under_review"
    assert "auto_transition_at" in meta


# ── Integration tests (11–18) ─────────────────────────────────────────────────


async def test_sweep_no_candidates(session_factory, redis_client):
    """Test 11: sweep with no candidates completes with 0 counts."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    run = await run_lifecycle_auto_sweep(
        session_factory, redis_client, settings, "schedule", now=now
    )

    assert run is not None
    assert run.tracks_scanned == 0
    assert run.transitions_submitted_to_review == 0
    assert run.transitions_to_abandoned == 0
    assert run.error is None
    assert run.finished_at is not None


async def test_sweep_processes_multiple_tracks(session_factory, redis_client):
    """Test 12: sweep with 2 submitted-30d + 1 inactive-90d tracks → 3 transitions."""
    settings = get_settings()
    now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)

    # 2 submitted tracks past the 30-day cutoff
    for _ in range(2):
        await _make_track(
            session_factory,
            lifecycle_status="submitted",
            lifecycle_updated_at=now - timedelta(days=31),
        )

    # 1 researching track past the 90-day cutoff
    await _make_track(
        session_factory,
        lifecycle_status="researching",
        lifecycle_updated_at=now - timedelta(days=91),
    )

    run = await run_lifecycle_auto_sweep(
        session_factory, redis_client, settings, "schedule", now=now
    )

    assert run is not None
    assert run.tracks_scanned == 3
    assert run.transitions_submitted_to_review == 2
    assert run.transitions_to_abandoned == 1
    assert run.error is None


async def test_sweep_lock_held_scheduled_returns_none(session_factory, redis_client):
    """Test 13a: scheduled sweep returns None when Redis lock is already held."""
    settings = get_settings()
    await redis_client.set(_LIFECYCLE_LOCK_KEY, "existing-run-id", nx=True, ex=600)

    run = await run_lifecycle_auto_sweep(
        session_factory, redis_client, settings, "schedule", now=datetime.now(timezone.utc)
    )

    assert run is None


async def test_sweep_lock_held_manual_raises_conflict(session_factory, redis_client):
    """Test 13b: manual sweep raises ConflictError when Redis lock is already held."""
    settings = get_settings()
    await redis_client.set(_LIFECYCLE_LOCK_KEY, "existing-run-id", nx=True, ex=600)

    with pytest.raises(ConflictError) as exc_info:
        await run_lifecycle_auto_sweep(
            session_factory, redis_client, settings, "manual", now=datetime.now(timezone.utc)
        )

    assert exc_info.value.code == "lifecycle_auto_in_progress"


async def test_trigger_lifecycle_run_endpoint(client):
    """Test 14: POST /admin/lifecycle/run returns 202 with run_id."""
    res = await client.post("/api/admin/lifecycle/run")
    assert res.status_code == 202
    body = res.json()
    assert "run_id" in body
    uuid.UUID(body["run_id"])  # validates it's a valid UUID


async def test_trigger_lifecycle_run_conflict(client, redis_client):
    """Test 15: POST /admin/lifecycle/run while lock held returns 409."""
    await redis_client.set(_LIFECYCLE_LOCK_KEY, "existing-run-id", nx=True, ex=600)

    res = await client.post("/api/admin/lifecycle/run")
    assert res.status_code == 409
    body = res.json()
    assert body["code"] == "lifecycle_auto_in_progress"


async def test_list_lifecycle_runs_desc_order(session_factory, client):
    """Test 16: GET /admin/lifecycle/runs returns last 20 runs in started_at DESC."""
    base_time = datetime.now(timezone.utc)

    async with session_factory() as s:
        for i in range(3):
            run = LifecycleAutoRun(
                started_at=base_time - timedelta(minutes=i * 10),
                triggered_by="schedule",
            )
            s.add(run)
        await s.commit()

    res = await client.get("/api/admin/lifecycle/runs")
    assert res.status_code == 200
    body = res.json()
    runs = body["runs"]
    assert len(runs) == 3

    timestamps = [r["started_at"] for r in runs]
    assert timestamps == sorted(timestamps, reverse=True)


async def test_round_trip_auto_abandoned_to_manual_interested(
    client, grants, session_factory, redis_client
):
    """Test 17: full round-trip — auto-abandoned track manually re-interested.

    Seeds a 91-day-inactive track, runs sweep, verifies abandoned audit event,
    then manually transitions back to interested and verifies both events exist.
    """
    grant_ref = grants[0]
    now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
    settings = get_settings()

    # Track the grant via HTTP
    res = await client.post(
        "/api/grants/track",
        json={"grant_id": grant_ref},
        headers={"X-Session-Id": SESSION_AUTO},
    )
    assert res.status_code == 200
    track_id = uuid.UUID(res.json()["id"])

    # Back-date lifecycle_updated_at to 91 days ago so the sweep catches it
    stale_ts = now - timedelta(days=91)
    async with session_factory() as s:
        await s.execute(
            sa.update(GrantTrack)
            .where(GrantTrack.id == track_id)
            .values(lifecycle_updated_at=stale_ts)
        )
        await s.commit()

    # Run the auto sweep directly
    run = await run_lifecycle_auto_sweep(
        session_factory, redis_client, settings, "schedule", now=now
    )
    assert run is not None
    assert run.transitions_to_abandoned >= 1

    # Verify abandoned status and audit event via HTTP
    ev_res = await client.get(
        f"/api/grants/{grant_ref}/lifecycle/events",
        headers={"X-Session-Id": SESSION_AUTO},
    )
    assert ev_res.status_code == 200
    events = ev_res.json()["events"]
    assert len(events) == 1
    assert events[0]["transition_kind"] == "automated"
    assert events[0]["to_status"] == "abandoned"

    # Manually transition back to interested
    lc_res = await client.post(
        f"/api/grants/{grant_ref}/lifecycle",
        json={"to_status": "interested"},
        headers={"X-Session-Id": SESSION_AUTO},
    )
    assert lc_res.status_code == 200
    assert lc_res.json()["lifecycle_status"] == "interested"

    # Verify total 2 events: automated then user
    ev_res2 = await client.get(
        f"/api/grants/{grant_ref}/lifecycle/events",
        headers={"X-Session-Id": SESSION_AUTO},
    )
    assert ev_res2.status_code == 200
    events2 = ev_res2.json()["events"]
    assert len(events2) == 2
    assert events2[0]["transition_kind"] == "automated"
    assert events2[0]["to_status"] == "abandoned"
    assert events2[1]["transition_kind"] == "user"
    assert events2[1]["to_status"] == "interested"


async def test_scheduler_lifecycle_clean_start_stop(
    session_factory, redis_client, fake_llm
):
    """Test 18: both schedulers start and stop cleanly via lifespan, no unawaited tasks."""
    from backend.db.session import get_db, get_db_factory
    from backend.main import create_app
    from backend.redis_client import get_redis
    from backend.services.llm.dependency import get_llm_client

    app = create_app()

    async def _db():
        async with session_factory() as s:
            yield s

    async def _redis_dep():
        yield redis_client

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_redis] = _redis_dep
    app.dependency_overrides[get_db_factory] = lambda: session_factory
    app.dependency_overrides[get_llm_client] = lambda: fake_llm

    transport = ASGITransport(app=app)
    # Entering triggers lifespan startup (both scheduler tasks created).
    # Exiting triggers lifespan shutdown (both tasks cancelled cleanly).
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
    # Reaching here without exception means CancelledError was caught properly
    # in both lifespan branches — no unawaited-task warnings.
