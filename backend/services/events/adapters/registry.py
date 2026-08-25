from __future__ import annotations

from backend.services.events.adapters.base import EventSourceAdapter
from backend.services.events.adapters.eventbrite import EventbriteAdapter
from backend.services.events.adapters.generic_jsonld import GenericJsonLdAdapter
from backend.services.events.adapters.luma import LumaAdapter
from backend.services.events.adapters.meetup import MeetupAdapter
from backend.services.events.adapters.startupgrind import StartupGrindAdapter
from backend.services.events.adapters.techstars import TechstarsAdapter

_ADAPTERS: list[EventSourceAdapter] = [
    StartupGrindAdapter(),
    TechstarsAdapter(),
    EventbriteAdapter(),
    MeetupAdapter(),
    LumaAdapter(),
]
_FALLBACK_ADAPTER = GenericJsonLdAdapter()


def get_adapter_for_source_url(source_url: str) -> EventSourceAdapter:
    return get_custom_adapter_for_source_url(source_url) or _FALLBACK_ADAPTER


def get_custom_adapter_for_source_url(source_url: str) -> EventSourceAdapter | None:
    """Return a known provider adapter; unknown hosts are left to generic discovery."""
    for adapter in _ADAPTERS:
        if adapter.supports(source_url):
            return adapter
    return None


def list_adapters() -> list[EventSourceAdapter]:
    return [*_ADAPTERS, _FALLBACK_ADAPTER]
