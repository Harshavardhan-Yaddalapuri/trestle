"""SBIR.gov source adapter.

Ingests open SBIR/STTR topics from the SBIR.gov public API.

Note (verified 2026-06): The SBIR.gov public API (api.www.sbir.gov/public/api) has
begun requiring authentication tokens for all endpoints. The /topics endpoint returns
403 "Missing Authentication Token" and /solicitations returns 429 when rate-limited.
If SBIR.gov adds a public-access path in future, the adapter will work as-is.
For now, SBIRGOV_ENABLED=True should only be used with a valid API key once SBIR.gov
documents their auth flow. Tracker: TODO add SBIRGOV_API_KEY setting when available.

Real API base (spec-documented):
  GET /topics — paginated list of topics; params: rows, start, open

Topic response shape (representative — exact field names verified in smoke test):
  topicNumber:      "AF251-001"
  topicTitle:       str
  solicitationId:   str
  solicitationTitle: str
  branch:           "Air Force" | "Navy" | "Army" | "DARPA" | "HHS" | ...
  program:          "SBIR" | "STTR"
  phase:            "Phase I" | "Phase II" | "Direct to Phase II" | ...
  topicStatus:      "Open" | "Closed" | "Pre-release"
  openDate:         str  (ISO or MM/DD/YYYY)
  closeDate:        str  (ISO or MM/DD/YYYY)
  topicDescription: str  (may contain HTML)
  topicObjective:   str | None
  topicUrl:         str | None
  awardCeiling:     int | None
  awardFloor:       int | None
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

# Branch name substrings → industry tags (longest match applied first)
_BRANCH_INDUSTRY: list[tuple[str, list[str]]] = [
    ("defense health", ["defense", "healthcare"]),
    ("cbdp", ["defense", "biotech"]),
    ("darpa", ["defense", "dual_use"]),
    ("defense advanced research", ["defense", "dual_use"]),
    ("special operations", ["defense", "dual_use"]),
    ("missile defense", ["defense", "dual_use"]),
    ("air force", ["defense", "dual_use"]),
    ("space force", ["defense", "dual_use"]),
    ("army", ["defense", "dual_use"]),
    ("navy", ["defense", "dual_use"]),
    ("marine corps", ["defense", "dual_use"]),
    ("dod", ["defense", "dual_use"]),
    ("department of defense", ["defense", "dual_use"]),
    ("national institutes of health", ["healthcare", "biotech"]),
    ("nih", ["healthcare", "biotech"]),
    ("cdc", ["healthcare"]),
    ("health and human services", ["healthcare", "biotech"]),
    ("hhs", ["healthcare", "biotech"]),
    ("department of energy", ["energy", "cleantech"]),
    ("doe", ["energy", "cleantech"]),
    ("national science foundation", ["research"]),
    ("nsf", ["research"]),
    ("nasa", ["aerospace"]),
    ("usda", ["agriculture"]),
    ("agriculture", ["agriculture"]),
    ("epa", ["cleantech"]),
    ("environmental", ["cleantech"]),
]


def _strip_html(text: str) -> str:
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return " ".join(text.split())


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"continuous", "none", "n/a", "tbd"}:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    m = _US_DATE_RE.match(s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError:
            pass
    return None


def _parse_amount_cents(value: Any) -> int | None:
    if value is None:
        return None
    try:
        amount = int(float(str(value).strip()))
        return amount * 100 if amount > 0 else None
    except (ValueError, TypeError):
        return None


_PHASE_I_ONLY_RE = re.compile(r"\bphase\s+1\b|\bphase\s+i\b(?!i)", re.IGNORECASE)
_PHASE_II_RE = re.compile(r"\bphase\s+2\b|\bphase\s+ii\b", re.IGNORECASE)
_DIRECT_II_RE = re.compile(r"direct\s+to\s+phase\s+(?:2|ii)", re.IGNORECASE)


def _phase_to_stage(phase: str | None) -> list[str]:
    if not phase:
        return []
    if _DIRECT_II_RE.search(phase):
        return ["seed", "series_a"]
    if _PHASE_II_RE.search(phase):
        return ["pre_seed", "seed", "series_a"]
    if _PHASE_I_ONLY_RE.search(phase):
        return ["idea", "pre_seed", "seed"]
    return []


def _branch_to_industry(branch: str | None) -> list[str]:
    if not branch:
        return []
    b = branch.lower()
    for keyword, tags in _BRANCH_INDUSTRY:
        if keyword in b:
            return tags
    return []


def _extract_topics(body: Any) -> tuple[list[dict], int | None]:
    """Normalize API response envelope into (topics_list, total_or_None)."""
    if isinstance(body, list):
        return body, None
    if not isinstance(body, dict):
        return [], None
    for key in ("topics", "results", "data", "items", "oppHits"):
        if key in body and isinstance(body[key], list):
            total = body.get("totalCount") or body.get("count") or body.get("total")
            return body[key], total
    return [], None


class SbirGovAdapter:
    """Ingest open SBIR/STTR topics from the SBIR.gov public API."""

    source_name: ClassVar[str] = "sbirgov"

    async def fetch_all(
        self,
        client: httpx.AsyncClient,
        settings: Any,
        since: datetime | None = None,
    ) -> AsyncIterator[IngestedGrant]:
        start = 0
        pages_fetched = 0
        total: int | None = None

        while pages_fetched < settings.SBIRGOV_MAX_PAGES:
            try:
                resp = await client.get(
                    f"{settings.SBIRGOV_API_BASE}/topics",
                    params={
                        "rows": settings.SBIRGOV_PAGE_SIZE,
                        "start": start,
                        "open": 1,
                    },
                )
            except httpx.TimeoutException as exc:
                raise UpstreamError(
                    f"Timeout fetching SBIR.gov topics page {pages_fetched}",
                    code="sbirgov_timeout",
                ) from exc

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "10"))
                logger.warning(
                    "sbirgov_rate_limited",
                    page=pages_fetched,
                    retry_after=retry_after,
                )
                await asyncio.sleep(retry_after)
                continue

            if resp.status_code != 200:
                raise UpstreamError(
                    f"SBIR.gov topics returned HTTP {resp.status_code}",
                    code="sbirgov_search_error",
                )

            try:
                body = resp.json()
            except Exception:
                logger.warning("sbirgov_json_parse_error", page=pages_fetched)
                break

            topics, page_total = _extract_topics(body)
            if page_total is not None and total is None:
                total = page_total

            if not topics:
                break

            for raw_topic in topics:
                try:
                    record = self._map(raw_topic)
                    if record is not None:
                        yield record
                except Exception:
                    logger.warning(
                        "sbirgov_topic_map_error",
                        topic_number=raw_topic.get("topicNumber"),
                    )

            start += len(topics)
            pages_fetched += 1

            # Stop when we have all records
            if total is not None and start >= total:
                break
            # Or when page is short (last page)
            if len(topics) < settings.SBIRGOV_PAGE_SIZE:
                break

    def _map(self, raw: dict) -> IngestedGrant | None:
        topic_number = str(raw.get("topicNumber") or "").upper().strip()
        if not topic_number:
            logger.warning("sbirgov_missing_topic_number", raw_keys=list(raw.keys()))
            return None

        source_id = f"sbirgov:{topic_number}"

        title = str(raw.get("topicTitle") or "").strip()
        branch = str(raw.get("branch") or "").strip()
        program = str(raw.get("program") or "SBIR").strip()
        phase = str(raw.get("phase") or "").strip()
        topic_status = str(raw.get("topicStatus") or "Open").strip()

        # Description: objective block (if present) + description
        raw_desc = _strip_html(str(raw.get("topicDescription") or ""))
        raw_obj = _strip_html(str(raw.get("topicObjective") or ""))
        if raw_obj:
            description = f"**Objective:** {raw_obj}\n\n{raw_desc}".strip()
        else:
            description = raw_desc or title

        # URL
        topic_url = raw.get("topicUrl") or ""
        if not topic_url:
            topic_url = f"https://www.sbir.gov/sbirsearch/detail/{topic_number}"

        # Amounts
        amount_max = _parse_amount_cents(raw.get("awardCeiling"))
        amount_min = _parse_amount_cents(raw.get("awardFloor"))

        # Deadline
        deadline = _parse_date(raw.get("closeDate"))

        # Stage from phase
        stage = _phase_to_stage(phase)

        # Industry from branch
        industry = _branch_to_industry(branch)

        # Eligibility
        eligibility: dict[str, Any] = {
            "required_location": ["US"],
            "requires_incorporation": True,
            "max_team_size": 500,
            "_program": program,
            "_phase": phase,
            "_branch": branch,
            "_topic_number": topic_number,
            "_solicitation_id": str(raw.get("solicitationId") or ""),
        }

        if _PHASE_I_ONLY_RE.search(phase) and not _DIRECT_II_RE.search(phase):
            eligibility["max_funding_raised_usd"] = 2_000_000

        if program.upper() == "STTR":
            eligibility["_requires_research_partner"] = True

        status = "active" if topic_status.lower() == "open" else "expired"
        provider_name = f"{branch} {program}".strip() if branch else program

        return IngestedGrant(
            source="sbirgov",
            source_id=source_id,
            name=title or topic_number,
            type="grant",
            description=description,
            url=topic_url,
            application_url=None,
            amount_min_usd_cents=amount_min,
            amount_max_usd_cents=amount_max,
            deadline=deadline,
            rolling=False,
            stage=stage,
            industry=industry,
            location=["US"],
            eligibility=eligibility,
            provider_name=provider_name,
            provider_type="government",
            status=status,
            source_payload=raw,
        )
