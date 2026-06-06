"""SBIR.gov fetcher.

SBIR.gov public API (api.www.sbir.gov) is heavily rate-limited / often 403.
Strategies:
1. Grants.gov proxy — search SBIR solicitations via Grants.gov (most reliable).
2. SBIR.gov public API — lightweight attempt; gracefully degrades on 403.
3. Static curated list — hard-coded high-value solicitations if both fail.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

_GRANTS_GOV_BASE = "https://api.grants.gov/v1/api"
_SBIR_API_BASE = "https://api.www.sbir.gov/public/api"


def _parse_date(s: str | None) -> date | None:
    if not s or not str(s).strip():
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


class SBIRGovFetcher:
    """Fetch SBIR/STTR funding opportunities."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(timeout=60)

    async def _from_grants_gov(self, rows: int = 50, max_pages: int = 4) -> list[dict[str, Any]]:
        """Query Grants.gov for SBIR-related postings."""
        hits: list[dict[str, Any]] = []
        for page in range(max_pages):
            offset = page * rows
            body = {
                "startRecordNum": offset,
                "oppNum": None,
                "cfdaNumbers": None,
                "fundingCategories": None,
                "fundingInstruments": None,
                "dateRange": None,
                "oppStatuses": "posted|forecasted",
                "sortBy": "openDate|desc",
                "keywords": "SBIR",
                "fields": "all",
                "eligibilities": None,
                "agencyNumbers": None,
                "estimateFunding": None,
                "oppFilters": None,
                "rows": rows,
            }
            try:
                r = await self.client.post(
                    f"{_GRANTS_GOV_BASE}/search2",
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
                r.raise_for_status()
                data = r.json()
                opp_hits = data.get("data", {}).get("oppHits", [])
                if not opp_hits:
                    break
                hits.extend(opp_hits)
                if len(opp_hits) < rows:
                    break
            except httpx.HTTPError as exc:
                logger.warning("sbir_grants_gov_error", page=page, error=str(exc))
                break
        for h in hits:
            h["_trestle_source"] = "SBIR.gov"
            h["_trestle_via"] = "grants.gov"
        return hits

    async def _from_sbir_api(self, agency: str | None = None) -> list[dict[str, Any]]:
        """Attempt SBIR.gov public API."""
        params: dict[str, str] = {}
        if agency:
            params["agency"] = agency
        try:
            r = await self.client.get(
                f"{_SBIR_API_BASE}/solicitations",
                params=params or None,
                headers={"Accept": "application/json"},
                timeout=httpx.Timeout(10, connect=5),
            )
            if r.status_code in (403, 429, 500):
                logger.warning("sbir_api_blocked", status=r.status_code)
                return []
            r.raise_for_status()
            data = r.json()
            sols = data if isinstance(data, list) else data.get("solicitations", [])
            for s in sols:
                s["_trestle_source"] = "SBIR.gov"
                s["_trestle_via"] = "sbir.gov"
            return sols
        except httpx.HTTPError as exc:
            logger.warning("sbir_api_error", error=str(exc))
            return []

    async def fetch_all(self, rows: int = 50, max_pages: int = 4) -> list[dict[str, Any]]:
        """Return merged SBIR opportunities."""
        all_hits: list[dict[str, Any]] = []

        gg = await self._from_grants_gov(rows=rows, max_pages=max_pages)
        all_hits.extend(gg)
        logger.info("sbir_fetcher_grants_gov", count=len(gg))

        sbir = await self._from_sbir_api()
        if sbir:
            all_hits.extend(sbir)
            logger.info("sbir_fetcher_sbir_api", count=len(sbir))

        return all_hits

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.client.aclose()
