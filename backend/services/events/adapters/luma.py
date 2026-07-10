from __future__ import annotations

from urllib.parse import urlparse

import httpx

from backend.core.config import Settings
from backend.services.events.parser import DiscoveredEvent, parse_jsonld_events


class LumaAdapter:
    source_name = "luma"

    def supports(self, source_url: str) -> bool:
        host = urlparse(source_url).netloc.lower()
        return "lu.ma" in host or host.endswith("luma.com")

    async def discover(
        self,
        client: httpx.AsyncClient,
        settings: Settings,
        source_url: str,
    ) -> list[DiscoveredEvent]:
        response = await client.get(source_url, timeout=settings.EVENTS_HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        return parse_jsonld_events(
            response.text,
            source_url,
            source_name=self.source_name,
        )
