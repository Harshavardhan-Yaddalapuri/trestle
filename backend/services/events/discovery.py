from __future__ import annotations

import hashlib
import html
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import sqlalchemy as sa
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import get_logger
from backend.db.models.event import Event
from backend.services.events.adapters.registry import get_adapter_for_source_url

logger = get_logger(__name__)

_JSONLD_SCRIPT_RE = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")

_INDUSTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ai": ("ai", "artificial intelligence", "machine learning", "llm"),
    "biotech": ("biotech", "life sciences", "pharma", "wet lab"),
    "climate": ("climate", "cleantech", "decarbonization", "energy transition"),
    "hardware": ("hardware", "manufacturing", "iot", "robotics"),
    "fintech": ("fintech", "payments", "banking", "financial"),
    "healthcare": ("healthcare", "digital health", "medtech"),
}

_STAGE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "idea": ("idea stage", "first-time founder"),
    "pre_seed": ("pre-seed", "pre seed"),
    "seed": ("seed stage", "seed founders", "seed startup"),
    "series_a": ("series a", "growth stage"),
}

_BENEFIT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "networking": ("networking", "mixer", "community"),
    "investor_access": ("investor", "vc", "fundraising", "demo day", "pitch"),
    "hiring": ("hiring", "talent", "recruiting", "job fair"),
    "customer_discovery": ("customer", "go-to-market", "gtm", "sales"),
    "partnerships": ("partnership", "corporate", "business development"),
    "media_visibility": ("media", "press", "pr"),
    "lab_access": ("lab", "wet lab", "research park"),
}

_ATTENDEE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "founders": ("founder", "startup", "entrepreneur"),
    "investors": ("investor", "vc", "angel"),
    "students": ("student", "university"),
    "developers": ("developer", "engineer"),
}

_HIGH_QUALITY_HOST_PATTERNS: tuple[str, ...] = (
    "techstars",
    "ycombinator",
    "startup grind",
    "mit",
    "stanford",
    "berkeley",
    "google for startups",
    "aws startups",
)


class DiscoveredEvent(BaseModel):
    source: str = "web_jsonld"
    source_id: str
    name: str
    description: str = ""
    url: str
    host_name: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    timezone: str | None = None
    is_virtual: bool = False
    location_text: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    industry_tags: list[str] = Field(default_factory=list)
    stage_tags: list[str] = Field(default_factory=list)
    benefit_tags: list[str] = Field(default_factory=list)
    attendee_types: list[str] = Field(default_factory=list)
    cost_usd_cents: int | None = None
    application_required: bool = False
    host_quality_score: float = 0.5
    status: str = "active"
    source_payload: dict[str, Any] = Field(default_factory=dict)


def _normalized_text(value: str | None) -> str:
    if not value:
        return ""
    text = _TAG_RE.sub(" ", value)
    text = html.unescape(text)
    return " ".join(text.split())


def _extract_tags(text: str, mapping: dict[str, tuple[str, ...]]) -> list[str]:
    haystack = text.lower()
    return [tag for tag, phrases in mapping.items() if any(p in haystack for p in phrases)]


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _event_source_id(url: str, starts_at: datetime, name: str) -> str:
    stable = f"{url}|{starts_at.isoformat()}|{name.lower().strip()}"
    digest = hashlib.sha1(stable.encode("utf-8")).hexdigest()  # nosec B324
    return f"event:{digest}"


def _iter_event_nodes(node: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stack = [node]
    while stack:
        cur = stack.pop()
        if isinstance(cur, list):
            stack.extend(cur)
            continue
        if not isinstance(cur, dict):
            continue

        node_type = cur.get("@type")
        if isinstance(node_type, list):
            is_event = any(str(t).lower() == "event" for t in node_type)
        else:
            is_event = str(node_type).lower() == "event"
        if is_event:
            out.append(cur)

        graph = cur.get("@graph")
        if graph is not None:
            stack.append(graph)
    return out


def _parse_location(location_raw: Any) -> tuple[bool, str | None, str | None, str | None, str | None]:
    if location_raw is None:
        return False, None, None, None, None
    if isinstance(location_raw, list):
        for item in location_raw:
            parsed = _parse_location(item)
            if parsed[1] is not None:
                return parsed
        return False, None, None, None, None
    if isinstance(location_raw, str):
        text = _normalized_text(location_raw)
        return False, text or None, None, None, None
    if not isinstance(location_raw, dict):
        return False, None, None, None, None

    location_type = str(location_raw.get("@type") or "").lower()
    if location_type == "virtuallocation":
        name = _normalized_text(str(location_raw.get("name") or "Virtual"))
        return True, name or "Virtual", None, None, None

    name = _normalized_text(location_raw.get("name"))
    address = location_raw.get("address")
    city = region = country = None
    if isinstance(address, dict):
        city = _normalized_text(address.get("addressLocality")) or None
        region = _normalized_text(address.get("addressRegion")) or None
        country = _normalized_text(address.get("addressCountry")) or None
    location_text = ", ".join(v for v in [name, city, region, country] if v) or None
    return False, location_text, city, region, country


def _parse_cost_usd_cents(offers_raw: Any) -> int | None:
    offers = offers_raw[0] if isinstance(offers_raw, list) and offers_raw else offers_raw
    if not isinstance(offers, dict):
        return None
    price = offers.get("price")
    currency = str(offers.get("priceCurrency") or "USD").upper()
    if currency != "USD":
        return None
    if price is None:
        return None
    if isinstance(price, str) and price.strip().lower() in {"free", "0", "$0"}:
        return 0
    try:
        return int(float(str(price).replace("$", "").replace(",", "").strip()) * 100)
    except ValueError:
        return None


def _host_quality_score(host_name: str | None) -> float:
    if not host_name:
        return 0.5
    h = host_name.lower()
    if any(p in h for p in _HIGH_QUALITY_HOST_PATTERNS):
        return 0.85
    return 0.55


def _application_required(description: str) -> bool:
    d = description.lower()
    return any(
        phrase in d
        for phrase in ("application required", "must apply", "apply to attend", "selection process")
    )


def _build_discovered_event(event_node: dict[str, Any], source_url: str) -> DiscoveredEvent | None:
    name = _normalized_text(event_node.get("name"))
    starts_at = _parse_datetime(event_node.get("startDate"))
    if not name or starts_at is None:
        return None

    ends_at = _parse_datetime(event_node.get("endDate"))
    event_url = _normalized_text(event_node.get("url")) or source_url
    description = _normalized_text(event_node.get("description"))

    organizer = event_node.get("organizer")
    host_name = None
    if isinstance(organizer, dict):
        host_name = _normalized_text(organizer.get("name")) or None
    elif isinstance(organizer, list):
        for item in organizer:
            if isinstance(item, dict):
                host_name = _normalized_text(item.get("name")) or host_name

    is_virtual, location_text, city, region, country = _parse_location(event_node.get("location"))

    context_text = " ".join(
        value
        for value in [name, description, host_name or "", location_text or ""]
        if value
    )
    industry_tags = _extract_tags(context_text, _INDUSTRY_KEYWORDS)
    stage_tags = _extract_tags(context_text, _STAGE_KEYWORDS)
    benefit_tags = _extract_tags(context_text, _BENEFIT_KEYWORDS)
    attendee_types = _extract_tags(context_text, _ATTENDEE_KEYWORDS)

    now = datetime.now(UTC)
    status = "expired" if (ends_at or starts_at) < now else "active"

    return DiscoveredEvent(
        source_id=_event_source_id(event_url, starts_at, name),
        name=name,
        description=description,
        url=event_url,
        host_name=host_name,
        starts_at=starts_at,
        ends_at=ends_at,
        timezone=str(event_node.get("eventSchedule")) if event_node.get("eventSchedule") else None,
        is_virtual=is_virtual,
        location_text=location_text,
        city=city,
        region=region,
        country=country,
        industry_tags=industry_tags,
        stage_tags=stage_tags,
        benefit_tags=benefit_tags,
        attendee_types=attendee_types,
        cost_usd_cents=_parse_cost_usd_cents(event_node.get("offers")),
        application_required=_application_required(description),
        host_quality_score=_host_quality_score(host_name),
        status=status,
        source_payload=event_node,
    )


def _extract_jsonld_events(content: str, source_url: str) -> list[DiscoveredEvent]:
    events: list[DiscoveredEvent] = []
    seen_ids: set[str] = set()
    for raw_block in _JSONLD_SCRIPT_RE.findall(content):
        payload = raw_block.strip()
        if not payload:
            continue
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            continue
        for node in _iter_event_nodes(decoded):
            event = _build_discovered_event(node, source_url)
            if event is None or event.source_id in seen_ids:
                continue
            events.append(event)
            seen_ids.add(event.source_id)
    return events


async def discover_events_from_web(settings: Any) -> list[DiscoveredEvent]:
    urls = settings.EVENT_SOURCE_URLS_LIST
    if not urls:
        return []

    discovered: dict[str, DiscoveredEvent] = {}
    async with httpx.AsyncClient(
        headers={"User-Agent": settings.INGEST_USER_AGENT},
        timeout=settings.EVENTS_HTTP_TIMEOUT_SECONDS,
    ) as client:
        for source_url in urls:
            adapter = get_adapter_for_source_url(source_url)
            try:
                events = await adapter.discover(client, settings, source_url)
            except httpx.HTTPError:
                logger.warning(
                    "events_source_fetch_failed",
                    source_url=source_url,
                    adapter=adapter.source_name,
                )
                continue
            except Exception:
                logger.exception(
                    "events_source_adapter_failed",
                    source_url=source_url,
                    adapter=adapter.source_name,
                )
                continue

            logger.info(
                "events_source_scanned",
                source_url=source_url,
                adapter=adapter.source_name,
                discovered=len(events),
            )
            for event in events:
                discovered[event.source_id] = event

    return list(discovered.values())


def _to_db_dict(record: DiscoveredEvent, fetched_at: datetime) -> dict[str, Any]:
    return {
        "source_id": record.source_id,
        "source": record.source,
        "source_payload": record.source_payload,
        "source_fetched_at": fetched_at,
        "name": record.name,
        "description": record.description,
        "url": record.url,
        "host_name": record.host_name,
        "starts_at": record.starts_at,
        "ends_at": record.ends_at,
        "timezone": record.timezone,
        "is_virtual": record.is_virtual,
        "location_text": record.location_text,
        "city": record.city,
        "region": record.region,
        "country": record.country,
        "industry_tags": record.industry_tags or None,
        "stage_tags": record.stage_tags or None,
        "benefit_tags": record.benefit_tags or None,
        "attendee_types": record.attendee_types or None,
        "cost_usd_cents": record.cost_usd_cents,
        "application_required": record.application_required,
        "host_quality_score": record.host_quality_score,
        "status": record.status,
    }


async def upsert_discovered_events(
    session: AsyncSession,
    records: list[DiscoveredEvent],
    fetched_at: datetime,
) -> tuple[int, int]:
    if not records:
        return 0, 0

    source_ids = [r.source_id for r in records]
    result = await session.execute(
        sa.select(Event.source_id).where(Event.source_id.in_(source_ids))
    )
    existing_ids = {row.source_id for row in result}

    inserted = 0
    updated = 0
    now = datetime.now(UTC)

    conn = await session.connection()
    is_postgres = conn.dialect.name == "postgresql"
    if is_postgres:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        for record in records:
            data = _to_db_dict(record, fetched_at)
            stmt = pg_insert(Event).values(id=uuid.uuid4(), created_at=now, updated_at=now, **data)
            update_fields = {k: v for k, v in data.items() if k != "source_id"}
            stmt = stmt.on_conflict_do_update(
                index_elements=["source_id"],
                set_={**update_fields, "updated_at": now},
            )
            await session.execute(stmt)
            if record.source_id in existing_ids:
                updated += 1
            else:
                inserted += 1
    else:
        for record in records:
            data = _to_db_dict(record, fetched_at)
            if record.source_id in existing_ids:
                update_fields = {k: v for k, v in data.items() if k != "source_id"}
                await session.execute(
                    sa.update(Event)
                    .where(Event.source_id == record.source_id)
                    .values(**update_fields, updated_at=now)
                )
                updated += 1
            else:
                session.add(Event(id=uuid.uuid4(), created_at=now, updated_at=now, **data))
                inserted += 1

    await session.commit()
    return inserted, updated

