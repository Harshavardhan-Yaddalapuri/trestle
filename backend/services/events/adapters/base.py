from __future__ import annotations

from typing import Protocol

import httpx

from backend.core.config import Settings
from backend.services.events.parser import DiscoveredEvent


class EventSourceAdapter(Protocol):
    source_name: str

    def supports(self, source_url: str) -> bool:
        ...

    async def discover(
        self,
        client: httpx.AsyncClient,
        settings: Settings,
        source_url: str,
    ) -> list[DiscoveredEvent]:
        ...
