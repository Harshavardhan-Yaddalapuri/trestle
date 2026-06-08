"""Grants.gov Source2 adapter.

Ingests currently-posted opportunities from the Grants.gov public Search2 API.
No API key required — the endpoint is publicly accessible without authentication.

Real API endpoints (verified 2026-06):
  POST /search2        — paginated search; hits are in data.oppHits
  POST /fetchOpportunity — detail; full record under data, synopsis under data.synopsis

Search hit shape (relevant fields):
  id: str (e.g. "141593")
  number: str (e.g. "P12AC10113")
  title: str
  agencyCode: str
  agency: str  (display name)
  openDate: str  "MM/DD/YYYY"
  closeDate: str  "MM/DD/YYYY" or ""
  oppStatus: str
  cfdaList: list[str]

Synopsis shape (within detail["data"]["synopsis"]):
  awardCeiling: int | "none"
  awardFloor: int | "none"
  applicantTypes: list[{"id": str, "description": str}]
  synopsisDesc: str | None
  responseDate: str | None  (ISO date or None)
  agencyName: str
"""
from __future__ import annotations

import asyncio
import html
import re
from datetime import date, datetime
from typing import Any, AsyncIterator, ClassVar

import httpx

from backend.core.errors import UpstreamError
from backend.core.logging import get_logger
from backend.services.ingest.base import IngestedGrant

logger = get_logger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_US_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")

# Applicant-type description substrings that indicate startup eligibility
_FOR_STARTUP_SUBSTRINGS = frozenset({"small business", "small businesses", "for-profit"})

# Applicant-type description substrings that indicate non-startup eligibility only
_EXCLUSION_SUBSTRINGS = frozenset({
    "nonprofit",
    "not-for-profit",
    "501(c)",
    "individuals",
    "state government",
    "local government",
    "federal government",
    "county government",
    "city or township",
    "special district",
    "housing authority",
    "tribal government",
    "school district",
    "institution of higher education",
    "university",
    "college",
    "public and state controlled",
})


def _strip_html(text: str) -> str:
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return " ".join(text.split())


def _parse_amount_cents(value: Any) -> int | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in {"none", "", "0"}:
        return None
    try:
        amount = int(float(s))
        return amount * 100 if amount > 0 else None
    except (ValueError, TypeError):
        return None


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"continuous", "none"}:
        return None
    # Try ISO 8601 first
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    # Try MM/DD/YYYY (Grants.gov format)
    m = _US_DATE_RE.match(s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError:
            pass
    return None


def _extract_applicant_descriptions(applicant_types: list) -> list[str]:
    """Normalize applicant_types from list of {id, description} dicts or plain strings."""
    descriptions: list[str] = []
    for item in applicant_types:
        if isinstance(item, dict):
            desc = item.get("description") or ""
            if desc:
                descriptions.append(desc)
        elif isinstance(item, str):
            descriptions.append(item)
    return descriptions


def _parse_eligibility(applicant_descriptions: list[str]) -> dict[str, Any]:
    """Return eligibility extras derived from Grants.gov applicant type descriptions."""
    if not applicant_descriptions:
        return {}

    for desc in applicant_descriptions:
        d_lower = desc.lower()
        if any(sub in d_lower for sub in _FOR_STARTUP_SUBSTRINGS):
            return {}  # startup-eligible, no exclusion flag

    all_excluded = all(
        any(sub in desc.lower() for sub in _EXCLUSION_SUBSTRINGS)
        for desc in applicant_descriptions
    )
    if all_excluded:
        return {"_excluded_for_startups": True}

    return {}


class GrantsGovAdapter:
    """Ingest currently-posted opportunities from the Grants.gov Search2 API."""

    source_name: ClassVar[str] = "grantsgov"

    async def fetch_all(
        self,
        client: httpx.AsyncClient,
        settings: Any,
        since: datetime | None = None,
    ) -> AsyncIterator[IngestedGrant]:
        sem = asyncio.Semaphore(5)
        start_record_num = 0
        pages_fetched = 0
        hit_count: int | None = None

        while hit_count is None or (
            start_record_num < hit_count
            and pages_fetched < settings.GRANTSGOV_MAX_PAGES
        ):
            try:
                resp = await client.post(
                    f"{settings.GRANTSGOV_API_BASE}/search2",
                    json={
                        "rows": settings.GRANTSGOV_PAGE_SIZE,
                        "keyword": "",
                        "oppStatuses": "posted",
                        "startRecordNum": start_record_num,
                    },
                )
            except httpx.TimeoutException as exc:
                raise UpstreamError(
                    f"Timeout fetching Grants.gov page {pages_fetched}",
                    code="grantsgov_timeout",
                ) from exc

            if resp.status_code != 200:
                raise UpstreamError(
                    f"Grants.gov search2 returned HTTP {resp.status_code}",
                    code="grantsgov_search_error",
                )

            body = resp.json()
            search_data = body.get("data") or {}
            hit_count = search_data.get("hitCount", 0)
            # API uses "oppHits" (not "hits")
            hits: list[dict] = search_data.get("oppHits") or []

            if not hits:
                break

            tasks = [
                asyncio.create_task(
                    self._fetch_record(client, settings, sem, hit)
                )
                for hit in hits
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, BaseException):
                    logger.warning("grantsgov_record_task_error", error=str(result))
                    continue
                if result is not None:
                    yield result  # type: ignore[misc]

            start_record_num += len(hits)
            pages_fetched += 1

    async def _fetch_record(
        self,
        client: httpx.AsyncClient,
        settings: Any,
        sem: asyncio.Semaphore,
        hit: dict,
    ) -> IngestedGrant | None:
        async with sem:
            for attempt in range(settings.INGEST_HTTP_MAX_RETRIES):
                try:
                    resp = await client.post(
                        f"{settings.GRANTSGOV_API_BASE}/fetchOpportunity",
                        json={"opportunityId": hit["id"]},
                    )
                except httpx.TimeoutException:
                    logger.warning(
                        "grantsgov_detail_timeout",
                        opportunity_id=hit.get("id"),
                        attempt=attempt,
                    )
                    if attempt >= settings.INGEST_HTTP_MAX_RETRIES - 1:
                        return None
                    await asyncio.sleep(1)
                    continue

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "5"))
                    logger.warning(
                        "grantsgov_detail_rate_limited",
                        opportunity_id=hit.get("id"),
                        retry_after=retry_after,
                        attempt=attempt,
                    )
                    if attempt >= settings.INGEST_HTTP_MAX_RETRIES - 1:
                        return None
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status_code == 404:
                    logger.warning(
                        "grantsgov_detail_not_found",
                        opportunity_id=hit.get("id"),
                    )
                    return None

                if resp.status_code != 200:
                    logger.warning(
                        "grantsgov_detail_error",
                        opportunity_id=hit.get("id"),
                        status=resp.status_code,
                    )
                    return None

                try:
                    # Real API wraps detail under data
                    body = resp.json()
                    detail = body.get("data") or body
                    return self._map(hit, detail)
                except Exception:
                    logger.exception(
                        "grantsgov_detail_parse_error",
                        opportunity_id=hit.get("id"),
                    )
                    return None

            return None

    def _map(self, hit: dict, detail: dict) -> IngestedGrant:
        synopsis: dict = detail.get("synopsis") or {}

        # Deadline — prefer hit's closeDate, fall back to synopsis responseDate
        close_date = hit.get("closeDate") or synopsis.get("responseDate")
        deadline = _parse_date(close_date)
        rolling = deadline is None

        # Amounts (API may return int or "none" string)
        amount_min = _parse_amount_cents(synopsis.get("awardFloor"))
        amount_max = _parse_amount_cents(synopsis.get("awardCeiling"))

        # Applicant types: list of {id, description} dicts in real API
        raw_types: list = synopsis.get("applicantTypes") or []
        descriptions = _extract_applicant_descriptions(raw_types)
        extra_elig = _parse_eligibility(descriptions)

        eligibility: dict[str, Any] = {
            "required_location": ["US"],
            "_applicant_types": descriptions,
            "_cfda_numbers": hit.get("cfdaList") or [],
            "_agency_code": hit.get("agencyCode") or "",
            **extra_elig,
        }

        raw_desc = synopsis.get("synopsisDesc") or ""
        description = _strip_html(raw_desc) or hit.get("title", "").strip()

        # Agency name: hit uses "agency" key (real API), synopsis uses "agencyName"
        agency_name = (
            hit.get("agency")
            or synopsis.get("agencyName")
            or "Grants.gov"
        )

        opp_id = hit.get("id", "")
        opp_number = hit.get("number") or str(opp_id)

        apply_url: str | None = synopsis.get("applyUrl") or None

        return IngestedGrant(
            source="grantsgov",
            source_id=f"grantsgov:{opp_number}",
            name=hit.get("title", "").strip(),
            type="grant",
            description=description,
            url=f"https://www.grants.gov/search-results-detail/{opp_id}",
            application_url=apply_url,
            amount_min_usd_cents=amount_min,
            amount_max_usd_cents=amount_max,
            deadline=deadline,
            rolling=rolling,
            stage=[],
            industry=[],
            location=["US"],
            eligibility=eligibility,
            provider_name=agency_name,
            provider_type="government",
            status="active",
            source_payload=detail,
        )
