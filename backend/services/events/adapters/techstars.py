"""Techstars events adapter backed by their public Typesense search index.

Techstars renders `/events/search` entirely client-side, so there is no JSON-LD
to scrape and their old WordPress events API is gone. The page instead reads a
search-only Typesense credential from `/api/search/config/events` and queries
the index directly. This adapter follows the same two-step flow, which gives us
clean structured records instead of brittle HTML scraping.

The credential is fetched per sweep rather than hardcoded, so key rotation on
the Techstars side does not break ingestion.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from backend.core.config import Settings
from backend.core.logging import get_logger
from backend.services.events.location import parse_location_label
from backend.services.events.parser import DiscoveredEvent
from backend.services.events.taxonomy import (
    ATTENDEE_KEYWORDS,
    BENEFIT_KEYWORDS,
    INDUSTRY_KEYWORDS,
    STAGE_KEYWORDS,
    extract_tags,
    host_quality_score,
    merge_tags,
    normalize_text,
    parse_iso_datetime,
)

logger = get_logger(__name__)

_HOST_NAME = "Techstars"
_SEARCH_COLLECTION = "events"
_CONFIG_PATH_TEMPLATE = "/api/search/config/{collection}"
_EVENTS_FALLBACK_PATH = "/events/search"

# Typesense caps a single page at 250 documents.
_MAX_PAGE_SIZE = 250

# Techstars event_type values carry intent that free-text matching would miss.
# Types whose benefit is not one of our tags (workshops, webinars) are omitted
# rather than mapped to a loose approximation.
_EVENT_TYPE_BENEFITS: dict[str, tuple[str, ...]] = {
    # 54 hours of team building that ends in a pitch to judges.
    "startup weekend": ("networking", "investor_access"),
    "startup week": ("networking",),
    "networking/meetup": ("networking",),
    "network": ("networking",),
    "conference": ("networking",),
    "vertical network partner event": ("partnerships", "networking"),
}

_ONLINE_LOCATION_TYPES = frozenset({"online", "virtual", "hybrid"})


@dataclass(frozen=True, slots=True)
class TypesenseSearchConfig:
    """Search-only Typesense credentials published by the Techstars frontend."""

    url: str
    collection: str
    api_key: str


class TechstarsAdapter:
    source_name = "techstars"
    page_size = _MAX_PAGE_SIZE
    max_pages = 4

    def supports(self, source_url: str) -> bool:
        host = urlparse(source_url).netloc.lower()
        return "techstars.com" in host

    async def discover(
        self,
        client: httpx.AsyncClient,
        settings: Settings,
        source_url: str,
    ) -> list[DiscoveredEvent]:
        config = await self._fetch_search_config(client, settings, source_url)
        documents = await self._fetch_upcoming_documents(client, settings, config)

        events: list[DiscoveredEvent] = []
        for document in documents:
            event = self._to_discovered_event(document, source_url)
            if event is not None:
                events.append(event)
        return events

    async def _fetch_search_config(
        self,
        client: httpx.AsyncClient,
        settings: Settings,
        source_url: str,
    ) -> TypesenseSearchConfig:
        config_url = urljoin(
            _site_origin(source_url),
            _CONFIG_PATH_TEMPLATE.format(collection=_SEARCH_COLLECTION),
        )
        response = await client.get(
            config_url,
            timeout=settings.EVENTS_HTTP_TIMEOUT_SECONDS,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()

        url = normalize_text(payload.get("url"))
        api_key = normalize_text(payload.get("apiKey"))
        if not url or not api_key:
            raise ValueError(
                f"Techstars search config at {config_url} is missing url or apiKey"
            )
        return TypesenseSearchConfig(
            url=url.rstrip("/"),
            collection=normalize_text(payload.get("collection")) or _SEARCH_COLLECTION,
            api_key=api_key,
        )

    async def _fetch_upcoming_documents(
        self,
        client: httpx.AsyncClient,
        settings: Settings,
        config: TypesenseSearchConfig,
    ) -> list[dict[str, Any]]:
        search_url = f"{config.url}/collections/{config.collection}/documents/search"
        documents: list[dict[str, Any]] = []

        for page in range(1, self.max_pages + 1):
            response = await client.get(
                search_url,
                params={
                    "q": "*",
                    "query_by": "title",
                    "per_page": min(self.page_size, _MAX_PAGE_SIZE),
                    "page": page,
                    # Only event_start_epoch is filterable in their schema.
                    "filter_by": f"event_start_epoch:>={_utc_midnight_epoch()}",
                    "sort_by": "event_start_epoch:asc",
                },
                headers={"X-TYPESENSE-API-KEY": config.api_key},
                timeout=settings.EVENTS_HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()

            hits = payload.get("hits")
            if not isinstance(hits, list) or not hits:
                break

            for hit in hits:
                document = hit.get("document")
                if isinstance(document, dict):
                    documents.append(document)

            found = payload.get("found")
            if isinstance(found, int) and len(documents) >= found:
                break

        logger.info(
            "techstars_events_fetched",
            collection=config.collection,
            documents=len(documents),
        )
        return documents

    def _to_discovered_event(
        self,
        document: dict[str, Any],
        source_url: str,
    ) -> DiscoveredEvent | None:
        document_id = normalize_text(document.get("id"))
        name = normalize_text(document.get("title"))
        starts_at = _document_start(document)
        if not document_id or not name or starts_at is None:
            return None

        ends_at = parse_iso_datetime(document.get("event_end"))
        event_type = normalize_text(document.get("event_type"))
        verticals = _industry_verticals(document)
        location = parse_location_label(document.get("location"))
        is_virtual = location.is_virtual or _is_online(document.get("location_type"))

        context_text = " ".join(
            value for value in [name, event_type, location.text or "", *verticals] if value
        )
        type_benefits = _EVENT_TYPE_BENEFITS.get(event_type.lower(), ())

        return DiscoveredEvent(
            source=self.source_name,
            source_id=f"techstars:{document_id}",
            name=name,
            description=_build_description(name, event_type, location.text),
            url=_event_url(document.get("website"), source_url),
            host_name=_HOST_NAME,
            starts_at=starts_at,
            ends_at=ends_at,
            is_virtual=is_virtual,
            location_text=location.text,
            city=location.city,
            region=location.region,
            country=location.country,
            industry_tags=extract_tags(context_text, INDUSTRY_KEYWORDS),
            stage_tags=extract_tags(context_text, STAGE_KEYWORDS),
            benefit_tags=merge_tags(
                extract_tags(context_text, BENEFIT_KEYWORDS), type_benefits
            ),
            # Every Techstars event targets founders, whatever the copy says.
            attendee_types=merge_tags(
                extract_tags(context_text, ATTENDEE_KEYWORDS), ("founders",)
            ),
            host_quality_score=host_quality_score(_HOST_NAME),
            status="expired" if (ends_at or starts_at) < datetime.now(UTC) else "active",
            source_payload=document,
        )


def _site_origin(source_url: str) -> str:
    parsed = urlparse(source_url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return "https://www.techstars.com"


def _utc_midnight_epoch() -> int:
    today = datetime.now(UTC)
    return calendar.timegm((today.year, today.month, today.day, 0, 0, 0))


def _document_start(document: dict[str, Any]) -> datetime | None:
    starts_at = parse_iso_datetime(document.get("event_start"))
    if starts_at is not None:
        return starts_at
    epoch = document.get("event_start_epoch")
    if isinstance(epoch, (int, float)):
        return datetime.fromtimestamp(int(epoch), tz=UTC)
    return None


def _industry_verticals(document: dict[str, Any]) -> list[str]:
    raw = document.get("industry_vertical")
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [text for text in (normalize_text(item) for item in raw) if text]


def _is_online(location_type: Any) -> bool:
    return normalize_text(location_type).lower() in _ONLINE_LOCATION_TYPES


def _build_description(name: str, event_type: str, location_text: str | None) -> str:
    """Techstars' index carries no blurb, so summarise the structured fields."""
    parts = [event_type or "Techstars event", f"hosted by {_HOST_NAME}"]
    if location_text:
        parts.append(f"in {location_text}")
    return f"{name} — {' '.join(parts)}."


def _event_url(website: Any, source_url: str) -> str:
    """Prefer the organiser's registration page, falling back to the calendar."""
    url = normalize_text(website)
    if not url:
        return urljoin(_site_origin(source_url), _EVENTS_FALLBACK_PATH)
    if not urlparse(url).scheme:
        return f"https://{url.lstrip('/')}"
    return url
