"""Startup Grind adapter backed by their public chapter events JSON API.

Startup Grind exposes `/api/event/` for the upcoming list and
`/api/event/<id>/` for per-event detail, which carries the chapter (host),
description and timezone that the list endpoint omits.
"""
from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import httpx

from backend.core.config import Settings
from backend.core.logging import get_logger
from backend.services.events.parser import DiscoveredEvent
from backend.services.events.taxonomy import (
    ATTENDEE_KEYWORDS,
    BENEFIT_KEYWORDS,
    INDUSTRY_KEYWORDS,
    STAGE_KEYWORDS,
    extract_tags,
    normalize_text,
    parse_iso_datetime,
)

logger = get_logger(__name__)

_DEFAULT_ORIGIN = "https://www.startupgrind.com"
_DEFAULT_HOST_NAME = "Startup Grind"
_HOST_QUALITY_SCORE = 0.85
_CANCELLED_STATUSES = frozenset({"cancelled", "canceled"})


def _list_api_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    base = (
        f"{parsed.scheme}://{parsed.netloc}"
        if parsed.scheme and parsed.netloc
        else _DEFAULT_ORIGIN
    )
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
        list_rows = await self._fetch_list(client, settings, source_url)
        if not list_rows:
            return []

        events: list[DiscoveredEvent] = []
        for row in list_rows[: self.max_events]:
            event_id = row.get("id")
            if event_id is None:
                continue
            detail = await self._fetch_detail(client, settings, source_url, event_id, row)
            event = self._to_discovered_event(event_id, row, detail, source_url)
            if event is not None:
                events.append(event)
        return events

    async def _fetch_list(
        self,
        client: httpx.AsyncClient,
        settings: Settings,
        source_url: str,
    ) -> list[dict]:
        rows: list[dict] = []
        next_url: str | None = _list_api_url(source_url)
        pages = 0

        while next_url and pages < self.max_pages:
            response = await client.get(
                next_url,
                timeout=settings.EVENTS_HTTP_TIMEOUT_SECONDS,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
            page_rows = payload.get("results") or []
            if not isinstance(page_rows, list):
                break
            rows.extend(page_rows)
            pages += 1
            next_url = (
                ((payload.get("links") or {}).get("next"))
                if isinstance(payload, dict)
                else None
            )

        return rows

    async def _fetch_detail(
        self,
        client: httpx.AsyncClient,
        settings: Settings,
        source_url: str,
        event_id: object,
        fallback: dict,
    ) -> dict:
        detail_url = urljoin(source_url, f"/api/event/{event_id}/")
        try:
            response = await client.get(
                detail_url,
                timeout=settings.EVENTS_HTTP_TIMEOUT_SECONDS,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            detail = response.json()
        except Exception:
            logger.warning("startupgrind_event_detail_failed", event_id=event_id)
            return fallback
        return detail if isinstance(detail, dict) else fallback

    def _to_discovered_event(
        self,
        event_id: object,
        row: dict,
        detail: dict,
        source_url: str,
    ) -> DiscoveredEvent | None:
        title = normalize_text(detail.get("title") or row.get("title"))
        starts_at = parse_iso_datetime(detail.get("start_date") or row.get("start_date"))
        if not title or starts_at is None:
            return None
        ends_at = parse_iso_datetime(detail.get("end_date") or row.get("end_date"))

        chapter = detail.get("chapter") if isinstance(detail.get("chapter"), dict) else {}
        host_name = normalize_text(chapter.get("title")) or _DEFAULT_HOST_NAME
        city = normalize_text(chapter.get("city")) or None
        region = normalize_text(chapter.get("state")) or None
        country = normalize_text(chapter.get("country_name") or chapter.get("country")) or None
        location_text = ", ".join(v for v in [city, region, country] if v) or None

        description = normalize_text(
            detail.get("description")
            or detail.get("description_short")
            or row.get("description")
        )
        manual_tags = detail.get("tags")
        tag_blob = (
            " ".join(normalize_text(tag) for tag in manual_tags)
            if isinstance(manual_tags, list)
            else ""
        )
        context_text = " ".join(
            value
            for value in [title, description, host_name, location_text or "", tag_blob]
            if value
        )

        return DiscoveredEvent(
            source=self.source_name,
            source_id=f"startupgrind:{event_id}",
            name=title,
            description=description,
            url=normalize_text(detail.get("url") or row.get("url")) or source_url,
            host_name=host_name,
            starts_at=starts_at,
            ends_at=ends_at,
            timezone=detail.get("event_timezone"),
            is_virtual=bool(detail.get("is_virtual_event")) or "online" in title.lower(),
            location_text=location_text,
            city=city,
            region=region,
            country=country,
            industry_tags=extract_tags(context_text, INDUSTRY_KEYWORDS),
            stage_tags=extract_tags(context_text, STAGE_KEYWORDS),
            benefit_tags=extract_tags(context_text, BENEFIT_KEYWORDS),
            attendee_types=extract_tags(context_text, ATTENDEE_KEYWORDS),
            application_required=False,
            host_quality_score=_HOST_QUALITY_SCORE,
            status=self._status(row, detail, starts_at, ends_at),
            source_payload=detail,
        )

    @staticmethod
    def _status(
        row: dict,
        detail: dict,
        starts_at: datetime,
        ends_at: datetime | None,
    ) -> str:
        raw_status = normalize_text(detail.get("status") or row.get("status")).lower()
        if raw_status in _CANCELLED_STATUSES:
            return "archived"
        if (ends_at or starts_at) < datetime.now(UTC):
            return "expired"
        return "active"
