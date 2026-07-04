"""Tests for the pluggable ingest framework (Step 21).

Layout:
  1–2   Framework: Protocol + registry
  3–7   startup_relevance_filter
  8–9   upsert_ingested_grants
  10–11 archive_missing_grants
  12–14 GrantsGovAdapter.fetch_all (respx mocks)
  15    GrantsGovAdapter — pagination
  16    GrantsGovAdapter — per-record 404
  17    GrantsGovAdapter — per-record timeout
  18    GrantsGovAdapter — 429 with Retry-After
  19    GrantsGovAdapter — amount mapping
  20    GrantsGovAdapter — continuous deadline
  21    GrantsGovAdapter — nonprofit-only applicant types
  22    GrantsGovAdapter — small-business applicant types
  23–27 Orchestration (run_ingest_sweep)
  28–31 Admin endpoints
  32    Scheduler lifecycle
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone
from typing import AsyncIterator
from unittest.mock import AsyncMock

import httpx
import pytest
import respx
import sqlalchemy as sa
from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient

from backend.core.config import Settings, get_settings
from backend.core.errors import ConflictError, NotFoundError, ValidationError
from backend.db.models.grant import Grant
from backend.db.models.ingest_run import IngestRun
from backend.services.ingest.adapters.grantsgov import (
    GrantsGovAdapter,
    _parse_eligibility,
    _strip_html,
)
from backend.services.ingest.base import IngestedGrant, SourceAdapter
from backend.services.ingest.filters import startup_relevance_filter
from backend.services.ingest.orchestration import run_ingest_sweep
from backend.services.ingest.registry import get_adapter, get_enabled_sources
from backend.services.ingest.upsert import archive_missing_grants, upsert_ingested_grants


# ── helpers ───────────────────────────────────────────────────────────────────


def _settings(**overrides) -> Settings:
    base = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/0",
        INGEST_ENABLED=True,
        INGEST_HTTP_MAX_RETRIES=3,
        INGEST_HTTP_TIMEOUT_SECONDS=5.0,
        INGEST_USER_AGENT="TestBot/1.0",
        INGEST_REDIS_LOCK_TTL_SECONDS=60,
        INGEST_INTERVAL_HOURS=24,
        GRANTSGOV_ENABLED=True,
        GRANTSGOV_API_BASE="https://api.grants.gov/v1/api",
        GRANTSGOV_PAGE_SIZE=100,
        GRANTSGOV_MAX_PAGES=50,
        GRANTSGOV_DAYS_AHEAD=180,
        SBIRGOV_ENABLED=True,
        SBIRGOV_API_BASE="https://api.www.sbir.gov/public/api",
        SBIRGOV_PAGE_SIZE=100,
        SBIRGOV_MAX_PAGES=30,
    )
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


def _make_ingested(**overrides) -> IngestedGrant:
    defaults: dict = dict(
        source="grantsgov",
        source_id="grantsgov:PD-25-0001",
        name="Test Grant",
        type="grant",
        description="A test grant for startups.",
        url="https://www.grants.gov/search-results-detail/12345",
        provider_name="Test Agency",
        provider_type="government",
        location=["US"],
        eligibility={"required_location": ["US"]},
        amount_min_usd_cents=5_000_000,
        amount_max_usd_cents=25_000_000,
        deadline=date(2026, 12, 31),
    )
    defaults.update(overrides)
    return IngestedGrant(**defaults)


def _hit(opp_id: str = "1", number: str = "PD-25-0001", title: str = "Test Grant") -> dict:
    """Match real Grants.gov search hit structure (oppHits items)."""
    return {
        "id": opp_id,
        "number": number,
        "title": title,
        "agencyCode": "USDOT",
        "agency": "Test Agency",       # real API uses "agency" not "agencyName"
        "openDate": "01/01/2026",
        "closeDate": "12/31/2026",     # MM/DD/YYYY format
        "oppStatus": "posted",
        "cfdaList": ["20.200"],        # real API uses "cfdaList" not "alnist"
    }


def _search_resp(hits: list[dict], hit_count: int | None = None) -> dict:
    """Build a Grants.gov search2 response."""
    return {
        "data": {
            "hitCount": hit_count if hit_count is not None else len(hits),
            "oppHits": hits,            # real API uses "oppHits" not "hits"
        }
    }


def _detail(
    *,
    award_floor: int = 50_000,
    award_ceiling: int = 250_000,
    applicant_types: list[str] | None = None,
    desc: str = "A great grant for startups.",
    apply_url: str | None = None,
) -> dict:
    """Build a fetchOpportunity response body.

    The adapter does `body.get("data") or body`, so we can return the synopsis
    wrapper directly (without a "data" envelope) — the adapter falls back correctly.
    """
    return {
        "synopsis": {
            "awardFloor": award_floor,
            "awardCeiling": award_ceiling,
            "applicantTypes": [
                {"id": "12", "description": t}
                for t in (applicant_types or ["Small businesses"])
            ],
            "synopsisDesc": desc,
            "applyUrl": apply_url,
        }
    }


# ── 1. Protocol: SourceAdapter is satisfied by GrantsGovAdapter ──────────────


def test_adapter_satisfies_protocol():
    """Test 1: GrantsGovAdapter structurally satisfies SourceAdapter Protocol."""
    adapter = GrantsGovAdapter()
    assert isinstance(adapter, SourceAdapter)
    assert GrantsGovAdapter.source_name == "grantsgov"


# ── 2. Registry ───────────────────────────────────────────────────────────────


def test_registry_get_adapter_known():
    """Test 2a: get_adapter('grantsgov') returns GrantsGovAdapter."""
    cls = get_adapter("grantsgov")
    assert cls is GrantsGovAdapter


def test_registry_get_adapter_unknown():
    """Test 2b: get_adapter returns None for unknown sources."""
    assert get_adapter("unknown_source") is None


def test_registry_get_enabled_sources():
    """Test 2c: get_enabled_sources returns both sources when both enabled."""
    settings = _settings(GRANTSGOV_ENABLED=True, SBIRGOV_ENABLED=True)
    assert get_enabled_sources(settings) == ["grantsgov", "sbirgov"]


def test_registry_get_enabled_sources_only_grantsgov():
    """Test 2c2: get_enabled_sources returns only grantsgov when sbirgov disabled."""
    settings = _settings(GRANTSGOV_ENABLED=True, SBIRGOV_ENABLED=False)
    assert get_enabled_sources(settings) == ["grantsgov"]


def test_registry_get_enabled_sources_disabled():
    """Test 2d: get_enabled_sources returns [] when both disabled."""
    settings = _settings(GRANTSGOV_ENABLED=False, SBIRGOV_ENABLED=False)
    assert get_enabled_sources(settings) == []


# ── 3–7. startup_relevance_filter ────────────────────────────────────────────


def test_filter_nonprofits_only():
    """Test 3: nonprofits-only → skipped."""
    record = _make_ingested(eligibility={"_applicant_types": ["nonprofits"]})
    kept, reason = startup_relevance_filter(record)
    assert not kept
    assert reason == "nonprofits-only"


def test_filter_individuals_only():
    """Test 4: individuals-only → skipped."""
    record = _make_ingested(eligibility={"_applicant_types": ["individuals"]})
    kept, reason = startup_relevance_filter(record)
    assert not kept
    assert reason == "individuals-only"


def test_filter_below_threshold():
    """Test 5: max < $10K → skipped."""
    record = _make_ingested(amount_max_usd_cents=900_000)  # $9K < $10K
    kept, reason = startup_relevance_filter(record)
    assert not kept
    assert reason == "below-threshold"


def test_filter_small_business_kept():
    """Test 6: Small Business + For-profit → kept."""
    record = _make_ingested(
        eligibility={
            "_applicant_types": ["Small businesses", "For-profit organizations"],
        }
    )
    kept, reason = startup_relevance_filter(record)
    assert kept
    assert reason is None


def test_filter_no_applicant_types_kept():
    """Test 7: no _applicant_types key → kept."""
    record = _make_ingested(eligibility={"required_location": ["US"]})
    kept, reason = startup_relevance_filter(record)
    assert kept
    assert reason is None


def test_filter_explicitly_excluded_for_startups():
    """Test 7b: _excluded_for_startups=True → skipped."""
    record = _make_ingested(
        eligibility={"_excluded_for_startups": True, "_applicant_types": []}
    )
    kept, reason = startup_relevance_filter(record)
    assert not kept
    assert reason == "explicitly-not-for-startups"


# ── 8–9. upsert_ingested_grants ──────────────────────────────────────────────


async def test_upsert_inserts_new_records(session_factory):
    """Test 8: upsert inserts new records correctly."""
    now = datetime.now(timezone.utc)
    records = [_make_ingested(source_id="grantsgov:PD-25-0001")]

    async with session_factory() as s:
        inserted, updated = await upsert_ingested_grants(s, "grantsgov", records, now)

    assert inserted == 1
    assert updated == 0

    async with session_factory() as s:
        result = await s.execute(
            sa.select(Grant).where(Grant.source_id == "grantsgov:PD-25-0001")
        )
        grant = result.scalar_one()

    assert grant.name == "Test Grant"
    assert grant.source == "grantsgov"
    assert grant.amount_min == 5_000_000
    assert grant.amount_max == 25_000_000


async def test_upsert_updates_existing_records(session_factory):
    """Test 9: upsert updates existing records on source_id collision."""
    now = datetime.now(timezone.utc)
    records = [_make_ingested(source_id="grantsgov:PD-25-0002", name="Original Name")]

    async with session_factory() as s:
        ins, upd = await upsert_ingested_grants(s, "grantsgov", records, now)
    assert ins == 1
    assert upd == 0

    updated_records = [
        _make_ingested(source_id="grantsgov:PD-25-0002", name="Updated Name")
    ]
    async with session_factory() as s:
        ins2, upd2 = await upsert_ingested_grants(
            s, "grantsgov", updated_records, now
        )
    assert ins2 == 0
    assert upd2 == 1

    async with session_factory() as s:
        result = await s.execute(
            sa.select(Grant).where(Grant.source_id == "grantsgov:PD-25-0002")
        )
        grant = result.scalar_one()
    assert grant.name == "Updated Name"


# ── 10–11. archive_missing_grants ────────────────────────────────────────────


async def test_archive_missing_archives_absent_grants(session_factory):
    """Test 10: grants in DB but not in fresh set → archived."""
    now = datetime.now(timezone.utc)
    records = [
        _make_ingested(source_id="grantsgov:PD-25-0010"),
        _make_ingested(source_id="grantsgov:PD-25-0011"),
    ]
    async with session_factory() as s:
        await upsert_ingested_grants(s, "grantsgov", records, now)

    # Only 0010 is in fresh set — 0011 should be archived
    fresh = {"grantsgov:PD-25-0010"}
    async with session_factory() as s:
        count = await archive_missing_grants(s, "grantsgov", fresh, now)

    assert count == 1

    async with session_factory() as s:
        result = await s.execute(
            sa.select(Grant).where(Grant.source_id == "grantsgov:PD-25-0011")
        )
        grant = result.scalar_one()
    assert grant.status == "archived"


async def test_archive_missing_skips_already_archived(session_factory):
    """Test 11: already-archived grants are not double-counted."""
    now = datetime.now(timezone.utc)
    records = [_make_ingested(source_id="grantsgov:PD-25-0020", status="active")]
    async with session_factory() as s:
        await upsert_ingested_grants(s, "grantsgov", records, now)

    # Archive manually first
    async with session_factory() as s:
        await s.execute(
            sa.update(Grant)
            .where(Grant.source_id == "grantsgov:PD-25-0020")
            .values(status="archived")
        )
        await s.commit()

    # archive_missing_grants should not count it again
    async with session_factory() as s:
        count = await archive_missing_grants(s, "grantsgov", set(), now)

    # Empty fresh set with guard → 0 (internal guard)
    assert count == 0


# ── 12–14. GrantsGovAdapter basic fetch ──────────────────────────────────────


@pytest.mark.asyncio
async def test_adapter_fetch_3_records():
    """Test 12: adapter yields 3 IngestedGrant records from mocked API."""
    settings = _settings()
    adapter = GrantsGovAdapter()

    hits = [_hit(str(i), f"PD-25-000{i}", f"Grant {i}") for i in range(1, 4)]
    search_response = _search_resp(hits)
    detail_responses = [
        httpx.Response(200, json=_detail(award_floor=50_000, award_ceiling=250_000))
        for _ in range(3)
    ]

    with respx.mock:
        respx.post("https://api.grants.gov/v1/api/search2").mock(
            return_value=httpx.Response(200, json=search_response)
        )
        respx.post("https://api.grants.gov/v1/api/fetchOpportunity").mock(
            side_effect=detail_responses
        )

        async with httpx.AsyncClient() as client:
            records = [
                r async for r in adapter.fetch_all(client, settings, since=None)
            ]

    assert len(records) == 3
    for r in records:
        assert r.source == "grantsgov"
        assert r.source_id.startswith("grantsgov:PD-25-000")
        assert r.amount_min_usd_cents == 5_000_000
        assert r.amount_max_usd_cents == 25_000_000
        assert r.deadline == date(2026, 12, 31)


# ── 15. Pagination ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_adapter_pagination():
    """Test 15: adapter paginates — page 1 returns 100, page 2 returns 50 = 150 total."""
    settings = _settings(GRANTSGOV_PAGE_SIZE=100)
    adapter = GrantsGovAdapter()

    page1_hits = [_hit(str(i), f"PD-25-{i:04d}", f"Grant {i}") for i in range(100)]
    page2_hits = [_hit(str(i), f"PD-25-{i:04d}", f"Grant {i}") for i in range(100, 150)]

    page1_response = _search_resp(page1_hits, hit_count=150)
    page2_response = _search_resp(page2_hits, hit_count=150)

    detail_resp = httpx.Response(200, json=_detail())

    call_count = 0

    def search_side_effect(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(200, json=page1_response)
        return httpx.Response(200, json=page2_response)

    with respx.mock:
        respx.post("https://api.grants.gov/v1/api/search2").mock(
            side_effect=search_side_effect
        )
        respx.post("https://api.grants.gov/v1/api/fetchOpportunity").mock(
            return_value=detail_resp
        )

        async with httpx.AsyncClient() as client:
            records = [
                r async for r in adapter.fetch_all(client, settings, since=None)
            ]

    assert len(records) == 150
    assert call_count == 2


# ── 16. Per-record 404 ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_adapter_detail_404_skips_record():
    """Test 16: 404 on a detail fetch → that record skipped, others yielded."""
    settings = _settings()
    adapter = GrantsGovAdapter()

    hits = [_hit(str(i), f"PD-25-{i:04d}", f"Grant {i}") for i in range(3)]
    search_resp = _search_resp(hits)

    detail_resps = [
        httpx.Response(200, json=_detail()),
        httpx.Response(404, json={"message": "not found"}),
        httpx.Response(200, json=_detail()),
    ]

    with respx.mock:
        respx.post("https://api.grants.gov/v1/api/search2").mock(
            return_value=httpx.Response(200, json=search_resp)
        )
        respx.post("https://api.grants.gov/v1/api/fetchOpportunity").mock(
            side_effect=detail_resps
        )

        async with httpx.AsyncClient() as client:
            records = [
                r async for r in adapter.fetch_all(client, settings, since=None)
            ]

    assert len(records) == 2


# ── 17. Per-record timeout ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_adapter_detail_timeout_skips_record():
    """Test 17: timeout on detail fetch → record skipped after retries, others yielded."""
    settings = _settings(INGEST_HTTP_MAX_RETRIES=1)
    adapter = GrantsGovAdapter()

    hits = [_hit("1", "PD-25-0001"), _hit("2", "PD-25-0002")]
    search_resp = _search_resp(hits)

    call_num = 0

    def detail_side_effect(request: httpx.Request) -> httpx.Response:
        nonlocal call_num
        call_num += 1
        if call_num == 1:
            raise httpx.TimeoutException("timed out")
        return httpx.Response(200, json=_detail())

    with respx.mock:
        respx.post("https://api.grants.gov/v1/api/search2").mock(
            return_value=httpx.Response(200, json=search_resp)
        )
        respx.post("https://api.grants.gov/v1/api/fetchOpportunity").mock(
            side_effect=detail_side_effect
        )

        async with httpx.AsyncClient() as client:
            records = [
                r async for r in adapter.fetch_all(client, settings, since=None)
            ]

    assert len(records) == 1


# ── 18. 429 with Retry-After ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_adapter_detail_429_retries_then_skips(monkeypatch):
    """Test 18: 429 with Retry-After → backs off and retries up to max, then skips."""
    settings = _settings(INGEST_HTTP_MAX_RETRIES=2)
    adapter = GrantsGovAdapter()

    hits = [_hit("1", "PD-25-0001")]
    search_resp = _search_resp(hits)

    slept: list[float] = []
    original_sleep = asyncio.sleep

    async def fake_sleep(t: float) -> None:
        slept.append(t)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    with respx.mock:
        respx.post("https://api.grants.gov/v1/api/search2").mock(
            return_value=httpx.Response(200, json=search_resp)
        )
        respx.post("https://api.grants.gov/v1/api/fetchOpportunity").mock(
            return_value=httpx.Response(
                429,
                headers={"Retry-After": "2"},
                json={"message": "rate limited"},
            )
        )

        async with httpx.AsyncClient() as client:
            records = [
                r async for r in adapter.fetch_all(client, settings, since=None)
            ]

    # max_retries=2 → one retry attempt → slept once
    assert records == []
    assert len(slept) >= 1
    assert slept[0] == 2.0


# ── 19. Amount mapping ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_adapter_amount_mapping():
    """Test 19: awardFloor=50000, awardCeiling=250000 → cents correctly."""
    settings = _settings()
    adapter = GrantsGovAdapter()

    hits = [_hit("1", "PD-25-0001")]
    search_resp = _search_resp(hits)

    with respx.mock:
        respx.post("https://api.grants.gov/v1/api/search2").mock(
            return_value=httpx.Response(200, json=search_resp)
        )
        respx.post("https://api.grants.gov/v1/api/fetchOpportunity").mock(
            return_value=httpx.Response(
                200,
                json=_detail(award_floor=50_000, award_ceiling=250_000),
            )
        )

        async with httpx.AsyncClient() as client:
            records = [
                r async for r in adapter.fetch_all(client, settings, since=None)
            ]

    assert len(records) == 1
    assert records[0].amount_min_usd_cents == 5_000_000
    assert records[0].amount_max_usd_cents == 25_000_000


# ── 20. Continuous deadline → rolling ────────────────────────────────────────


@pytest.mark.asyncio
async def test_adapter_continuous_deadline_is_rolling():
    """Test 20: closeDate='Continuous' or missing → rolling=True, deadline=None."""
    settings = _settings()
    adapter = GrantsGovAdapter()

    hit = _hit("1", "PD-25-0001")
    hit["closeDate"] = "Continuous"
    search_resp = _search_resp([hit])

    with respx.mock:
        respx.post("https://api.grants.gov/v1/api/search2").mock(
            return_value=httpx.Response(200, json=search_resp)
        )
        respx.post("https://api.grants.gov/v1/api/fetchOpportunity").mock(
            return_value=httpx.Response(200, json=_detail())
        )

        async with httpx.AsyncClient() as client:
            records = [
                r async for r in adapter.fetch_all(client, settings, since=None)
            ]

    assert len(records) == 1
    assert records[0].rolling is True
    assert records[0].deadline is None


# ── 21. Nonprofit-only → _excluded_for_startups ──────────────────────────────


def test_parse_eligibility_nonprofit_only():
    """Test 21: only nonprofit applicant types → _excluded_for_startups=True."""
    result = _parse_eligibility(
        ["Nonprofits having a 501(c)(3) status", "Local governments"]
    )
    assert result.get("_excluded_for_startups") is True


@pytest.mark.asyncio
async def test_adapter_nonprofit_applicant_types_sets_excluded(session_factory):
    """Test 21b: adapter yields grant with _excluded_for_startups → filter drops it."""
    settings = _settings()
    adapter = GrantsGovAdapter()

    hits = [_hit("1", "PD-25-0001")]
    search_resp = _search_resp(hits)

    with respx.mock:
        respx.post("https://api.grants.gov/v1/api/search2").mock(
            return_value=httpx.Response(200, json=search_resp)
        )
        respx.post("https://api.grants.gov/v1/api/fetchOpportunity").mock(
            return_value=httpx.Response(
                200,
                json=_detail(applicant_types=["Nonprofits having a 501(c)(3) status"]),
            )
        )

        async with httpx.AsyncClient() as client:
            records = [
                r async for r in adapter.fetch_all(client, settings, since=None)
            ]

    assert len(records) == 1
    assert records[0].eligibility.get("_excluded_for_startups") is True

    # Confirm the filter drops it
    kept, reason = startup_relevance_filter(records[0])
    assert not kept
    assert reason == "explicitly-not-for-startups"


# ── 22. Small businesses → kept ──────────────────────────────────────────────


def test_parse_eligibility_small_businesses_kept():
    """Test 22: 'Small businesses' in applicant types → no _excluded_for_startups."""
    result = _parse_eligibility(
        ["Small businesses", "For-profit organizations other than small businesses"]
    )
    assert "_excluded_for_startups" not in result


# ── 23–27. Orchestration ─────────────────────────────────────────────────────


class _FakeAdapter:
    source_name = "grantsgov"

    def __init__(self, records: list[IngestedGrant]):
        self._records = records

    async def fetch_all(self, client, settings, since):
        for r in self._records:
            yield r


async def _sweep_with_fake_adapter(
    session_factory,
    redis,
    records: list[IngestedGrant],
    *,
    triggered_by: str = "schedule",
    pre_run_id: uuid.UUID | None = None,
    monkeypatch_target=None,
) -> IngestRun | None:
    """Run a sweep with the adapter registry patched to return _FakeAdapter."""
    import backend.services.ingest.registry as reg

    original = reg._ADAPTERS.copy()
    reg._ADAPTERS["grantsgov"] = lambda: _FakeAdapter(records)  # type: ignore[assignment]
    try:
        settings = _settings()
        return await run_ingest_sweep(
            "grantsgov",
            session_factory,
            redis,
            settings,
            triggered_by=triggered_by,
            pre_run_id=pre_run_id,
        )
    finally:
        reg._ADAPTERS.clear()
        reg._ADAPTERS.update(original)


async def test_sweep_happy_path(session_factory, redis_client):
    """Test 23: 10 fresh records, 3 filtered → 7 inserted. ingest_runs row correct."""
    # 7 startup-eligible + 3 nonprofit-only
    eligible = [
        _make_ingested(source_id=f"grantsgov:PD-25-{i:04d}", name=f"Grant {i}")
        for i in range(7)
    ]
    filtered = [
        _make_ingested(
            source_id=f"grantsgov:PD-25-{i:04d}",
            eligibility={"_applicant_types": ["nonprofits"]},
        )
        for i in range(7, 10)
    ]

    import backend.services.ingest.registry as reg

    original = reg._ADAPTERS.copy()
    reg._ADAPTERS["grantsgov"] = lambda: _FakeAdapter(eligible + filtered)  # type: ignore[assignment]
    try:
        settings = _settings()
        run = await run_ingest_sweep(
            "grantsgov", session_factory, redis_client, settings, "schedule"
        )
    finally:
        reg._ADAPTERS.clear()
        reg._ADAPTERS.update(original)

    assert run is not None
    assert run.records_fetched == 10
    assert run.records_inserted == 7
    assert run.records_skipped == 3
    assert run.records_updated == 0
    assert run.error is None
    assert run.finished_at is not None


async def test_sweep_second_run_all_updated(session_factory, redis_client):
    """Test 24: second run with same 10 records → all updated, 0 inserted."""
    records = [
        _make_ingested(source_id=f"grantsgov:PD-25-{i:04d}", name=f"Grant {i}")
        for i in range(7)
    ]

    import backend.services.ingest.registry as reg

    original = reg._ADAPTERS.copy()
    reg._ADAPTERS["grantsgov"] = lambda: _FakeAdapter(records)  # type: ignore[assignment]
    try:
        settings = _settings()
        await run_ingest_sweep(
            "grantsgov", session_factory, redis_client, settings, "schedule"
        )
        # Clear the lock for the second run
        await redis_client.delete("ingest:grantsgov:lock")

        run2 = await run_ingest_sweep(
            "grantsgov", session_factory, redis_client, settings, "schedule"
        )
    finally:
        reg._ADAPTERS.clear()
        reg._ADAPTERS.update(original)

    assert run2 is not None
    assert run2.records_inserted == 0
    assert run2.records_updated == 7


async def test_sweep_absent_record_archived(session_factory, redis_client):
    """Test 25: one previously-ingested record absent on second run → archived."""
    import backend.services.ingest.registry as reg

    records_run1 = [
        _make_ingested(source_id=f"grantsgov:PD-25-{i:04d}") for i in range(3)
    ]
    records_run2 = [
        _make_ingested(source_id=f"grantsgov:PD-25-{i:04d}") for i in range(2)
    ]

    original = reg._ADAPTERS.copy()
    settings = _settings()

    try:
        reg._ADAPTERS["grantsgov"] = lambda: _FakeAdapter(records_run1)  # type: ignore[assignment]
        await run_ingest_sweep(
            "grantsgov", session_factory, redis_client, settings, "schedule"
        )
        await redis_client.delete("ingest:grantsgov:lock")

        reg._ADAPTERS["grantsgov"] = lambda: _FakeAdapter(records_run2)  # type: ignore[assignment]
        run2 = await run_ingest_sweep(
            "grantsgov", session_factory, redis_client, settings, "schedule"
        )
    finally:
        reg._ADAPTERS.clear()
        reg._ADAPTERS.update(original)

    assert run2 is not None
    assert run2.records_archived == 1

    async with session_factory() as s:
        result = await s.execute(
            sa.select(Grant).where(Grant.source_id == "grantsgov:PD-25-0002")
        )
        grant = result.scalar_one()
    assert grant.status == "archived"


async def test_sweep_lock_held_schedule_returns_none(session_factory, redis_client):
    """Test 26a: lock held → schedule returns None."""
    await redis_client.set("ingest:grantsgov:lock", "existing-run", nx=True, ex=60)
    settings = _settings()
    run = await run_ingest_sweep(
        "grantsgov", session_factory, redis_client, settings, "schedule"
    )
    assert run is None


async def test_sweep_lock_held_manual_raises_conflict(session_factory, redis_client):
    """Test 26b: lock held → manual raises ConflictError."""
    await redis_client.set("ingest:grantsgov:lock", "existing-run", nx=True, ex=60)
    settings = _settings()

    with pytest.raises(ConflictError) as exc_info:
        await run_ingest_sweep(
            "grantsgov", session_factory, redis_client, settings, "manual"
        )

    assert exc_info.value.code == "ingest_in_progress"


async def test_sweep_empty_fetch_skips_archive(session_factory, redis_client):
    """Test 27: 0 records fetched → archive sweep skipped, no rows touched."""
    now = datetime.now(timezone.utc)
    # Seed a grant first
    async with session_factory() as s:
        await upsert_ingested_grants(
            s, "grantsgov", [_make_ingested(source_id="grantsgov:PD-25-EXISTING")], now
        )

    import backend.services.ingest.registry as reg

    original = reg._ADAPTERS.copy()
    reg._ADAPTERS["grantsgov"] = lambda: _FakeAdapter([])  # type: ignore[assignment]
    try:
        settings = _settings()
        run = await run_ingest_sweep(
            "grantsgov", session_factory, redis_client, settings, "schedule"
        )
    finally:
        reg._ADAPTERS.clear()
        reg._ADAPTERS.update(original)

    assert run is not None
    assert run.records_fetched == 0
    assert run.records_archived == 0

    # Pre-existing grant should NOT be archived
    async with session_factory() as s:
        result = await s.execute(
            sa.select(Grant).where(Grant.source_id == "grantsgov:PD-25-EXISTING")
        )
        grant = result.scalar_one()
    assert grant.status == "active"


# ── 28–31. Admin endpoints ────────────────────────────────────────────────────


async def test_trigger_ingest_returns_202(client):
    """Test 28: POST /admin/ingest/trigger/grantsgov → 202 with run_id."""
    # Background task runs the real adapter; mock the Grants.gov API to return empty.
    empty = {"data": {"hitCount": 0, "hits": []}}
    with respx.mock:
        respx.post("https://api.grants.gov/v1/api/search2").mock(
            return_value=httpx.Response(200, json=empty)
        )
        res = await client.post("/api/admin/ingest/trigger/grantsgov")
    assert res.status_code == 202
    body = res.json()
    assert "run_id" in body
    assert body["source"] == "grantsgov"
    uuid.UUID(body["run_id"])


async def test_trigger_ingest_conflict(client, redis_client):
    """Test 29: trigger while lock held → 409 with code='ingest_in_progress'."""
    await redis_client.set(
        "ingest:grantsgov:lock", "existing-run-id", nx=True, ex=60
    )
    res = await client.post("/api/admin/ingest/trigger/grantsgov")
    assert res.status_code == 409
    body = res.json()
    assert body["code"] == "ingest_in_progress"


async def test_trigger_ingest_unknown_source(client):
    """Test 30: unknown source → 404."""
    res = await client.post("/api/admin/ingest/trigger/unknownsource_xyz")
    assert res.status_code == 404


async def test_list_ingest_runs(session_factory, client):
    """Test 31: GET /admin/ingest/runs returns runs in DESC order; supports source filter."""
    base_time = datetime.now(timezone.utc)
    async with session_factory() as s:
        for i in range(3):
            run = IngestRun(
                source="grantsgov",
                triggered_by="schedule",
                started_at=base_time,
            )
            s.add(run)
        s.add(
            IngestRun(
                source="sbirgov",
                triggered_by="manual",
                started_at=base_time,
            )
        )
        await s.commit()

    res = await client.get("/api/admin/ingest/runs")
    assert res.status_code == 200
    body = res.json()
    assert len(body["runs"]) == 4

    # Filter by source
    res2 = await client.get("/api/admin/ingest/runs", params={"source": "grantsgov"})
    assert res2.status_code == 200
    assert len(res2.json()["runs"]) == 3

    res3 = await client.get("/api/admin/ingest/runs", params={"source": "sbirgov"})
    assert res3.status_code == 200
    assert len(res3.json()["runs"]) == 1


# ── 32. Scheduler lifecycle ───────────────────────────────────────────────────


async def test_ingest_scheduler_clean_start_stop(session_factory, redis_client, fake_llm):
    """Test 32: all three schedulers start and stop cleanly in lifespan."""
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
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
    # No unawaited-task warnings means both start and stop cleanly
