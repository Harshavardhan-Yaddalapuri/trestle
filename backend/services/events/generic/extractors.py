"""Deterministic generic extractors for feeds, calendars, JSON-LD and HTML."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urljoin

import feedparser
import httpx
from bs4 import BeautifulSoup
from icalendar import Calendar

from backend.services.events.parser import parse_jsonld_events
from backend.services.events.taxonomy import normalize_text, parse_iso_datetime
from backend.services.events.generic.types import ExtractedEvent, ExtractionBatch

_MAX_HTML_CHARS = 24_000


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def extract_jsonld(content: str, source_url: str) -> ExtractionBatch:
    records = parse_jsonld_events(content, source_url, source_name="generic_jsonld")
    events = [
        ExtractedEvent(
            name=record.name, description=record.description, starts_at=record.starts_at,
            ends_at=record.ends_at, timezone=record.timezone, venue=record.location_text,
            city=record.city, region=record.region, country=record.country,
            is_virtual=record.is_virtual, registration_url=record.url, organizer=record.host_name,
            price_usd_cents=record.cost_usd_cents, industry_tags=record.industry_tags,
            stage_tags=record.stage_tags, benefit_tags=record.benefit_tags,
            attendee_types=record.attendee_types, source_identifier=record.source_id,
            field_confidences={"name": .99, "starts_at": .99, "registration_url": .95},
            evidence={"name": "schema.org Event.name", "starts_at": "schema.org Event.startDate"},
            raw_payload=record.source_payload,
        )
        for record in records
    ]
    return ExtractionBatch(method="jsonld", events=events)


def extract_ics(content: str, source_url: str) -> ExtractionBatch:
    calendar = Calendar.from_ical(content)
    events: list[ExtractedEvent] = []
    for component in calendar.walk("VEVENT"):
        start = _ical_datetime(component.get("dtstart"))
        if start is None:
            continue
        end = _ical_datetime(component.get("dtend"))
        location = normalize_text(component.get("location"))
        url = normalize_text(component.get("url")) or source_url
        events.append(ExtractedEvent(
            name=normalize_text(component.get("summary")), description=normalize_text(component.get("description")),
            starts_at=start, ends_at=end, venue=location or None, registration_url=url,
            organizer=normalize_text(component.get("organizer")) or None,
            source_identifier=normalize_text(component.get("uid")) or None,
            field_confidences={"name": .99, "starts_at": .99, "registration_url": .9},
            evidence={"name": "iCalendar SUMMARY", "starts_at": "iCalendar DTSTART"},
            raw_payload={"uid": normalize_text(component.get("uid")), "location": location},
        ))
    return ExtractionBatch(method="ics", events=events)


def extract_rss(content: str, source_url: str) -> ExtractionBatch:
    feed = feedparser.parse(content)
    events: list[ExtractedEvent] = []
    for entry in feed.entries:
        date = _feed_datetime(entry)
        if date is None:
            continue
        title = normalize_text(entry.get("title"))
        if not title:
            continue
        link = normalize_text(entry.get("link")) or source_url
        events.append(ExtractedEvent(
            name=title, description=normalize_text(entry.get("summary") or entry.get("description")),
            starts_at=date, registration_url=link, source_identifier=normalize_text(entry.get("id")) or link,
            field_confidences={"name": .85, "starts_at": .7, "registration_url": .9},
            evidence={"name": "RSS entry.title", "starts_at": "RSS published/updated"},
            raw_payload={"id": entry.get("id"), "published": entry.get("published"), "updated": entry.get("updated")},
        ))
    return ExtractionBatch(method="rss", events=events, diagnostics={"bozo": bool(feed.bozo)})


def find_feeds_and_calendar(content: str, source_url: str) -> list[str]:
    soup = BeautifulSoup(content, "html.parser")
    links: list[str] = []
    for tag in soup.select("link[rel='alternate'], link[type='text/calendar'], a[href$='.ics']"):
        href = tag.get("href")
        type_ = (tag.get("type") or "").lower()
        if href and (type_ in {"application/rss+xml", "application/atom+xml", "text/calendar"} or href.endswith(".ics")):
            links.append(urljoin(source_url, href))
    return list(dict.fromkeys(links))


def extract_readable_html(content: str) -> str:
    """Reduce an HTML page to bounded, prompt-safe text for LLM extraction."""
    soup = BeautifulSoup(content, "html.parser")
    for element in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
        element.decompose()
    text = " ".join(soup.stripped_strings)
    return text[:_MAX_HTML_CHARS]


async def render_page(url: str, timeout_ms: int) -> str:
    """Render an intentionally requested JS-heavy source with Playwright."""
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            return await page.content()
        finally:
            await browser.close()


async def fetch(client: httpx.AsyncClient, url: str) -> httpx.Response:
    response = await client.get(url)
    response.raise_for_status()
    return response


def _ical_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    raw = value.dt
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=UTC) if raw.tzinfo is None else raw.astimezone(UTC)
    return datetime.combine(raw, datetime.min.time(), tzinfo=UTC) if raw else None


def _feed_datetime(entry: Any) -> datetime | None:
    raw = entry.get("published") or entry.get("updated")
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return parse_iso_datetime(raw)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
