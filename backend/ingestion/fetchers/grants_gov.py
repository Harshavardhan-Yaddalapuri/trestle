"""Grants.gov fetcher — calls the public Search2 + fetchOpportunity APIs.

Docs: https://www.grants.gov/api/api-guide
Endpoints:
  POST https://api.grants.gov/v1/api/search2     — search opportunities
  GET  https://api.grants.gov/v1/api/fetchOpportunity?oppId=<id> — detail

No auth key required.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

_BASE = "https://api.grants.gov/v1/api"


def _parse_date(s: str | None) -> date | None:
    if not s or not str(s).strip():
        return None
    try:
        return datetime.strptime(s.strip(), "%m/%d/%Y").date()
    except ValueError:
        try:
            return datetime.strptime(s.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None


def _money(s: str | None) -> int | None:
    """Parse a money string like '$1,500,000' → 1500000 (USD cents → dollars)."""
    if not s:
        return None
    s = s.replace("$", "").replace(",", "").strip()
    try:
        return int(s)
    except ValueError:
        return None


class GrantsGovFetcher:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(timeout=60)

    async def search(
        self,
        *,
        keyword: str | None = None,
        agency: str | None = None,
        opp_statuses: str = "posted",
        rows: int = 25,
        start_record: int = 0,
    ) -> dict[str, Any]:
        """Run Search2 and return raw API response dict."""
        body: dict[str, Any] = {
            "startRecordNum": start_record,
            "oppNum": None,
            "cfdaNumbers": None,
            "fundingCategories": None,
            "fundingInstruments": None,
            "dateRange": None,
            "oppStatuses": opp_statuses,
            "sortBy": "openDate|desc",
            "keywords": keyword,
            "fields": "all",
            "eligibilities": None,
            "agencyNumbers": None,
            "estimateFunding": None,
            "oppFilters": None,
            "rows": rows,
        }
        if agency:
            body["agencies"] = agency
        r = await self.client.post(
            f"{_BASE}/search2", json=body, headers={"Content-Type": "application/json"}
        )
        r.raise_for_status()
        return r.json()

    async def fetch_detail(self, opp_id: str) -> dict[str, Any] | None:
        """Call fetchOpportunity (requires auth token for some oppIds)."""
        try:
            r = await self.client.get(
                f"{_BASE}/fetchOpportunity", params={"oppId": opp_id}
            )
            if r.status_code == 403:
                logger.warning("fetchOpportunity forbidden", opp_id=opp_id)
                return None
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("fetchOpportunity failed", opp_id=opp_id, status=exc.response.status_code)
            return None

    async def fetch_opportunities(
        self,
        *,
        keyword: str | None = None,  # broader default
        rows: int = 50,
        max_pages: int = 4,
    ) -> list[dict[str, Any]]:
        """Paginate Search2 and flatten oppHits into a list."""
        hits: list[dict[str, Any]] = []
        for page in range(max_pages):
            offset = page * rows
            data = await self.search(
                keyword=keyword, rows=rows, start_record=offset
            )
            wrapper = data.get("data", {})
            opp_hits = wrapper.get("oppHits", [])
            if not opp_hits:
                break
            for h in opp_hits:
                h["_trestle_source"] = "Grants.gov"
                h["_trestle_via"] = "grants.gov"
            hits.extend(opp_hits)
            if len(opp_hits) < rows:
                break
        return hits

    # Alias used by the pipeline orchestrator
    fetch_all = fetch_opportunities

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.client.aclose()
