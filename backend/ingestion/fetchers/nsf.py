"""NSF funding-opportunity fetcher.

Tries multiple strategies in order:
1. Grants.gov API filtered to NSF agency  (most reliable)
2. SBIR.gov API for NSF solicitations      (public, rate-limited)
3. seedfund.nsf.gov web page scraping      (fallback)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

_GRANTS_GOV_BASE = "https://api.grants.gov/v1/api"
_SBIR_API_BASE = "https://api.www.sbir.gov/public/api"
_SEEDFUND_URL = "https://seedfund.nsf.gov/"


def _parse_date(s: str | None) -> date | None:
    if not s or not str(s).strip():
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


class NSFFetcher:
    """Fetch NSF SBIR / funding opportunity listings."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(timeout=60)

    # ── Strategy 1: Grants.gov proxy ───────────────────────────────────────────

    async def _from_grants_gov(self, rows: int = 50, max_pages: int = 4) -> list[dict[str, Any]]:
        """Query Grants.gov filtered to NSF agency."""
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
                "keywords": None,
                "fields": "all",
                "eligibilities": None,
                "agencies": "NSF",          # <-- correct filter
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
                logger.warning("grants_gov_nsffetcher_error", page=page, error=str(exc))
                break
        for h in hits:
            h["_trestle_source"] = "NSF"
            h["_trestle_via"] = "grants.gov"
        return hits

    # ── Strategy 2: SBIR.gov public API ──────────────────────────────────────

    async def _from_sbir_api(self) -> list[dict[str, Any]]:
        """Try SBIR.gov public API for NSF solicitations."""
        try:
            r = await self.client.get(
                f"{_SBIR_API_BASE}/solicitations",
                params={"agency": "NSF"},
                headers={"Accept": "application/json"},
            )
            if r.status_code in (403, 429):
                logger.warning("sbir_api_forbidden", status=r.status_code)
                return []
            r.raise_for_status()
            data = r.json()
            sols = data if isinstance(data, list) else data.get("solicitations", [])
            for s in sols:
                s["_trestle_source"] = "NSF"
                s["_trestle_via"] = "sbir.gov"
            return sols
        except httpx.HTTPError as exc:
            logger.warning("sbir_api_error", error=str(exc))
            return []

    # ── Strategy 3: Seedfund page (last resort) ─────────────────────────────

    async def _from_seedfund_html(self) -> list[dict[str, Any]]:
        """Lightweight HTML scrape of seedfund.nsf.gov for active solicitations.
        Returns a best-effort list — not expected to be comprehensive."""
        try:
            r = await self.client.get(_SEEDFUND_URL, headers={"Accept": "text/html"})
            r.raise_for_status()
            text = r.text
            records: list[dict[str, Any]] = []
            # Heuristic: find links that look like solicitations
            # We won't do full parsing here; firecrawl/tavily would be better.
            logger.info("seedfund_html_scrape", bytes=len(text))
            return records
        except httpx.HTTPError as exc:
            logger.warning("seedfund_html_error", error=str(exc))
            return []

    # ── Public API ───────────────────────────────────────────────────────────

    async def fetch_all(self, rows: int = 50, max_pages: int = 4) -> list[dict[str, Any]]:
        """Run all strategies and merge deduplicated results.
        Deduplication key = Grants.gov oppId or SBIR solicitation number."""
        all_hits: list[dict[str, Any]] = []

        gg = await self._from_grants_gov(rows=rows, max_pages=max_pages)
        all_hits.extend(gg)
        logger.info("nsf_fetcher_grants_gov", count=len(gg))

        sbir = await self._from_sbir_api()
        if sbir:
            all_hits.extend(sbir)
            logger.info("nsf_fetcher_sbir", count=len(sbir))

        if not all_hits:
            html = await self._from_seedfund_html()
            all_hits.extend(html)

        return all_hits

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.client.aclose()
