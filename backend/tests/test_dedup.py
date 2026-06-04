"""Tests for cross-source deduplication (Step 22).

Layout:
  1    run_dedup_pass with no overlapping records → 0 duplicates
  2    topic_number match: grantsgov row marked as duplicate of sbirgov row
  3    Dedup idempotency: running pass twice doesn't change existing is_duplicate_of
  4    URL-based dedup fallback
  5    grant with dedup_checked_at set is skipped on subsequent pass
  6    is_duplicate_of excluded from POST /grants/match results
  7    GET /grants excludes duplicates by default
  8    GET /grants?include_duplicates=true returns them
  9    GET /grants/{id} returns duplicate record (no filter on detail)
  10   ingest_runs.duplicates_found populated after sweep
  11   Two-source sweep: sbirgov ingest links K duplicates to grantsgov records
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import sqlalchemy as sa
import pytest
from httpx import ASGITransport, AsyncClient

from backend.core.config import Settings
from backend.db.models.grant import Grant
from backend.db.models.ingest_run import IngestRun
from backend.services.ingest.base import IngestedGrant
from backend.services.ingest.dedup import DedupResult, _normalize_url, run_dedup_pass
from backend.services.ingest.orchestration import run_ingest_sweep
from backend.services.ingest.upsert import upsert_ingested_grants


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


def _make_sbirgov(
    *,
    topic_number: str = "AF251-001",
    url: str | None = None,
    status: str = "active",
) -> IngestedGrant:
    return IngestedGrant(
        source="sbirgov",
        source_id=f"sbirgov:{topic_number}",
        name=f"SBIR Topic {topic_number}",
        type="grant",
        description="A SBIR topic.",
        url=url or f"https://www.sbir.gov/sbirsearch/detail/{topic_number}",
        provider_name="Air Force SBIR",
        provider_type="government",
        location=["US"],
        eligibility={
            "required_location": ["US"],
            "requires_incorporation": True,
            "_program": "SBIR",
            "_phase": "Phase I",
            "_branch": "Air Force",
            "_topic_number": topic_number,
        },
        amount_max_usd_cents=25_000_000,
        deadline=date(2026, 12, 31),
        status=status,
    )


def _make_grantsgov(
    *,
    opp_number: str = "GG-25-001",
    url: str | None = None,
    status: str = "active",
) -> IngestedGrant:
    return IngestedGrant(
        source="grantsgov",
        source_id=f"grantsgov:{opp_number}",
        name=f"Grants.gov Opp {opp_number}",
        type="grant",
        description="A Grants.gov opportunity.",
        url=url or f"https://www.grants.gov/search-results-detail/{opp_number}",
        provider_name="Air Force",
        provider_type="government",
        location=["US"],
        eligibility={"required_location": ["US"]},
        amount_max_usd_cents=25_000_000,
        deadline=date(2026, 12, 31),
        source_payload={"number": opp_number, "id": "99999"},
        status=status,
    )


async def _seed(session_factory, records: list[IngestedGrant]) -> None:
    now = datetime.now(timezone.utc)
    for record in records:
        async with session_factory() as s:
            await upsert_ingested_grants(s, record.source, [record], now)


# ── 1. No overlapping records → 0 duplicates ─────────────────────────────────


async def test_dedup_no_overlap(session_factory):
    """Test 1: sbirgov and grantsgov with different numbers → 0 duplicates."""
    await _seed(session_factory, [
        _make_sbirgov(topic_number="AF251-001"),
        _make_grantsgov(opp_number="GG-99-999"),  # different number
    ])

    source_ids = {"sbirgov:AF251-001"}
    async with session_factory() as s:
        result = await run_dedup_pass(s, "sbirgov", source_ids)

    assert result.duplicates_found == 0
    assert result.grants_checked == 1


# ── 2. topic_number match → grantsgov marked as duplicate of sbirgov ─────────


async def test_dedup_topic_number_match(session_factory):
    """Test 2: sbirgov topic AF251-001 matches grantsgov opp AF251-001."""
    topic_number = "AF251-001"
    await _seed(session_factory, [
        _make_sbirgov(topic_number=topic_number),
        _make_grantsgov(opp_number=topic_number),  # same number
    ])

    # Get IDs
    async with session_factory() as s:
        sbir_row = (await s.execute(
            sa.select(Grant).where(Grant.source_id == f"sbirgov:{topic_number}")
        )).scalar_one()
        gg_row = (await s.execute(
            sa.select(Grant).where(Grant.source_id == f"grantsgov:{topic_number}")
        )).scalar_one()

    source_ids = {f"sbirgov:{topic_number}"}
    async with session_factory() as s:
        result = await run_dedup_pass(s, "sbirgov", source_ids)

    assert result.duplicates_found == 1
    assert result.sbirgov_canonical_wins == 1

    # grantsgov row should be marked as duplicate of sbirgov row
    async with session_factory() as s:
        gg_updated = (await s.execute(
            sa.select(Grant).where(Grant.id == gg_row.id)
        )).scalar_one()

    assert gg_updated.is_duplicate_of == sbir_row.id
    assert gg_updated.dedup_match_kind == "topic_number"
    assert gg_updated.dedup_checked_at is not None


# ── 3. Idempotency ───────────────────────────────────────────────────────────


async def test_dedup_idempotent(session_factory):
    """Test 3: running the dedup pass twice doesn't change is_duplicate_of."""
    topic_number = "AF251-002"
    await _seed(session_factory, [
        _make_sbirgov(topic_number=topic_number),
        _make_grantsgov(opp_number=topic_number),
    ])

    source_ids = {f"sbirgov:{topic_number}"}

    # First pass
    async with session_factory() as s:
        result1 = await run_dedup_pass(s, "sbirgov", source_ids)
    assert result1.duplicates_found == 1

    # Second pass — sbirgov record has dedup_checked_at set, should be skipped
    async with session_factory() as s:
        result2 = await run_dedup_pass(s, "sbirgov", source_ids)

    assert result2.grants_checked == 0  # skipped because dedup_checked_at is set
    assert result2.duplicates_found == 0

    # is_duplicate_of on grantsgov row unchanged
    async with session_factory() as s:
        sbir_row = (await s.execute(
            sa.select(Grant).where(Grant.source_id == f"sbirgov:{topic_number}")
        )).scalar_one()
        gg_row = (await s.execute(
            sa.select(Grant).where(Grant.source_id == f"grantsgov:{topic_number}")
        )).scalar_one()

    assert gg_row.is_duplicate_of == sbir_row.id  # unchanged


# ── 4. URL-based dedup fallback ───────────────────────────────────────────────


async def test_dedup_url_fallback(session_factory):
    """Test 4: URL match when no topic_number match → linked, dedup_match_kind='url'."""
    shared_url = "https://example.gov/opportunity/123"
    await _seed(session_factory, [
        _make_sbirgov(topic_number="XYZ-001", url=shared_url),
        _make_grantsgov(opp_number="NONTOPIC-001", url=shared_url),
    ])

    source_ids = {"sbirgov:XYZ-001"}
    async with session_factory() as s:
        result = await run_dedup_pass(s, "sbirgov", source_ids)

    assert result.duplicates_found == 1

    async with session_factory() as s:
        gg_row = (await s.execute(
            sa.select(Grant).where(Grant.source_id == "grantsgov:NONTOPIC-001")
        )).scalar_one()

    assert gg_row.is_duplicate_of is not None
    assert gg_row.dedup_match_kind == "url"


# ── 5. dedup_checked_at set → skipped on next pass ───────────────────────────


async def test_dedup_already_checked_skipped(session_factory):
    """Test 5: grant with dedup_checked_at already set is skipped."""
    now = datetime.now(timezone.utc)
    await _seed(session_factory, [_make_sbirgov(topic_number="CHECKED-001")])

    # Manually set dedup_checked_at
    async with session_factory() as s:
        await s.execute(
            sa.update(Grant)
            .where(Grant.source_id == "sbirgov:CHECKED-001")
            .values(dedup_checked_at=now)
        )
        await s.commit()

    source_ids = {"sbirgov:CHECKED-001"}
    async with session_factory() as s:
        result = await run_dedup_pass(s, "sbirgov", source_ids)

    assert result.grants_checked == 0  # skipped


# ── 6. Matching engine excludes duplicates ────────────────────────────────────


async def test_match_excludes_duplicates(session_factory, redis_client, client):
    """Test 6: POST /grants/match excludes grants with is_duplicate_of set."""
    sbir = _make_sbirgov(topic_number="MATCH-001")
    gg = _make_grantsgov(opp_number="MATCH-001")

    await _seed(session_factory, [sbir, gg])

    async with session_factory() as s:
        sbir_row = (await s.execute(
            sa.select(Grant).where(Grant.source_id == "sbirgov:MATCH-001")
        )).scalar_one()
        gg_row = (await s.execute(
            sa.select(Grant).where(Grant.source_id == "grantsgov:MATCH-001")
        )).scalar_one()
        await s.execute(
            sa.update(Grant)
            .where(Grant.id == gg_row.id)
            .values(is_duplicate_of=sbir_row.id, dedup_match_kind="topic_number")
        )
        await s.commit()

    # include_ineligible=true so grants appear even with no profile; min_score=0
    resp = await client.post(
        "/api/grants/match",
        json={"include_ineligible": True, "min_score": 0.0},
    )
    assert resp.status_code == 200
    grant_ids = {r["grant"]["id"] for r in resp.json()["results"]}

    # sbirgov (canonical) present; grantsgov (duplicate) excluded by query filter
    assert str(sbir_row.id) in grant_ids
    assert str(gg_row.id) not in grant_ids


# ── 7. GET /grants excludes duplicates by default ─────────────────────────────


async def test_list_grants_excludes_duplicates_by_default(session_factory, client):
    """Test 7: GET /grants hides is_duplicate_of IS NOT NULL rows."""
    now = datetime.now(timezone.utc)
    sbir = _make_sbirgov(topic_number="LIST-001")
    gg = _make_grantsgov(opp_number="LIST-001")
    await _seed(session_factory, [sbir, gg])

    async with session_factory() as s:
        sbir_row = (await s.execute(
            sa.select(Grant).where(Grant.source_id == "sbirgov:LIST-001")
        )).scalar_one()
        await s.execute(
            sa.update(Grant)
            .where(Grant.source_id == "grantsgov:LIST-001")
            .values(is_duplicate_of=sbir_row.id, dedup_match_kind="topic_number")
        )
        await s.commit()

    resp = await client.get("/api/grants")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]

    async with session_factory() as s:
        gg_row = (await s.execute(
            sa.select(Grant).where(Grant.source_id == "grantsgov:LIST-001")
        )).scalar_one()

    assert str(gg_row.id) not in ids


# ── 8. GET /grants?include_duplicates=true returns them ──────────────────────


async def test_list_grants_include_duplicates_param(session_factory, client):
    """Test 8: GET /grants?include_duplicates=true returns duplicate rows."""
    sbir = _make_sbirgov(topic_number="INC-001")
    gg = _make_grantsgov(opp_number="INC-001")
    await _seed(session_factory, [sbir, gg])

    async with session_factory() as s:
        sbir_row = (await s.execute(
            sa.select(Grant).where(Grant.source_id == "sbirgov:INC-001")
        )).scalar_one()
        gg_row = (await s.execute(
            sa.select(Grant).where(Grant.source_id == "grantsgov:INC-001")
        )).scalar_one()
        await s.execute(
            sa.update(Grant)
            .where(Grant.id == gg_row.id)
            .values(is_duplicate_of=sbir_row.id, dedup_match_kind="topic_number")
        )
        await s.commit()

    # Without flag: only canonical
    resp_default = await client.get("/api/grants")
    ids_default = {item["id"] for item in resp_default.json()["items"]}

    # With flag: both
    resp_all = await client.get("/api/grants", params={"include_duplicates": "true"})
    ids_all = {item["id"] for item in resp_all.json()["items"]}

    assert str(gg_row.id) not in ids_default
    assert str(gg_row.id) in ids_all
    assert str(sbir_row.id) in ids_all


# ── 9. GET /grants/{id} returns duplicate (no filter) ────────────────────────


async def test_get_grant_detail_returns_duplicate(session_factory, client):
    """Test 9: GET /grants/{id} returns duplicate record regardless of is_duplicate_of."""
    sbir = _make_sbirgov(topic_number="DETAIL-001")
    gg = _make_grantsgov(opp_number="DETAIL-001")
    await _seed(session_factory, [sbir, gg])

    async with session_factory() as s:
        sbir_row = (await s.execute(
            sa.select(Grant).where(Grant.source_id == "sbirgov:DETAIL-001")
        )).scalar_one()
        gg_row = (await s.execute(
            sa.select(Grant).where(Grant.source_id == "grantsgov:DETAIL-001")
        )).scalar_one()
        await s.execute(
            sa.update(Grant)
            .where(Grant.id == gg_row.id)
            .values(is_duplicate_of=sbir_row.id, dedup_match_kind="topic_number")
        )
        await s.commit()

    resp = await client.get(f"/api/grants/{gg_row.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(gg_row.id)


# ── 10. ingest_runs.duplicates_found populated ────────────────────────────────


async def test_ingest_run_duplicates_found_counter(session_factory, redis_client):
    """Test 10: duplicates_found counter on ingest_run reflects dedup results."""
    topic_number = "COUNTER-001"

    # Pre-seed a grantsgov record
    now = datetime.now(timezone.utc)
    async with session_factory() as s:
        await upsert_ingested_grants(
            s, "grantsgov", [_make_grantsgov(opp_number=topic_number)], now
        )

    import backend.services.ingest.registry as reg

    class _FakeSbirAdapter:
        source_name = "sbirgov"

        async def fetch_all(self, client, settings, since):
            yield _make_sbirgov(topic_number=topic_number)

    original = reg._ADAPTERS.copy()
    reg._ADAPTERS["sbirgov"] = lambda: _FakeSbirAdapter()  # type: ignore[assignment]
    try:
        settings = _settings()
        run = await run_ingest_sweep(
            "sbirgov", session_factory, redis_client, settings, "schedule"
        )
    finally:
        reg._ADAPTERS.clear()
        reg._ADAPTERS.update(original)

    assert run is not None
    assert run.duplicates_found == 1


# ── 11. Two-source: sbirgov links duplicates from grantsgov ──────────────────


async def test_two_source_dedup(session_factory, redis_client):
    """Test 11: sbirgov ingest finds duplicates among previously-ingested grantsgov."""
    shared_numbers = ["TOPIC-A", "TOPIC-B", "TOPIC-C"]
    now = datetime.now(timezone.utc)

    # Seed grantsgov records first
    async with session_factory() as s:
        await upsert_ingested_grants(
            s,
            "grantsgov",
            [_make_grantsgov(opp_number=n) for n in shared_numbers],
            now,
        )

    # Now run sbirgov sweep with matching topics
    import backend.services.ingest.registry as reg

    class _FakeSbirAdapter2:
        source_name = "sbirgov"

        async def fetch_all(self, client, settings, since):
            for n in shared_numbers:
                yield _make_sbirgov(topic_number=n)
            # One extra that has no grantsgov match
            yield _make_sbirgov(topic_number="UNIQUE-SBIR")

    original = reg._ADAPTERS.copy()
    reg._ADAPTERS["sbirgov"] = lambda: _FakeSbirAdapter2()  # type: ignore[assignment]
    try:
        settings = _settings()
        run = await run_ingest_sweep(
            "sbirgov", session_factory, redis_client, settings, "schedule"
        )
    finally:
        reg._ADAPTERS.clear()
        reg._ADAPTERS.update(original)

    assert run is not None
    assert run.records_inserted == 4  # 3 + unique
    assert run.duplicates_found == 3

    # Verify grantsgov rows are marked as duplicates
    async with session_factory() as s:
        dup_count = (await s.execute(
            sa.select(sa.func.count())
            .select_from(Grant)
            .where(Grant.source == "grantsgov", Grant.is_duplicate_of.isnot(None))
        )).scalar()

    assert dup_count == 3


# ── URL normalization helper tests ────────────────────────────────────────────


def test_normalize_url_strips_trailing_slash():
    assert _normalize_url("https://example.com/path/") == "https://example.com/path"


def test_normalize_url_lowercases_host():
    assert _normalize_url("HTTPS://Example.COM/path") == "https://example.com/path"


def test_normalize_url_drops_tracking_params():
    url = "https://example.com/path?utm_source=google&real=1"
    result = _normalize_url(url)
    assert "utm_source" not in result
    assert "real=1" in result
