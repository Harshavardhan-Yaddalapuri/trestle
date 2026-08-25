from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx
import sqlalchemy as sa

from backend.core.config import Settings
from backend.db.models.event import Event
from backend.db.models.event_ingestion import EventCandidate, EventDiscoveryRun, EventProvenance
from backend.services.events.generic.pipeline import GenericEventPipeline
from backend.services.llm.types import LLMResponse


def _settings() -> Settings:
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/0",
        EVENTS_ENABLED=True,
        EVENTS_HTTP_TIMEOUT_SECONDS=10,
    )


def _jsonld(name: str = "Founder Meetup") -> str:
    return f"""<script type="application/ld+json">{{
      "@type":"Event","name":"{name}","startDate":"2030-09-01T18:00:00Z",
      "url":"https://events.example.test/register","organizer":{{"name":"Test Hub"}}
    }}</script>"""


async def test_jsonld_candidate_is_accepted_persisted_and_provenanced(session_factory):
    with respx.mock:
        respx.get("https://example.test/events").mock(return_value=httpx.Response(200, text=_jsonld()))
        run = await GenericEventPipeline(session_factory, _settings()).discover("https://example.test/events")

    assert run.error is None
    assert run.strategy == "jsonld"
    assert (run.records_found, run.records_accepted, run.records_pending_review) == (1, 1, 0), run.__dict__
    async with session_factory() as session:
        candidate = (await session.execute(sa.select(EventCandidate))).scalar_one()
        event = (await session.execute(sa.select(Event))).scalar_one()
        provenance = (await session.execute(sa.select(EventProvenance))).scalar_one()
    assert candidate.review_status == "accepted"
    assert event.name == "Founder Meetup"
    assert provenance.event_id == event.id
    assert provenance.extraction_method == "jsonld"
    assert provenance.last_verified_at is not None


async def test_same_registration_url_is_recorded_as_cross_source_duplicate(session_factory):
    with respx.mock:
        respx.get("https://example.test/one").mock(return_value=httpx.Response(200, text=_jsonld("Founders")))
        respx.get("https://other.test/two").mock(return_value=httpx.Response(200, text=_jsonld("Different listing")))
        pipeline = GenericEventPipeline(session_factory, _settings())
        first = await pipeline.discover("https://example.test/one")
        second = await pipeline.discover("https://other.test/two")

    assert first.records_accepted == 1
    assert second.records_duplicates == 1
    async with session_factory() as session:
        assert len((await session.execute(sa.select(Event))).scalars().all()) == 1
        duplicate = (await session.execute(sa.select(EventCandidate).where(EventCandidate.review_status == "duplicate"))).scalar_one()
        assert duplicate.duplicate_event_id is not None


class _LowConfidenceLlm:
    async def complete(self, *args, **kwargs):
        return LLMResponse(content="""{"events":[{"name":"Uncertain workshop","starts_at":"2030-09-01T18:00:00Z","field_confidences":{"name":0.6,"starts_at":0.6}}]}""")


async def test_low_confidence_llm_result_stays_in_review_queue(session_factory):
    with respx.mock:
        respx.get("https://plain.test/events").mock(return_value=httpx.Response(200, text="<h1>Events</h1>"))
        run = await GenericEventPipeline(session_factory, _settings(), _LowConfidenceLlm()).discover("https://plain.test/events")

    assert run.records_pending_review == 1
    assert run.records_accepted == 0
    async with session_factory() as session:
        candidate = (await session.execute(sa.select(EventCandidate))).scalar_one()
        assert candidate.review_status == "pending_review"
        assert not (await session.execute(sa.select(Event))).scalars().all()


async def test_invalid_llm_event_is_rejected_not_inserted(session_factory):
    class _BadLlm:
        async def complete(self, *args, **kwargs):
            return LLMResponse(content='{"events":[{"name":"No date","field_confidences":{"name":1}}]}')

    with respx.mock:
        respx.get("https://invalid.test/events").mock(return_value=httpx.Response(200, text="<p>events</p>"))
        run = await GenericEventPipeline(session_factory, _settings(), _BadLlm()).discover("https://invalid.test/events")

    assert run.records_rejected == 1
    async with session_factory() as session:
        candidate = (await session.execute(sa.select(EventCandidate))).scalar_one()
        assert candidate.validation_errors == ["missing_starts_at"]


async def test_ics_is_preferred_over_html(session_factory):
    ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:unit-test-1
DTSTART:20300901T180000Z
DTEND:20300901T190000Z
SUMMARY:Calendar Founder Event
URL:https://calendar.test/register
END:VEVENT
END:VCALENDAR"""
    with respx.mock:
        respx.get("https://calendar.test/events.ics").mock(return_value=httpx.Response(200, text=ics, headers={"content-type": "text/calendar"}))
        run = await GenericEventPipeline(session_factory, _settings()).discover("https://calendar.test/events.ics")

    assert run.strategy == "ics"
    assert run.records_accepted == 1


async def test_rss_requires_review_due_to_weaker_date_confidence(session_factory):
    rss = """<?xml version="1.0"?><rss><channel><item>
    <title>RSS Founder Event</title><link>https://rss.test/event</link>
    <pubDate>Sun, 01 Sep 2030 18:00:00 GMT</pubDate></item></channel></rss>"""
    with respx.mock:
        respx.get("https://rss.test/events.xml").mock(return_value=httpx.Response(200, text=rss, headers={"content-type": "application/rss+xml"}))
        run = await GenericEventPipeline(session_factory, _settings()).discover("https://rss.test/events.xml")

    assert run.strategy == "rss"
    assert run.records_pending_review == 1


async def test_browser_rendering_is_opt_in_and_used_after_static_failure(session_factory, monkeypatch):
    async def _render(url: str, timeout_ms: int) -> str:
        assert url == "https://rendered.test/events"
        return _jsonld("Rendered event")

    monkeypatch.setattr("backend.services.events.generic.pipeline.render_page", _render)
    with respx.mock:
        respx.get("https://rendered.test/events").mock(return_value=httpx.Response(200, text="<div id='app'></div>"))
        run = await GenericEventPipeline(session_factory, _settings()).discover(
            "https://rendered.test/events", allow_browser=True
        )

    assert "browser" in (run.strategy or "")
    assert run.records_accepted == 1
