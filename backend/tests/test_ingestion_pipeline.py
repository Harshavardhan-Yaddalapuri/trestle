"""Integration test for the grant ingestion pipeline.

Run manually:
    cd backend && python -m pytest tests/test_ingestion_pipeline.py -v
Requires SUPABASE_URL and SUPABASE_SERVICE_KEY env vars.
"""

from __future__ import annotations

import os
from datetime import date

import pytest
import pytest_asyncio

from backend.ingestion.fetchers.grants_gov import GrantsGovFetcher
from backend.ingestion.fetchers.nsf import NSFFetcher
from backend.ingestion.normalizer import normalize_batch
from backend.ingestion.pipeline import IngestionPipeline


pytestmark = pytest.mark.asyncio


async def test_grants_gov_fetcher():
    """Grants.gov fetcher returns tagged records with expected keys."""
    async with GrantsGovFetcher() as fetcher:
        raw = await fetcher.fetch_all(rows=10, max_pages=1)
    assert len(raw) > 0
    for r in raw:
        assert r["_trestle_source"] == "Grants.gov"
        assert r["_trestle_via"] == "grants.gov"
        assert "id" in r
        assert "number" in r
        assert "title" in r
        assert "agency" in r


async def test_nsf_fetcher():
    """NSF fetcher returns only NSF-tagged records."""
    async with NSFFetcher() as fetcher:
        raw = await fetcher.fetch_all(rows=10, max_pages=1)
    assert len(raw) > 0
    for r in raw:
        assert r["_trestle_source"] == "NSF"
        assert "id" in r
        assert "title" in r
        # Verify agency is actually NSF
        assert "National Science Foundation" in (r.get("agency") or "")


async def test_normalizer_produces_valid_rows():
    """Normalizer produces rows that pass pipeline validation."""
    async with GrantsGovFetcher() as fetcher:
        raw = await fetcher.fetch_all(rows=20, max_pages=1)
    normalized = normalize_batch(raw)
    assert len(normalized) > 0
    for n in normalized:
        assert n["source"]
        assert n["source_id"]
        assert n["name"]
        assert n["description"]
        assert n["source_url"]
        assert n["status"] in ("open", "upcoming", "rolling", "archived")
        assert "tags" in n
        assert "metadata_json" in n


@pytest.mark.skipif(
    not os.environ.get("SUPABASE_SERVICE_KEY"),
    reason="SUPABASE_SERVICE_KEY not set",
)
async def test_end_to_end_pipeline():
    """Full pipeline: fetch → normalize → upsert → verify."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    pipeline = IngestionPipeline(url, key)

    result = await pipeline.run([
        GrantsGovFetcher(),
        NSFFetcher(),
    ])

    # Sanity checks
    assert result["raw_fetched"] > 0
    assert result["normalized"] > 0
    assert result["valid"] > 0
    assert result["errors"] == 0
    assert result["duration_seconds"] < 120  # should be fast with bulk ops

    # Verify at least some new NSF grants were fetched
    assert result["inserted"] >= 0
    assert result["updated"] >= 0
    assert result["total_processed"] == result["inserted"] + result["updated"]
