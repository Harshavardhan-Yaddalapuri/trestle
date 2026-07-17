from __future__ import annotations

import httpx
import respx

from backend.core.config import Settings
from backend.services.events.adapters.registry import get_adapter_for_source_url
from backend.services.events.discovery import discover_events_from_web


def _settings(**overrides) -> Settings:
    base = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/0",
        EVENTS_ENABLED=True,
        EVENTS_SOURCE_URLS="",
        EVENTS_HTTP_TIMEOUT_SECONDS=10.0,
    )
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


def _event_jsonld(name: str, url: str) -> str:
    return f"""
    <html><body>
      <script type="application/ld+json">
        {{
          "@context":"https://schema.org",
          "@type":"Event",
          "name":"{name}",
          "startDate":"2026-12-01T10:00:00Z",
          "url":"{url}"
        }}
      </script>
    </body></html>
    """


def test_adapter_registry_selection():
    assert get_adapter_for_source_url("https://www.eventbrite.com/e/foo").source_name == "eventbrite"
    assert get_adapter_for_source_url("https://www.meetup.com/foo/events").source_name == "meetup"
    assert get_adapter_for_source_url("https://lu.ma/abc123").source_name == "luma"
    assert get_adapter_for_source_url("https://startupgrind.com/events").source_name == "web_jsonld"


async def test_discover_events_uses_provider_source_name():
    settings = _settings(
        EVENTS_SOURCE_URLS="https://www.eventbrite.com/e/foo,https://startupgrind.com/events/bar"
    )
    with respx.mock:
        respx.get("https://www.eventbrite.com/e/foo").mock(
            return_value=httpx.Response(
                200,
                text=_event_jsonld(
                    "Eventbrite Founder Night",
                    "https://www.eventbrite.com/e/foo",
                ),
            )
        )
        respx.get("https://startupgrind.com/events/bar").mock(
            return_value=httpx.Response(
                200,
                text=_event_jsonld(
                    "Community Builder Meetup",
                    "https://startupgrind.com/events/bar",
                ),
            )
        )

        events = await discover_events_from_web(settings)

    assert len(events) == 2
    by_name = {event.name: event for event in events}
    assert by_name["Eventbrite Founder Night"].source == "eventbrite"
    assert by_name["Community Builder Meetup"].source == "web_jsonld"
