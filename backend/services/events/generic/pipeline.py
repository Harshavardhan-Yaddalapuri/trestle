"""Generic event source pipeline with review-first persistence.

Known provider adapters remain authoritative. Unknown URLs progress through
feed/calendar, JSON-LD, static-page LLM, and browser-rendered LLM strategies.
Only high-confidence, validated candidates are inserted automatically.
"""
from __future__ import annotations

import uuid
import ipaddress
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import Settings
from backend.db.models.event import Event
from backend.db.models.event_ingestion import EventCandidate, EventDiscoveryRun, EventProvenance
from backend.services.events.adapters.registry import get_custom_adapter_for_source_url
from backend.services.events.discovery import upsert_discovered_events
from backend.services.events.generic.extractors import (
    content_hash, extract_ics, extract_jsonld, extract_readable_html, extract_rss,
    fetch, find_feeds_and_calendar, render_page,
)
from backend.services.events.generic.llm import extract_with_llm
from backend.services.events.generic.types import ExtractedEvent, ExtractionBatch
from backend.services.events.generic.validation import validate
from backend.services.events.parser import DiscoveredEvent
from backend.services.events.taxonomy import host_quality_score, normalize_text
from backend.services.llm.base import LLMClient


class GenericEventPipeline:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], settings: Settings, llm: LLMClient | None = None) -> None:
        self._sessions = session_factory
        self._settings = settings
        self._llm = llm

    async def discover(self, source_url: str, *, triggered_by: str = "manual", allow_browser: bool = False) -> EventDiscoveryRun:
        run = EventDiscoveryRun(id=uuid.uuid4(), source_url=source_url, triggered_by=triggered_by)
        async with self._sessions() as session:
            session.add(run)
            await session.commit()
        try:
            _validate_source_url(source_url)
            batches = await self._extract(source_url, allow_browser=allow_browser)
            run.strategy = ",".join(batch.method for batch in batches)
            run.diagnostics = {"strategies": [batch.model_dump(exclude={"events"}) for batch in batches]}
            for batch in batches:
                for extracted in batch.events:
                    run.records_found += 1
                    await self._persist_candidate(run, source_url, batch, extracted)
        except Exception as exc:
            run.error = str(exc)[:500]
        finally:
            run.finished_at = datetime.now(UTC)
            async with self._sessions() as session:
                existing = await session.get(EventDiscoveryRun, run.id)
                if existing:
                    for field in ("strategy", "diagnostics", "records_found", "records_accepted", "records_pending_review", "records_rejected", "records_duplicates", "error", "finished_at"):
                        setattr(existing, field, getattr(run, field))
                    await session.commit()
        return run

    async def _extract(self, source_url: str, *, allow_browser: bool) -> list[ExtractionBatch]:
        import httpx
        async with httpx.AsyncClient(headers={"User-Agent": self._settings.INGEST_USER_AGENT}, timeout=self._settings.EVENTS_HTTP_TIMEOUT_SECONDS, follow_redirects=True) as client:
            custom = get_custom_adapter_for_source_url(source_url)
            if custom:
                records = await custom.discover(client, self._settings, source_url)
                return [ExtractionBatch(method="custom_adapter", events=[_from_discovered(record) for record in records])]
            response = await fetch(client, source_url)
            content = response.text
            media_type = response.headers.get("content-type", "").lower()
            if "calendar" in media_type or source_url.lower().endswith(".ics"):
                return [extract_ics(content, source_url)]
            if "rss" in media_type or "atom" in media_type or source_url.lower().endswith((".rss", ".atom", ".xml")):
                return [extract_rss(content, source_url)]
            batches = [extract_jsonld(content, source_url)]
            for feed_url in find_feeds_and_calendar(content, source_url):
                feed_response = await fetch(client, feed_url)
                if "calendar" in feed_response.headers.get("content-type", "").lower() or feed_url.endswith(".ics"):
                    batches.append(extract_ics(feed_response.text, feed_url))
                else:
                    batches.append(extract_rss(feed_response.text, feed_url))
            # RSS publication dates are only review-level evidence. Do not let
            # a linked news feed suppress static-page event extraction.
            if any(batch.events and batch.method in {"ics", "jsonld"} for batch in batches):
                return batches
            page_text = extract_readable_html(content)
            if self._llm:
                batches.append(await extract_with_llm(self._llm, page_text, source_url))
            if not any(batch.events for batch in batches) and allow_browser:
                rendered = await render_page(source_url, int(self._settings.EVENTS_HTTP_TIMEOUT_SECONDS * 1000))
                browser_jsonld = extract_jsonld(rendered, source_url)
                browser_jsonld.method = "browser"
                batches.append(browser_jsonld)
                if not browser_jsonld.events and self._llm:
                    batches.append(await extract_with_llm(self._llm, extract_readable_html(rendered), source_url))
            return batches

    async def _persist_candidate(self, run: EventDiscoveryRun, source_url: str, batch: ExtractionBatch, extracted: ExtractedEvent) -> None:
        verdict = validate(extracted, extraction_method=batch.method)
        candidate = EventCandidate(
            run_id=run.id, source_url=source_url, source_identifier=extracted.source_identifier,
            extraction_method=batch.method, normalized_data=extracted.model_dump(mode="json", exclude={"field_confidences", "evidence", "raw_payload"}),
            field_confidences=extracted.field_confidences, evidence=extracted.evidence, raw_payload=extracted.raw_payload,
            content_hash=content_hash(str(extracted.raw_payload)), review_status=verdict.status, validation_errors=verdict.errors,
        )
        async with self._sessions() as session:
            duplicate = await _find_duplicate(session, extracted)
            if duplicate:
                candidate.review_status = "duplicate"
                candidate.duplicate_event_id = duplicate.id
                run.records_duplicates += 1
                session.add(candidate)
                await session.flush()
                await _upsert_provenance(session, duplicate.id, candidate, extracted)
            elif verdict.status == "accepted":
                event = _to_discovered(extracted, source_url, batch.method)
                inserted, updated = await upsert_discovered_events(session, [event], datetime.now(UTC))
                record = (await session.execute(sa.select(Event).where(Event.source_id == event.source_id))).scalar_one()
                candidate.review_status = "accepted"
                run.records_accepted += 1
                session.add(candidate)
                await session.flush()
                await _upsert_provenance(session, record.id, candidate, extracted)
            elif verdict.status == "pending_review":
                run.records_pending_review += 1
                session.add(candidate)
            else:
                run.records_rejected += 1
                session.add(candidate)
            await session.commit()


def _from_discovered(event: DiscoveredEvent) -> ExtractedEvent:
    return ExtractedEvent(name=event.name, description=event.description, starts_at=event.starts_at, ends_at=event.ends_at, timezone=event.timezone, venue=event.location_text, city=event.city, region=event.region, country=event.country, is_virtual=event.is_virtual, registration_url=event.url, organizer=event.host_name, price_usd_cents=event.cost_usd_cents, industry_tags=event.industry_tags, stage_tags=event.stage_tags, benefit_tags=event.benefit_tags, attendee_types=event.attendee_types, source_identifier=event.source_id, source_name=event.source, field_confidences={"name": .99, "starts_at": .99, "registration_url": .95}, raw_payload=event.source_payload)


def _to_discovered(item: ExtractedEvent, source_url: str, method: str) -> DiscoveredEvent:
    assert item.name and item.starts_at
    stable = f"{source_url}|{item.source_identifier or ''}|{item.name}|{item.starts_at.isoformat()}"
    source_id = item.source_identifier or f"generic:{uuid.uuid5(uuid.NAMESPACE_URL, stable)}"
    return DiscoveredEvent(source=item.source_name or f"generic_{method}", source_id=source_id, name=item.name, description=item.description, url=item.registration_url or source_url, host_name=item.organizer, starts_at=item.starts_at, ends_at=item.ends_at, timezone=item.timezone, is_virtual=bool(item.is_virtual), location_text=item.venue or item.address, city=item.city, region=item.region, country=item.country, industry_tags=item.industry_tags, stage_tags=item.stage_tags, benefit_tags=item.benefit_tags, attendee_types=item.attendee_types, cost_usd_cents=item.price_usd_cents, host_quality_score=host_quality_score(item.organizer), source_payload=item.raw_payload)


async def _find_duplicate(session: AsyncSession, item: ExtractedEvent) -> Event | None:
    if not item.name or not item.starts_at:
        return None
    start = item.starts_at - timedelta(hours=24)
    end = item.starts_at + timedelta(hours=24)
    rows = (await session.execute(sa.select(Event).where(Event.starts_at.between(start, end)))).scalars()
    normalized_name = normalize_text(item.name).lower()
    target_url = (item.registration_url or "").rstrip("/").lower()
    for event in rows:
        same_name = normalize_text(event.name).lower() == normalized_name
        same_url = target_url and event.url.rstrip("/").lower() == target_url
        same_organizer = item.organizer and event.host_name and normalize_text(item.organizer).lower() == normalize_text(event.host_name).lower()
        same_place = item.city and event.city and item.city.lower() == event.city.lower()
        if same_url or (same_name and (same_organizer or same_place)):
            return event
    return None


async def _upsert_provenance(session: AsyncSession, event_id: uuid.UUID, candidate: EventCandidate, item: ExtractedEvent) -> None:
    existing = (await session.execute(sa.select(EventProvenance).where(EventProvenance.event_id == event_id, EventProvenance.source_url == candidate.source_url, EventProvenance.source_identifier == candidate.source_identifier))).scalar_one_or_none()
    if existing:
        existing.last_verified_at = datetime.now(UTC)
        existing.field_confidences = item.field_confidences
        return
    session.add(EventProvenance(event_id=event_id, candidate_id=candidate.id, source_url=candidate.source_url, source_identifier=candidate.source_identifier, extraction_method=candidate.extraction_method, field_confidences=item.field_confidences, evidence=item.evidence, raw_payload=item.raw_payload, content_hash=candidate.content_hash))


def _validate_source_url(source_url: str) -> None:
    """Reject obvious SSRF targets before an arbitrary URL reaches a fetcher."""
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("source_url must be an absolute http(s) URL without credentials")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return
    if not address.is_global:
        raise ValueError("source_url must not target a private or reserved IP address")
