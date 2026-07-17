from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import httpx

from backend.core.config import Settings
from backend.core.logging import get_logger
from backend.services.events.parser import DiscoveredEvent

logger = get_logger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")

_INDUSTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ai": ("ai", "artificial intelligence", "machine learning", "llm"),
    "biotech": ("biotech", "life sciences", "pharma", "wet lab"),
    "climate": ("climate", "cleantech", "decarbonization", "energy transition"),
    "fintech": ("fintech", "payments", "banking", "financial"),
    "healthcare": ("healthcare", "digital health", "medtech", "health"),
    "saas": ("saas", "software"),
}

_STAGE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "idea": ("idea stage", "first-time founder"),
    "pre_seed": ("pre-seed", "pre seed"),
    "seed": ("seed stage", "seed founders", "seed startup"),
    "series_a": ("series a",),
    "growth": ("growth stage", "series b", "series c"),
}

_BENEFIT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "networking": ("networking", "mixer", "community"),
    "investor_access": ("investor", "vc", "fundraising", "demo day", "pitch"),
    "customer_discovery": ("customer", "go-to-market", "gtm", "sales"),
    "partnerships": ("partnership", "corporate", "business development"),
    "hiring": ("hiring", "talent", "recruiting"),
}

_ATTENDEE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "founders": ("founder", "startup", "entrepreneur"),
    "investors": ("investor", "vc", "angel"),
    "developers": ("developer", "engineer"),
    "students": ("student", "university"),
}


def _normalized_text(value: str | None) -> str:
    if not value:
        return ""
    text = _TAG_RE.sub(" ", value)
    text = html.unescape(text)
    return " ".join(text.split())


def _extract_tags(text: str, mapping: dict[str, tuple[str, ...]]) -> list[str]:
    haystack = text.lower()
    return [tag for tag, phrases in mapping.items() if any(p in haystack for p in phrases)]


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _list_api_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    base = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else "https://www.startupgrind.com"
    if parsed.path.startswith("/api/event"):
        return source_url
    return urljoin(base, "/api/event/?upcoming=true")


class StartupGrindAdapter:
    source_name = "startupgrind"
    max_pages = 2
    max_events = 120

    def supports(self, source_url: str) -> bool:
        host = urlparse(source_url).netloc.lower()
        return "startupgrind.com" in host

    async def discover(
        self,
        client: httpx.AsyncClient,
        settings: Settings,
        source_url: str,
    ) -> list[DiscoveredEvent]:
        list_url = _list_api_url(source_url)
        list_rows: list[dict] = []
        next_url: str | None = list_url
        pages = 0

        while next_url and pages < self.max_pages:
            response = await client.get(
                next_url,
                timeout=settings.EVENTS_HTTP_TIMEOUT_SECONDS,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("results") or []
            if not isinstance(rows, list):
                break
            list_rows.extend(rows)
            pages += 1
            next_url = ((payload.get("links") or {}).get("next")) if isinstance(payload, dict) else None

        if not list_rows:
            return []

        events: list[DiscoveredEvent] = []
        for row in list_rows[: self.max_events]:
            event_id = row.get("id")
            if event_id is None:
                continue
            detail_url = urljoin(source_url, f"/api/event/{event_id}/")
            try:
                detail_res = await client.get(
                    detail_url,
                    timeout=settings.EVENTS_HTTP_TIMEOUT_SECONDS,
                    headers={"Accept": "application/json"},
                )
                detail_res.raise_for_status()
                detail = detail_res.json()
            except Exception:
                logger.warning("startupgrind_event_detail_failed", event_id=event_id)
                detail = row

            title = _normalized_text(detail.get("title") or row.get("title"))
            starts_at = _parse_datetime(detail.get("start_date") or row.get("start_date"))
            if not title or starts_at is None:
                continue
            ends_at = _parse_datetime(detail.get("end_date") or row.get("end_date"))

            chapter = detail.get("chapter") if isinstance(detail.get("chapter"), dict) else {}
            host_name = _normalized_text(chapter.get("title")) or "Startup Grind"
            city = _normalized_text(chapter.get("city")) or None
            region = _normalized_text(chapter.get("state")) or None
            country = _normalized_text(chapter.get("country_name") or chapter.get("country")) or None
            location_text = ", ".join(v for v in [city, region, country] if v) or None

            description = _normalized_text(
                detail.get("description")
                or detail.get("description_short")
                or row.get("description")
            )
            context_text = " ".join(v for v in [title, description, host_name, location_text or ""] if v)

            tag_values = detail.get("tags")
            if isinstance(tag_values, list):
                manual_tags = [_normalized_text(str(v)) for v in tag_values if _normalized_text(str(v))]
            else:
                manual_tags = []
            manual_blob = " ".join(manual_tags)
            enrich_text = f"{context_text} {manual_blob}"

            url = _normalized_text(detail.get("url") or row.get("url")) or source_url
            is_virtual = bool(detail.get("is_virtual_event")) or "online" in title.lower()
            status_raw = _normalized_text(str(detail.get("status") or row.get("status") or "")).lower()
            status = "active"
            if status_raw in {"cancelled", "canceled"}:
                status = "archived"
            elif (ends_at or starts_at) < datetime.now(UTC):
                status = "expired"

            events.append(
                DiscoveredEvent(
                    source=self.source_name,
                    source_id=f"startupgrind:{event_id}",
                    name=title,
                    description=description,
                    url=url,
                    host_name=host_name,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    timezone=detail.get("event_timezone"),
                    is_virtual=is_virtual,
                    location_text=location_text,
                    city=city,
                    region=region,
                    country=country,
                    industry_tags=_extract_tags(enrich_text, _INDUSTRY_KEYWORDS),
                    stage_tags=_extract_tags(enrich_text, _STAGE_KEYWORDS),
                    benefit_tags=_extract_tags(enrich_text, _BENEFIT_KEYWORDS),
                    attendee_types=_extract_tags(enrich_text, _ATTENDEE_KEYWORDS),
                    cost_usd_cents=None,
                    application_required=False,
                    host_quality_score=0.85,
                    status=status,
                    source_payload=detail if isinstance(detail, dict) else row,
                )
            )

        return events
