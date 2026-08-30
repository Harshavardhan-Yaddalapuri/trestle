from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from backend.core.config import Settings
from backend.core.errors import ConflictError
from backend.db.models.event import Event
from backend.db.models.profile import Profile
from backend.schemas.event import EventMatchRequest
from backend.services.events.discovery import upsert_discovered_events
from backend.services.events.location_normalization import (
    event_is_in_country,
    event_is_in_state,
    normalize_country,
    normalize_us_state,
)
from backend.services.events.matching import evaluate_event, resolve_event_profile
from backend.services.events.orchestration import run_events_discovery_sweep
from backend.services.events.parser import parse_jsonld_events


def _settings(**overrides) -> Settings:
    base = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/0",
        EVENTS_ENABLED=True,
        EVENTS_SOURCE_URLS="https://x.test/events",
        EVENTS_HTTP_TIMEOUT_SECONDS=10.0,
        EVENTS_DISCOVERY_INTERVAL_HOURS=12,
        EVENTS_REDIS_LOCK_TTL_SECONDS=60,
    )
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


def test_parse_jsonld_events_parses_basic_fields():
    html = """
    <html>
      <body>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Event",
          "name": "Boston Climate Founder Meetup",
          "description": "Network with climate founders and seed investors.",
          "startDate": "2026-08-11T18:00:00-04:00",
          "endDate": "2026-08-11T20:00:00-04:00",
          "url": "https://example.org/events/climate-meetup",
          "organizer": {"@type": "Organization", "name": "Techstars Boston"},
          "location": {
            "@type": "Place",
            "name": "Kendall Square",
            "address": {
              "@type": "PostalAddress",
              "addressLocality": "Boston",
              "addressRegion": "MA",
              "addressCountry": "US"
            }
          }
        }
        </script>
      </body>
    </html>
    """

    events = parse_jsonld_events(html, "https://example.org/events")
    assert len(events) == 1
    event = events[0]
    assert event.name == "Boston Climate Founder Meetup"
    assert event.host_name == "Techstars Boston"
    assert event.city == "Boston"
    assert event.country == "US"
    assert "climate" in event.industry_tags
    assert "investor_access" in event.benefit_tags
    assert event.host_quality_score > 0.8


async def test_upsert_discovered_events_inserts_and_updates(session_factory):
    now = datetime.now(UTC)
    base = parse_jsonld_events(
        """
        <script type="application/ld+json">
          {"@type":"Event","name":"Founder Mixer","startDate":"2026-09-01T10:00:00Z","url":"https://x.test/event/1"}
        </script>
        """,
        "https://x.test/events",
    )
    assert len(base) == 1

    async with session_factory() as s:
        inserted, updated = await upsert_discovered_events(s, base, now)
    assert inserted == 1
    assert updated == 0

    changed = list(base)
    changed[0].description = "Updated description"
    async with session_factory() as s:
        inserted2, updated2 = await upsert_discovered_events(s, changed, now)
    assert inserted2 == 0
    assert updated2 == 1


def test_match_events_uses_profile_context():
    now = datetime.now(UTC)
    profile = Profile(
        session_id="events-session-1",
        company_stage="seed",
        industry=["climate"],
        location="boston",
        goals="raise seed, hire first engineer",
    )
    strong = Event(
        id=uuid.uuid4(),
        source_id="event:strong",
        source="web_jsonld",
        source_payload={},
        name="Boston Climate Investor Night",
        description="Meet seed investors and climate founders.",
        url="https://example.org/strong",
        host_name="Techstars Boston",
        starts_at=now + timedelta(days=7),
        ends_at=now + timedelta(days=7, hours=2),
        is_virtual=False,
        city="Boston",
        country="US",
        industry_tags=["climate"],
        stage_tags=["seed"],
        benefit_tags=["investor_access", "networking"],
        attendee_types=["founders", "investors"],
        application_required=False,
        host_quality_score=0.9,
        status="active",
    )
    weak = Event(
        id=uuid.uuid4(),
        source_id="event:weak",
        source="web_jsonld",
        source_payload={},
        name="Generic Remote Workshop",
        description="General workshop.",
        url="https://example.org/weak",
        starts_at=now + timedelta(days=5),
        is_virtual=True,
        industry_tags=["fintech"],
        stage_tags=["series_a"],
        benefit_tags=["customer_discovery"],
        application_required=False,
        host_quality_score=0.4,
        status="active",
    )
    match_profile = resolve_event_profile(profile, EventMatchRequest())
    strong_result = evaluate_event(match_profile, strong, include_virtual=True)
    weak_result = evaluate_event(match_profile, weak, include_virtual=True)
    assert strong_result.score > weak_result.score
    assert "industry" in strong_result.matched_on
    assert "outcome" in strong_result.matched_on


def test_event_location_matches_city_from_city_state_profile():
    """A profile's display location should match separately stored event city data."""
    profile = Profile(
        session_id="events-session-detroit",
        company_stage="seed",
        industry=["ai"],
        location="Detroit, MI",
        goals="networking",
    )
    event = Event(
        id=uuid.uuid4(),
        source_id="event:detroit",
        source="web_jsonld",
        source_payload={},
        name="Detroit Founder Meetup",
        description="Meet local startup founders.",
        url="https://example.org/detroit",
        starts_at=datetime.now(UTC) + timedelta(days=7),
        is_virtual=False,
        city="Detroit",
        region="Michigan",
        industry_tags=["ai"],
        stage_tags=["seed"],
        benefit_tags=["networking"],
        status="active",
    )

    result = evaluate_event(
        resolve_event_profile(profile, EventMatchRequest()),
        event,
        include_virtual=True,
    )

    assert "distance" in result.matched_on


@pytest.mark.parametrize(
    ("raw_country", "expected"),
    [
        ("US", "US"),
        ("USA", "US"),
        ("United States of America", "US"),
        ("United Kingdom", "GB"),
    ],
)
def test_normalize_country_accepts_codes_and_names(raw_country, expected):
    assert normalize_country(raw_country) == expected


@pytest.mark.parametrize(
    ("raw_state", "expected"),
    [("CA", "CA"), ("California", "CA"), ("Michigan", "MI")],
)
def test_normalize_us_state_accepts_codes_and_names(raw_state, expected):
    assert normalize_us_state(raw_state) == expected


def test_event_location_scope_matches_full_country_and_state_names():
    event = Event(
        id=uuid.uuid4(),
        source_id="event:california",
        source="web_jsonld",
        source_payload={},
        name="California Founder Meetup",
        description="Meet local startup founders.",
        url="https://example.org/california",
        starts_at=datetime.now(UTC) + timedelta(days=7),
        is_virtual=False,
        city="San Francisco",
        region="California",
        country="United States of America",
        status="active",
    )

    assert event_is_in_country(event, "US")
    assert event_is_in_state(event, "CA", "US")


async def test_events_discovery_sweep_happy_path(session_factory, redis_client, monkeypatch):
    discovered = parse_jsonld_events(
        """
        <script type="application/ld+json">
          {"@type":"Event","name":"Founder Mixer","startDate":"2026-09-01T10:00:00Z","url":"https://x.test/event/1"}
        </script>
        """,
        "https://x.test/events",
    )

    async def _fake_discover(settings):
        return discovered

    async def _fake_upsert(session, records, fetched_at):
        assert len(records) == len(discovered)
        return len(records), 0

    monkeypatch.setattr(
        "backend.services.events.orchestration.discover_events_from_web",
        _fake_discover,
    )
    monkeypatch.setattr(
        "backend.services.events.orchestration.upsert_discovered_events",
        _fake_upsert,
    )

    result = await run_events_discovery_sweep(
        session_factory=session_factory,
        redis=redis_client,
        settings=_settings(),
        triggered_by="schedule",
    )
    assert result is not None
    assert result.discovered == 1
    assert result.inserted == 1
    assert result.updated == 0
    assert result.sources_scanned == 1
    assert await redis_client.get("events:discover:lock") is None


async def test_events_discovery_sweep_manual_conflict(session_factory, redis_client):
    settings = _settings()
    await redis_client.set("events:discover:lock", "existing-run", nx=True, ex=60)

    with pytest.raises(ConflictError) as exc_info:
        await run_events_discovery_sweep(
            session_factory=session_factory,
            redis=redis_client,
            settings=settings,
            triggered_by="manual",
        )
    assert exc_info.value.code == "events_discovery_in_progress"
