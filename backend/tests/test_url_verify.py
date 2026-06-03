"""Tests for URL verification service and endpoints."""
from __future__ import annotations

import uuid

import httpx
import pytest
import respx
import sqlalchemy as sa

from backend.core.config import Settings
from backend.db.models.grant import Grant
from backend.db.models.verification_run import VerificationRun
from backend.services.url_verify import verify_grant_url, run_verification_sweep

# ── helpers ───────────────────────────────────────────────────────────────────


def _settings(**overrides) -> Settings:
    s = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/0",
        URL_VERIFY_TIMEOUT_SECONDS=10.0,
        URL_VERIFY_USER_AGENT="TestBot/1.0",
        URL_VERIFY_CONCURRENCY=5,
        URL_VERIFY_GONE_THRESHOLD=3,
        URL_VERIFY_REDIS_LOCK_TTL_SECONDS=30,
        URL_VERIFY_ENABLED=True,
        URL_VERIFY_INTERVAL_HOURS=168,
    )
    for k, v in overrides.items():
        object.__setattr__(s, k, v)
    return s


def _make_grant(**overrides) -> Grant:
    defaults = dict(
        source_id="test-grant",
        name="Test Grant",
        type="grant",
        description="Test",
        url="https://example.com",
        status="active",
        consecutive_failures=0,
        last_verification_error=None,
        source_status="unknown",
        provider_name="Test Org",
        eligibility={},
        rolling=False,
    )
    defaults.update(overrides)
    return Grant(**defaults)


# ── Unit tests: verify_grant_url ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_200_ok_resets_failures():
    """200 with no redirects → ok, consecutive_failures reset to 0."""
    grant = _make_grant(consecutive_failures=2)
    settings = _settings()

    with respx.mock:
        respx.head("https://example.com").mock(return_value=httpx.Response(200))

        async with httpx.AsyncClient() as client:
            result = await verify_grant_url(client, grant, settings)

    assert result.source_status == "ok"
    assert result.new_consecutive_failures == 0
    assert result.last_verification_error is None
    assert result.should_archive is False


@pytest.mark.asyncio
async def test_verify_200_with_redirects():
    """200 after a redirect chain → redirect, failures unchanged, logged."""
    grant = _make_grant(consecutive_failures=1)
    settings = _settings()

    with respx.mock:
        respx.head("https://example.com").mock(
            return_value=httpx.Response(
                301, headers={"location": "https://www.example.com"}
            )
        )
        respx.head("https://www.example.com").mock(
            return_value=httpx.Response(200)
        )

        async with httpx.AsyncClient(follow_redirects=True) as client:
            result = await verify_grant_url(client, grant, settings)

    assert result.source_status == "redirect"
    assert result.new_consecutive_failures == 1  # unchanged — redirect is healthy
    assert result.last_verification_error is None
    assert result.should_archive is False


@pytest.mark.asyncio
async def test_verify_404_increments_failures():
    """404 → gone, consecutive_failures incremented."""
    grant = _make_grant(consecutive_failures=0)
    settings = _settings()

    with respx.mock:
        respx.head("https://example.com").mock(return_value=httpx.Response(404))

        async with httpx.AsyncClient() as client:
            result = await verify_grant_url(client, grant, settings)

    assert result.source_status == "gone"
    assert result.new_consecutive_failures == 1
    assert result.should_archive is False


@pytest.mark.asyncio
async def test_verify_410_gone():
    """410 → gone, same behavior as 404."""
    grant = _make_grant(consecutive_failures=1)
    settings = _settings()

    with respx.mock:
        respx.head("https://example.com").mock(return_value=httpx.Response(410))

        async with httpx.AsyncClient() as client:
            result = await verify_grant_url(client, grant, settings)

    assert result.source_status == "gone"
    assert result.new_consecutive_failures == 2


@pytest.mark.asyncio
async def test_verify_500_transient_leaves_failures_unchanged():
    """5xx → error, consecutive_failures unchanged (server problem, not URL problem)."""
    grant = _make_grant(consecutive_failures=1)
    settings = _settings()

    with respx.mock:
        respx.head("https://example.com").mock(return_value=httpx.Response(500))

        async with httpx.AsyncClient() as client:
            result = await verify_grant_url(client, grant, settings)

    assert result.source_status == "error"
    assert result.new_consecutive_failures == 1  # unchanged
    assert result.last_verification_error == "HTTP 500"
    assert result.should_archive is False


@pytest.mark.asyncio
async def test_verify_timeout():
    """Timeout → error with last_verification_error='timeout'."""
    grant = _make_grant(consecutive_failures=0)
    settings = _settings()

    with respx.mock:
        respx.head("https://example.com").mock(
            side_effect=httpx.TimeoutException("timed out")
        )

        async with httpx.AsyncClient() as client:
            result = await verify_grant_url(client, grant, settings)

    assert result.source_status == "error"
    assert result.last_verification_error == "timeout"
    assert result.new_consecutive_failures == 0  # unchanged


@pytest.mark.asyncio
async def test_verify_405_falls_back_to_get():
    """HEAD returns 405 → retry with GET → ok."""
    grant = _make_grant(consecutive_failures=0)
    settings = _settings()

    with respx.mock:
        respx.head("https://example.com").mock(return_value=httpx.Response(405))
        respx.get("https://example.com").mock(return_value=httpx.Response(200))

        async with httpx.AsyncClient() as client:
            result = await verify_grant_url(client, grant, settings)

    assert result.source_status == "ok"
    assert result.new_consecutive_failures == 0


@pytest.mark.asyncio
async def test_verify_three_gone_runs_archives_grant():
    """Three consecutive 'gone' results cross the threshold → should_archive=True."""
    settings = _settings(URL_VERIFY_GONE_THRESHOLD=3)
    grant = _make_grant(consecutive_failures=0)

    with respx.mock:
        respx.head("https://example.com").mock(return_value=httpx.Response(404))

        async with httpx.AsyncClient() as client:
            r1 = await verify_grant_url(client, grant, settings)
            grant.consecutive_failures = r1.new_consecutive_failures

            r2 = await verify_grant_url(client, grant, settings)
            grant.consecutive_failures = r2.new_consecutive_failures

            r3 = await verify_grant_url(client, grant, settings)

    assert r1.should_archive is False
    assert r2.should_archive is False
    assert r3.should_archive is True
    assert r3.new_consecutive_failures == 3


@pytest.mark.asyncio
async def test_verify_gone_then_ok_resets_failures():
    """One gone followed by one ok → consecutive_failures back to 0, not archived."""
    settings = _settings()
    grant = _make_grant(consecutive_failures=0)

    with respx.mock:
        respx.head("https://example.com").mock(return_value=httpx.Response(404))
        async with httpx.AsyncClient() as client:
            r_gone = await verify_grant_url(client, grant, settings)

    assert r_gone.source_status == "gone"
    grant.consecutive_failures = r_gone.new_consecutive_failures

    with respx.mock:
        respx.head("https://example.com").mock(return_value=httpx.Response(200))
        async with httpx.AsyncClient() as client:
            r_ok = await verify_grant_url(client, grant, settings)

    assert r_ok.source_status == "ok"
    assert r_ok.new_consecutive_failures == 0
    assert r_ok.should_archive is False


# ── Integration tests: endpoints + sweep ─────────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_verification_returns_202_and_updates_run(
    client, session_factory, seeded_grants, redis_client
):
    """POST /admin/verification/run → 202, background task updates verification_runs."""
    with respx.mock(assert_all_called=False) as rx:
        rx.head(url__regex=r"https?://").mock(return_value=httpx.Response(200))

        res = await client.post("/api/admin/verification/run")
        assert res.status_code == 202, res.text
        body = res.json()
        assert "run_id" in body
        run_id = body["run_id"]

    async with session_factory() as s:
        run = await s.get(VerificationRun, uuid.UUID(run_id))

    assert run is not None
    assert run.triggered_by == "manual"
    assert run.finished_at is not None
    assert run.grants_ok == run.grants_checked
    assert run.grants_failed == 0
    assert run.grants_checked > 0


@pytest.mark.asyncio
async def test_trigger_verification_while_locked_returns_409(
    client, redis_client
):
    """POST /admin/verification/run while Redis lock is held → 409."""
    fake_run_id = str(uuid.uuid4())
    await redis_client.set("url_verify:lock", fake_run_id, ex=60)

    res = await client.post("/api/admin/verification/run")
    assert res.status_code == 409
    body = res.json()
    assert body["code"] == "verification_in_progress"
    assert body["run_id"] == fake_run_id


@pytest.mark.asyncio
async def test_get_grant_verification_before_any_run(client, seeded_grants):
    """GET /grants/{ref}/verification before any run → source_status='unknown'."""
    res = await client.get("/api/grants/nsf-sbir-phase-1/verification")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["source_status"] == "unknown"
    assert body["last_verified_at"] is None
    assert body["consecutive_failures"] == 0
    assert body["last_verification_error"] is None


@pytest.mark.asyncio
async def test_get_grant_verification_after_successful_run(
    client, session_factory, seeded_grants, redis_client
):
    """GET /grants/{ref}/verification after a sweep → source_status='ok'."""
    with respx.mock(assert_all_called=False) as rx:
        rx.head(url__regex=r"https?://").mock(return_value=httpx.Response(200))
        await client.post("/api/admin/verification/run")

    res = await client.get("/api/grants/nsf-sbir-phase-1/verification")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["source_status"] == "ok"
    assert body["last_verified_at"] is not None
    assert body["consecutive_failures"] == 0


@pytest.mark.asyncio
async def test_list_verification_runs_ordered_newest_first(
    client, session_factory, redis_client
):
    """GET /admin/verification/runs returns runs ordered by started_at DESC, max 20."""
    with respx.mock(assert_all_called=False) as rx:
        rx.head(url__regex=r"https?://").mock(return_value=httpx.Response(200))

        r1 = await client.post("/api/admin/verification/run")
        assert r1.status_code == 202

        r2 = await client.post("/api/admin/verification/run")
        assert r2.status_code == 202

    res = await client.get("/api/admin/verification/runs")
    assert res.status_code == 200, res.text
    runs = res.json()["runs"]
    assert len(runs) >= 2

    # Verify ordering: newest first
    started_ats = [r["started_at"] for r in runs]
    for i in range(len(started_ats) - 1):
        assert started_ats[i] >= started_ats[i + 1]


# ── Archive smoke test ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_grant_archived_after_three_gone_sweep(session_factory, redis_client):
    """Three consecutive 404 sweeps flip grant.status to 'archived'."""
    settings = _settings(URL_VERIFY_GONE_THRESHOLD=3)

    target_url = "https://gone-grant.example.com"
    async with session_factory() as s:
        grant = Grant(
            source_id="gone-test",
            name="Gone Grant",
            type="grant",
            description="Will be gone",
            url=target_url,
            status="active",
            provider_name="Test",
            eligibility={},
            rolling=False,
        )
        s.add(grant)
        await s.commit()
        grant_id = grant.id

    with respx.mock:
        respx.head(target_url).mock(return_value=httpx.Response(404))

        for _ in range(3):
            await run_verification_sweep(
                session_factory, redis_client, settings, "schedule"
            )

    async with session_factory() as s:
        result = await s.execute(sa.select(Grant).where(Grant.id == grant_id))
        archived_grant = result.scalar_one()

    assert archived_grant.status == "archived"
    assert archived_grant.consecutive_failures == 3
    assert archived_grant.source_status == "gone"
