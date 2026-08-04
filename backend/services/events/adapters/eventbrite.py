"""Eventbrite adapter driven by the JSON-LD embedded in listing pages.

Eventbrite retired public event *search* from their v3 API — the remaining
endpoints only expose events owned by the token holder, which is useless for
discovery. Their public listing pages, however, ship a complete schema.org
`ItemList` of Event nodes, so parsing that markup is both simpler and broader
than an authenticated API would be.

Listing pages are paginated with `?page=N` and return 20 events per page.
Single event pages (`/e/<slug>`) are fetched as-is.
"""
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from backend.core.config import Settings
from backend.core.logging import get_logger
from backend.services.events.parser import DiscoveredEvent, parse_jsonld_events

logger = get_logger(__name__)

# Path prefix for a single event page, which has nothing to paginate.
_SINGLE_EVENT_PREFIX = "/e/"


class EventbriteAdapter:
    source_name = "eventbrite"
    max_pages = 3

    def supports(self, source_url: str) -> bool:
        host = urlparse(source_url).netloc.lower()
        return "eventbrite" in host

    async def discover(
        self,
        client: httpx.AsyncClient,
        settings: Settings,
        source_url: str,
    ) -> list[DiscoveredEvent]:
        page_count = 1 if _is_single_event_page(source_url) else self.max_pages

        events: list[DiscoveredEvent] = []
        seen_ids: set[str] = set()

        for page in range(1, page_count + 1):
            page_url = source_url if page == 1 else _with_page_param(source_url, page)
            response = await client.get(
                page_url, timeout=settings.EVENTS_HTTP_TIMEOUT_SECONDS
            )
            response.raise_for_status()

            page_events = parse_jsonld_events(
                response.text, page_url, source_name=self.source_name
            )
            new_events = [
                event for event in page_events if event.source_id not in seen_ids
            ]
            if not new_events:
                # Past the last page, or the listing repeated itself.
                break

            for event in new_events:
                seen_ids.add(event.source_id)
            events.extend(new_events)

        logger.info(
            "eventbrite_events_fetched",
            source_url=source_url,
            discovered=len(events),
        )
        return events


def _is_single_event_page(source_url: str) -> bool:
    return urlparse(source_url).path.startswith(_SINGLE_EVENT_PREFIX)


def _with_page_param(source_url: str, page: int) -> str:
    parts = urlparse(source_url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if key != "page"]
    query.append(("page", str(page)))
    return urlunparse(parts._replace(query=urlencode(query)))
