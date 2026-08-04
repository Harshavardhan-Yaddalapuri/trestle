from __future__ import annotations

from datetime import UTC, datetime

import httpx
import respx

from backend.core.config import Settings
from backend.services.events.adapters.eventbrite import EventbriteAdapter
from backend.services.events.adapters.registry import get_adapter_for_source_url
from backend.services.events.discovery import discover_events_from_web
from backend.services.events.parser import parse_jsonld_events

EVENTBRITE_LISTING_URL = "https://www.eventbrite.com/d/online/startup/"


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


def _eventbrite_item_list(*names: str) -> str:
    items = ",".join(
        f"""
        {{
          "@type":"ListItem",
          "position":{index + 1},
          "item":{{
            "@type":"Event",
            "name":"{name}",
            "startDate":"2026-12-0{index + 1}",
            "url":"https://www.eventbrite.com/e/{name.lower().replace(' ', '-')}",
            "eventAttendanceMode":"https://schema.org/OnlineEventAttendanceMode",
            "location":{{"@type":"VirtualLocation"}}
          }}
        }}
        """
        for index, name in enumerate(names)
    )
    return f"""
    <html><body>
      <script type="application/ld+json">
        {{"@context":"https://schema.org","@type":"ItemList","itemListElement":[{items}]}}
      </script>
    </body></html>
    """


def test_adapter_registry_selection():
    assert get_adapter_for_source_url("https://www.eventbrite.com/e/foo").source_name == "eventbrite"
    assert get_adapter_for_source_url("https://www.meetup.com/foo/events").source_name == "meetup"
    assert get_adapter_for_source_url("https://lu.ma/abc123").source_name == "luma"
    assert (
        get_adapter_for_source_url("https://www.startupgrind.com/events/").source_name
        == "startupgrind"
    )
    assert (
        get_adapter_for_source_url("https://www.techstars.com/events/search").source_name
        == "techstars"
    )
    assert get_adapter_for_source_url("https://example.org/events").source_name == "web_jsonld"


def test_parse_jsonld_events_reads_nested_item_list():
    """Eventbrite nests Event nodes inside ItemList -> ListItem -> item."""
    events = parse_jsonld_events(
        _eventbrite_item_list("Founder Night", "Pitch Practice"),
        EVENTBRITE_LISTING_URL,
        source_name="eventbrite",
    )

    assert [event.name for event in events] == ["Founder Night", "Pitch Practice"]
    assert all(event.source == "eventbrite" for event in events)
    # eventAttendanceMode marks these as online even without a named location.
    assert all(event.is_virtual for event in events)


async def test_eventbrite_adapter_paginates_listing_pages():
    adapter = EventbriteAdapter()
    # Page 3 repeats page 2, which should stop pagination without duplicates.
    bodies_by_page = {
        None: _eventbrite_item_list("Page One Event"),
        "2": _eventbrite_item_list("Page Two Event"),
        "3": _eventbrite_item_list("Page Two Event"),
    }

    def _respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=bodies_by_page[request.url.params.get("page")])

    with respx.mock:
        route = respx.get(host="www.eventbrite.com").mock(side_effect=_respond)

        async with httpx.AsyncClient() as client:
            events = await adapter.discover(client, _settings(), EVENTBRITE_LISTING_URL)

    assert [event.name for event in events] == ["Page One Event", "Page Two Event"]
    # Stops after the repeated page rather than exhausting max_pages blindly.
    assert route.call_count == 3
    assert [call.request.url.params.get("page") for call in route.calls] == [None, "2", "3"]


def test_all_day_event_today_is_still_active():
    """A date-only endDate must not expire an event on the morning it happens."""
    today = datetime.now(UTC).date().isoformat()
    events = parse_jsonld_events(
        f"""
        <script type="application/ld+json">
          {{"@type":"Event","name":"All Day Founder Workshop",
            "startDate":"{today}","endDate":"{today}",
            "url":"https://www.eventbrite.com/e/all-day"}}
        </script>
        """,
        EVENTBRITE_LISTING_URL,
        source_name="eventbrite",
    )

    assert len(events) == 1
    assert events[0].status == "active"


async def test_eventbrite_adapter_does_not_paginate_single_event_page():
    adapter = EventbriteAdapter()
    single_event_url = "https://www.eventbrite.com/e/founder-night-tickets-123"
    with respx.mock:
        route = respx.get(single_event_url).mock(
            return_value=httpx.Response(
                200, text=_event_jsonld("Founder Night", single_event_url)
            )
        )

        async with httpx.AsyncClient() as client:
            events = await adapter.discover(client, _settings(), single_event_url)

    assert route.call_count == 1
    assert [event.name for event in events] == ["Founder Night"]


async def test_discover_events_uses_provider_source_name():
    settings = _settings(
        EVENTS_SOURCE_URLS="https://www.eventbrite.com/e/foo,https://example.org/events/bar"
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
        respx.get("https://example.org/events/bar").mock(
            return_value=httpx.Response(
                200,
                text=_event_jsonld(
                    "Community Builder Meetup",
                    "https://example.org/events/bar",
                ),
            )
        )

        events = await discover_events_from_web(settings)

    assert len(events) == 2
    by_name = {event.name: event for event in events}
    assert by_name["Eventbrite Founder Night"].source == "eventbrite"
    assert by_name["Community Builder Meetup"].source == "web_jsonld"


async def test_discover_events_skips_failing_source():
    """One broken source must not abort the whole sweep."""
    settings = _settings(
        EVENTS_SOURCE_URLS="https://example.org/broken,https://example.org/ok"
    )
    with respx.mock:
        respx.get("https://example.org/broken").mock(return_value=httpx.Response(500))
        respx.get("https://example.org/ok").mock(
            return_value=httpx.Response(
                200, text=_event_jsonld("Working Event", "https://example.org/ok")
            )
        )

        events = await discover_events_from_web(settings)

    assert [event.name for event in events] == ["Working Event"]
