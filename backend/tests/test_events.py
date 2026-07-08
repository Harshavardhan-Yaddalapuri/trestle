from __future__ import annotations

from datetime import UTC, datetime, timedelta

import sqlalchemy as sa

from backend.db.models.event import Event
from backend.db.models.profile import Profile
from backend.services.events.discovery import _extract_jsonld_events, upsert_discovered_events


def test_extract_jsonld_events_parses_basic_fields():
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

    events = _extract_jsonld_events(html, "https://example.org/events")
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
    base = _extract_jsonld_events(
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


async def test_match_events_uses_profile_context(client, session_factory):
    session_id = "events-session-1"
    now = datetime.now(UTC)

    async with session_factory() as s:
        s.add(
            Profile(
                session_id=session_id,
                company_stage="seed",
                industry=["climate"],
                location="boston",
                goals="raise seed, hire first engineer",
            )
        )
        s.add(
            Event(
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
                host_quality_score=0.9,
                status="active",
            )
        )
        s.add(
            Event(
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
                host_quality_score=0.4,
                status="active",
            )
        )
        await s.commit()

    res = await client.post(
        "/api/events/match",
        headers={"X-Session-Id": session_id},
        json={"limit": 5, "min_score": 0.0},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total_returned"] == 2
    assert body["results"][0]["event"]["source_id"] == "event:strong"
    assert body["results"][0]["score"] >= body["results"][1]["score"]

    async with session_factory() as s:
        count = (
            await s.execute(sa.select(sa.func.count()).select_from(Event))
        ).scalar_one()
    assert count == 2
