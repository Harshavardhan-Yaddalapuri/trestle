"""Tests for the SBIR.gov source adapter (Step 22).

Layout:
  1    SbirGovAdapter satisfies SourceAdapter Protocol
  2    fetch_all: 3 topics with varied phases → 3 IngestedGrant records
  3    Phase I topic includes max_funding_raised_usd in eligibility
  4    Phase II topic does NOT include max_funding_raised_usd
  5    STTR program: eligibility includes _requires_research_partner=True
  6    Pagination: 2 pages (100 + 50) → 250 total
  7    closeDate ISO and MM/DD/YYYY both parsed
  8    4xx on topics page → UpstreamError raised
  9    Branch-to-industry mapping
  10   Direct-to-Phase-II stage mapping
  11   Missing topicNumber → record skipped, others yielded
  12   Malformed JSON topic in list → skipped, others yielded
  13   Registry: get_enabled_sources includes sbirgov when SBIRGOV_ENABLED
  14   Orchestration: run_ingest_sweep for sbirgov succeeds, ingest_run recorded
  15   Scheduler: get_enabled_sources returns sbirgov + grantsgov when both enabled
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import httpx
import pytest
import respx
import sqlalchemy as sa

from backend.core.config import Settings
from backend.db.models.grant import Grant
from backend.db.models.ingest_run import IngestRun
from backend.services.ingest.adapters.sbirgov import (
    SbirGovAdapter,
    _branch_to_industry,
    _extract_topics,
    _phase_to_stage,
)
from backend.services.ingest.base import IngestedGrant, SourceAdapter
from backend.services.ingest.orchestration import run_ingest_sweep
from backend.services.ingest.registry import get_adapter, get_enabled_sources


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


def _topic(
    *,
    topic_number: str = "AF251-001",
    title: str = "Autonomous Cyber Defense",
    branch: str = "Air Force",
    program: str = "SBIR",
    phase: str = "Phase I",
    status: str = "Open",
    close_date: str = "12/31/2026",
    award_ceiling: int = 250_000,
    award_floor: int = 50_000,
    description: str = "A SBIR topic.",
    objective: str = "",
    topic_url: str = "",
    solicitation_id: str = "SBIR-25-1",
) -> dict:
    return {
        "topicNumber": topic_number,
        "topicTitle": title,
        "solicitationId": solicitation_id,
        "solicitationTitle": "DoD SBIR 25.1",
        "branch": branch,
        "program": program,
        "phase": phase,
        "topicStatus": status,
        "openDate": "01/01/2026",
        "closeDate": close_date,
        "topicDescription": description,
        "topicObjective": objective,
        "topicUrl": topic_url,
        "awardCeiling": award_ceiling,
        "awardFloor": award_floor,
    }


def _topics_resp(topics: list[dict], total: int | None = None) -> dict:
    resp: dict[str, Any] = {"topics": topics}
    if total is not None:
        resp["totalCount"] = total
    return resp


SBIR_BASE = "https://api.www.sbir.gov/public/api"


# ── 1. Protocol ──────────────────────────────────────────────────────────────


def test_sbir_adapter_satisfies_protocol():
    """Test 1: SbirGovAdapter structurally satisfies SourceAdapter Protocol."""
    adapter = SbirGovAdapter()
    assert isinstance(adapter, SourceAdapter)
    assert SbirGovAdapter.source_name == "sbirgov"


# ── 2. fetch_all: 3 varied topics ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sbir_fetch_3_topics():
    """Test 2: adapter yields 3 IngestedGrant records with correct shape."""
    settings = _settings()
    adapter = SbirGovAdapter()

    topics = [
        _topic(topic_number="AF251-001", phase="Phase I", branch="Air Force"),
        _topic(topic_number="N251-002", phase="Phase II", branch="Navy", program="SBIR"),
        _topic(topic_number="HHS-001", phase="Phase I", branch="HHS", program="STTR"),
    ]
    body = _topics_resp(topics)

    with respx.mock:
        respx.get(f"{SBIR_BASE}/topics").mock(
            return_value=httpx.Response(200, json=body)
        )
        async with httpx.AsyncClient() as client:
            records = [r async for r in adapter.fetch_all(client, settings, since=None)]

    assert len(records) == 3
    for r in records:
        assert r.source == "sbirgov"
        assert r.source_id.startswith("sbirgov:")
        assert r.type == "grant"
        assert r.location == ["US"]
        assert r.provider_type == "government"
        assert r.eligibility.get("requires_incorporation") is True
        assert r.eligibility.get("_program") in ("SBIR", "STTR")


# ── 3. Phase I → max_funding_raised_usd ──────────────────────────────────────


@pytest.mark.asyncio
async def test_phase_1_has_funding_raised_limit():
    """Test 3: Phase I includes max_funding_raised_usd=2000000 in eligibility."""
    settings = _settings()
    adapter = SbirGovAdapter()

    body = _topics_resp([_topic(phase="Phase I")])
    with respx.mock:
        respx.get(f"{SBIR_BASE}/topics").mock(return_value=httpx.Response(200, json=body))
        async with httpx.AsyncClient() as client:
            records = [r async for r in adapter.fetch_all(client, settings, since=None)]

    assert len(records) == 1
    assert records[0].eligibility.get("max_funding_raised_usd") == 2_000_000


# ── 4. Phase II → no funding raised limit ────────────────────────────────────


@pytest.mark.asyncio
async def test_phase_2_no_funding_raised_limit():
    """Test 4: Phase II does NOT include max_funding_raised_usd."""
    settings = _settings()
    adapter = SbirGovAdapter()

    body = _topics_resp([_topic(phase="Phase II")])
    with respx.mock:
        respx.get(f"{SBIR_BASE}/topics").mock(return_value=httpx.Response(200, json=body))
        async with httpx.AsyncClient() as client:
            records = [r async for r in adapter.fetch_all(client, settings, since=None)]

    assert len(records) == 1
    assert "max_funding_raised_usd" not in records[0].eligibility


# ── 5. STTR → _requires_research_partner ─────────────────────────────────────


@pytest.mark.asyncio
async def test_sttr_requires_research_partner():
    """Test 5: STTR program includes _requires_research_partner=True."""
    settings = _settings()
    adapter = SbirGovAdapter()

    body = _topics_resp([_topic(program="STTR", phase="Phase I")])
    with respx.mock:
        respx.get(f"{SBIR_BASE}/topics").mock(return_value=httpx.Response(200, json=body))
        async with httpx.AsyncClient() as client:
            records = [r async for r in adapter.fetch_all(client, settings, since=None)]

    assert len(records) == 1
    assert records[0].eligibility.get("_requires_research_partner") is True


# ── 6. Pagination ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sbir_pagination():
    """Test 6: 2 pages (100 + 50) → 150 total records."""
    settings = _settings(SBIRGOV_PAGE_SIZE=100)
    adapter = SbirGovAdapter()

    page1 = [_topic(topic_number=f"AF251-{i:03d}") for i in range(100)]
    page2 = [_topic(topic_number=f"AF251-{i:03d}") for i in range(100, 150)]

    call_count = 0

    def side_effect(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(200, json=_topics_resp(page1, total=150))
        return httpx.Response(200, json=_topics_resp(page2, total=150))

    with respx.mock:
        respx.get(f"{SBIR_BASE}/topics").mock(side_effect=side_effect)
        async with httpx.AsyncClient() as client:
            records = [r async for r in adapter.fetch_all(client, settings, since=None)]

    assert len(records) == 150
    assert call_count == 2


# ── 7. Date parsing ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sbir_date_parsing():
    """Test 7: ISO date and MM/DD/YYYY both parsed correctly."""
    settings = _settings()
    adapter = SbirGovAdapter()

    topics = [
        _topic(topic_number="ISO-001", close_date="2026-12-31"),
        _topic(topic_number="US-001", close_date="12/31/2026"),
    ]
    body = _topics_resp(topics)

    with respx.mock:
        respx.get(f"{SBIR_BASE}/topics").mock(return_value=httpx.Response(200, json=body))
        async with httpx.AsyncClient() as client:
            records = [r async for r in adapter.fetch_all(client, settings, since=None)]

    assert len(records) == 2
    for r in records:
        assert r.deadline == date(2026, 12, 31)


# ── 8. 4xx error → UpstreamError ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sbir_500_raises_upstream_error():
    """Test 8: 500 on topics page → UpstreamError (wraps the entire sweep)."""
    from backend.core.errors import UpstreamError

    settings = _settings()
    adapter = SbirGovAdapter()

    with respx.mock:
        respx.get(f"{SBIR_BASE}/topics").mock(
            return_value=httpx.Response(500, json={"error": "internal server error"})
        )
        with pytest.raises(UpstreamError):
            async with httpx.AsyncClient() as client:
                _ = [r async for r in adapter.fetch_all(client, settings, since=None)]


# ── 9. Branch-to-industry mapping ────────────────────────────────────────────


def test_branch_industry_air_force():
    """Test 9a: Air Force → ["defense", "dual_use"]."""
    assert _branch_to_industry("Air Force") == ["defense", "dual_use"]


def test_branch_industry_hhs():
    """Test 9b: HHS → ["healthcare", "biotech"]."""
    assert _branch_to_industry("HHS") == ["healthcare", "biotech"]


def test_branch_industry_doe():
    """Test 9c: Department of Energy → ["energy", "cleantech"]."""
    assert _branch_to_industry("Department of Energy") == ["energy", "cleantech"]


def test_branch_industry_unknown():
    """Test 9d: unknown branch → []."""
    assert _branch_to_industry("Unknown Agency XYZ") == []


def test_branch_industry_nasa():
    """Test 9e: NASA → ["aerospace"]."""
    assert _branch_to_industry("NASA") == ["aerospace"]


# ── 10. Direct-to-Phase-II stage ─────────────────────────────────────────────


def test_phase_direct_to_phase_ii_stage():
    """Test 10: Direct to Phase II → ["seed", "series_a"]."""
    assert _phase_to_stage("Direct to Phase II") == ["seed", "series_a"]


def test_phase_i_stage():
    assert _phase_to_stage("Phase I") == ["idea", "pre_seed", "seed"]


def test_phase_ii_stage():
    assert _phase_to_stage("Phase II") == ["pre_seed", "seed", "series_a"]


def test_phase_unknown_stage():
    assert _phase_to_stage("Unknown Phase") == []


# ── 11. Missing topicNumber → record skipped ─────────────────────────────────


@pytest.mark.asyncio
async def test_sbir_missing_topic_number_skipped():
    """Test 11: topic with missing topicNumber is skipped; others still yielded."""
    settings = _settings()
    adapter = SbirGovAdapter()

    topics = [
        _topic(topic_number="AF251-001"),
        {**_topic(topic_number="MISSING"), "topicNumber": ""},  # empty → skipped
        _topic(topic_number="AF251-003"),
    ]
    body = _topics_resp(topics)

    with respx.mock:
        respx.get(f"{SBIR_BASE}/topics").mock(return_value=httpx.Response(200, json=body))
        async with httpx.AsyncClient() as client:
            records = [r async for r in adapter.fetch_all(client, settings, since=None)]

    assert len(records) == 2
    source_ids = {r.source_id for r in records}
    assert "sbirgov:AF251-001" in source_ids
    assert "sbirgov:AF251-003" in source_ids


# ── 12. _extract_topics handles multiple envelope shapes ─────────────────────


def test_extract_topics_list_envelope():
    """Test 12a: bare list response handled."""
    topics_list = [_topic(), _topic(topic_number="X-002")]
    result, total = _extract_topics(topics_list)
    assert len(result) == 2
    assert total is None


def test_extract_topics_topics_key():
    """Test 12b: {"topics": [...]} envelope handled."""
    body = {"topics": [_topic()], "totalCount": 1}
    result, total = _extract_topics(body)
    assert len(result) == 1
    assert total == 1


def test_extract_topics_unknown_shape():
    """Test 12c: unknown dict shape → empty list."""
    body = {"unknown_key": "value"}
    result, total = _extract_topics(body)
    assert result == []
    assert total is None


# ── 13. Registry includes sbirgov ─────────────────────────────────────────────


def test_registry_includes_sbirgov():
    """Test 13: get_adapter('sbirgov') returns SbirGovAdapter."""
    cls = get_adapter("sbirgov")
    assert cls is SbirGovAdapter


def test_registry_sbirgov_in_enabled_sources():
    """Test 13b: get_enabled_sources includes 'sbirgov' when SBIRGOV_ENABLED=True."""
    settings = _settings(SBIRGOV_ENABLED=True, GRANTSGOV_ENABLED=True)
    sources = get_enabled_sources(settings)
    assert "sbirgov" in sources


def test_registry_sbirgov_excluded_when_disabled():
    """Test 13c: get_enabled_sources excludes 'sbirgov' when SBIRGOV_ENABLED=False."""
    settings = _settings(SBIRGOV_ENABLED=False, GRANTSGOV_ENABLED=True)
    sources = get_enabled_sources(settings)
    assert "sbirgov" not in sources


# ── 14. Orchestration: run_ingest_sweep for sbirgov ──────────────────────────


class _FakeSbirAdapter:
    source_name = "sbirgov"

    def __init__(self, records: list[IngestedGrant]):
        self._records = records

    async def fetch_all(self, client, settings, since):
        for r in self._records:
            yield r


def _sbir_ingested(**overrides) -> IngestedGrant:
    defaults = dict(
        source="sbirgov",
        source_id="sbirgov:AF251-001",
        name="Autonomous Cyber Defense",
        type="grant",
        description="A test SBIR topic.",
        url="https://www.sbir.gov/sbirsearch/detail/AF251-001",
        provider_name="Air Force SBIR",
        provider_type="government",
        location=["US"],
        eligibility={
            "required_location": ["US"],
            "requires_incorporation": True,
            "_program": "SBIR",
            "_phase": "Phase I",
            "_branch": "Air Force",
            "_topic_number": "AF251-001",
        },
        amount_max_usd_cents=25_000_000,
        deadline=date(2026, 12, 31),
    )
    defaults.update(overrides)
    return IngestedGrant(**defaults)


async def test_sbirgov_sweep_inserts_run(session_factory, redis_client):
    """Test 14: run_ingest_sweep for sbirgov creates ingest_run row with correct source."""
    import backend.services.ingest.registry as reg

    records = [
        _sbir_ingested(source_id=f"sbirgov:AF251-{i:03d}", name=f"SBIR Topic {i}")
        for i in range(5)
    ]

    original = reg._ADAPTERS.copy()
    reg._ADAPTERS["sbirgov"] = lambda: _FakeSbirAdapter(records)  # type: ignore[assignment]
    try:
        settings = _settings()
        run = await run_ingest_sweep(
            "sbirgov", session_factory, redis_client, settings, "schedule"
        )
    finally:
        reg._ADAPTERS.clear()
        reg._ADAPTERS.update(original)

    assert run is not None
    assert run.source == "sbirgov"
    assert run.records_fetched == 5
    assert run.records_inserted == 5
    assert run.error is None

    async with session_factory() as s:
        result = await s.execute(
            sa.select(Grant).where(Grant.source == "sbirgov")
        )
        grants = result.scalars().all()
    assert len(grants) == 5


# ── 15. Scheduler: both sources returned ─────────────────────────────────────


def test_scheduler_both_sources_enabled():
    """Test 15: get_enabled_sources returns both when both enabled."""
    settings = _settings(GRANTSGOV_ENABLED=True, SBIRGOV_ENABLED=True)
    sources = get_enabled_sources(settings)
    assert sources == ["grantsgov", "sbirgov"]
