from __future__ import annotations

import httpx
import pytest
import respx

from backend.core.config import Settings
from backend.services.events.adapters.techstars import TechstarsAdapter
from backend.services.events.location import parse_location_label

SOURCE_URL = "https://www.techstars.com/events/search"
CONFIG_URL = "https://www.techstars.com/api/search/config/events"
TYPESENSE_URL = "https://search.typesense.test"
SEARCH_URL = f"{TYPESENSE_URL}/collections/events/documents/search"

SEARCH_CONFIG = {
    "url": TYPESENSE_URL,
    "collection": "events",
    "apiKey": "search-only-key",
}


def _settings(**overrides) -> Settings:
    base = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/0",
        EVENTS_ENABLED=True,
        EVENTS_SOURCE_URLS=SOURCE_URL,
        EVENTS_HTTP_TIMEOUT_SECONDS=10.0,
    )
    for key, value in overrides.items():
        object.__setattr__(base, key, value)
    return base


def _document(**overrides) -> dict:
    document = {
        "id": "9de91933-da7d-446e-95cc-046dc4e413e6",
        "title": "Techstars Startup Weekend Panambi",
        "event_start": "2099-12-04T00:00:00.000Z",
        "event_end": "2099-12-07T00:00:00.000Z",
        "event_start_epoch": 4102444800,
        "event_type": "Startup Weekend",
        "location": "Panambi, Brazil",
        "location_type": "In Person",
        "website": "https://startupweekendpanambi.com",
    }
    document.update(overrides)
    return document


def _search_response(documents: list[dict], found: int | None = None) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "found": found if found is not None else len(documents),
            "hits": [{"document": document} for document in documents],
        },
    )


async def _discover(documents_by_page: list[list[dict]], **settings_overrides):
    adapter = TechstarsAdapter()
    total = sum(len(page) for page in documents_by_page)
    with respx.mock:
        respx.get(CONFIG_URL).mock(return_value=httpx.Response(200, json=SEARCH_CONFIG))
        respx.get(SEARCH_URL).mock(
            side_effect=[_search_response(page, found=total) for page in documents_by_page]
            + [_search_response([], found=total)]
        )
        async with httpx.AsyncClient() as client:
            return await adapter.discover(client, _settings(**settings_overrides), SOURCE_URL)


def test_adapter_supports_techstars_urls_only():
    adapter = TechstarsAdapter()
    assert adapter.supports(SOURCE_URL)
    assert adapter.supports("https://techstars.com/events")
    assert not adapter.supports("https://www.eventbrite.com/d/online/startup/")


async def test_discover_maps_typesense_document_to_event():
    events = await _discover([[_document()]])

    assert len(events) == 1
    event = events[0]
    assert event.source == "techstars"
    assert event.source_id == "techstars:9de91933-da7d-446e-95cc-046dc4e413e6"
    assert event.name == "Techstars Startup Weekend Panambi"
    assert event.url == "https://startupweekendpanambi.com"
    assert event.host_name == "Techstars"
    assert event.starts_at.year == 2099
    assert event.ends_at is not None
    assert event.city == "Panambi"
    assert event.country == "Brazil"
    assert event.region is None
    assert event.is_virtual is False
    assert event.status == "active"
    # Techstars is a known high-quality host.
    assert event.host_quality_score > 0.8
    # Startup Weekend implies networking and pitching to judges.
    assert "networking" in event.benefit_tags
    assert "investor_access" in event.benefit_tags
    assert "founders" in event.attendee_types
    assert event.source_payload["event_type"] == "Startup Weekend"


async def test_discover_sends_search_only_key_and_upcoming_filter():
    adapter = TechstarsAdapter()
    with respx.mock:
        respx.get(CONFIG_URL).mock(return_value=httpx.Response(200, json=SEARCH_CONFIG))
        route = respx.get(SEARCH_URL).mock(
            side_effect=[_search_response([_document()]), _search_response([])]
        )
        async with httpx.AsyncClient() as client:
            await adapter.discover(client, _settings(), SOURCE_URL)

    request = route.calls[0].request
    assert request.headers["X-TYPESENSE-API-KEY"] == "search-only-key"
    assert request.url.params["sort_by"] == "event_start_epoch:asc"
    assert request.url.params["filter_by"].startswith("event_start_epoch:>=")


async def test_discover_paginates_until_all_documents_seen():
    page_one = [_document(id=f"id-{index}") for index in range(2)]
    page_two = [_document(id="id-2")]

    events = await _discover([page_one, page_two])

    assert [event.source_id for event in events] == [
        "techstars:id-0",
        "techstars:id-1",
        "techstars:id-2",
    ]


async def test_discover_marks_online_events_virtual():
    events = await _discover(
        [[_document(location="Virtual", location_type="Online", website=None)]]
    )

    event = events[0]
    assert event.is_virtual is True
    assert event.city is None
    # Without an organiser website we fall back to the Techstars calendar.
    assert event.url == "https://www.techstars.com/events/search"


async def test_discover_derives_industry_tags_from_verticals():
    events = await _discover(
        [
            [
                _document(
                    title="Founder Workshop",
                    event_type="Founder Workshops & Panels",
                    industry_vertical=["Climate Tech", "Healthtech"],
                )
            ]
        ]
    )

    assert set(events[0].industry_tags) >= {"climate", "healthcare"}


async def test_discover_normalizes_website_missing_scheme():
    events = await _discover([[_document(website="www.startupweekendtoronto.com")]])

    assert events[0].url == "https://www.startupweekendtoronto.com"


async def test_discover_skips_documents_without_title_or_start():
    events = await _discover(
        [
            [
                _document(id="no-title", title=""),
                _document(id="no-start", event_start=None, event_start_epoch=None),
                _document(id="valid"),
            ]
        ]
    )

    assert [event.source_id for event in events] == ["techstars:valid"]


async def test_discover_raises_when_config_missing_credentials():
    adapter = TechstarsAdapter()
    with respx.mock:
        respx.get(CONFIG_URL).mock(
            return_value=httpx.Response(200, json={"collection": "events"})
        )
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="missing url or apiKey"):
                await adapter.discover(client, _settings(), SOURCE_URL)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Panambi, Brazil", {"city": "Panambi", "region": None, "country": "Brazil"}),
        ("Iowa City, IA", {"city": "Iowa City", "region": "IA", "country": None}),
        (
            "Austin, Texas, USA",
            {"city": "Austin", "region": "Texas", "country": "USA"},
        ),
        ("Boulder", {"city": "Boulder", "region": None, "country": None}),
    ],
)
def test_parse_location_label_splits_city_region_country(label, expected):
    parsed = parse_location_label(label)
    assert parsed.is_virtual is False
    assert parsed.city == expected["city"]
    assert parsed.region == expected["region"]
    assert parsed.country == expected["country"]


@pytest.mark.parametrize("label", ["Virtual", "online", "Remote", " Global "])
def test_parse_location_label_detects_virtual(label):
    parsed = parse_location_label(label)
    assert parsed.is_virtual is True
    assert parsed.city is None


def test_parse_location_label_handles_empty():
    parsed = parse_location_label(None)
    assert parsed.is_virtual is False
    assert parsed.text is None
