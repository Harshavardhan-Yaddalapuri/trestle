"""schema.org JSON-LD event parser.

Turns the `application/ld+json` blocks embedded in an event listing page into
`DiscoveredEvent` records. Listing pages rarely put Event nodes at the top
level — Eventbrite, for example, wraps them in `ItemList` → `ListItem` →
`item` — so the node walker descends through arbitrary containers.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import deque
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.services.events.taxonomy import (
    ATTENDEE_KEYWORDS,
    BENEFIT_KEYWORDS,
    INDUSTRY_KEYWORDS,
    STAGE_KEYWORDS,
    extract_tags,
    host_quality_score,
    normalize_text,
    parse_iso_datetime,
)

_JSONLD_SCRIPT_RE = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)

# schema.org marks online events with an eventAttendanceMode enum value.
_ONLINE_ATTENDANCE_MODES = ("onlineeventattendancemode", "mixedeventattendancemode")

_APPLICATION_REQUIRED_PHRASES = (
    "application required",
    "must apply",
    "apply to attend",
    "selection process",
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


def _event_source_id(url: str, starts_at: datetime, name: str) -> str:
    stable = f"{url}|{starts_at.isoformat()}|{name.lower().strip()}"
    digest = hashlib.sha1(stable.encode("utf-8")).hexdigest()  # nosec B324
    return f"event:{digest}"


def _is_event_node(node: dict[str, Any]) -> bool:
    node_type = node.get("@type")
    if isinstance(node_type, list):
        return any(str(item).lower() == "event" for item in node_type)
    return str(node_type).lower() == "event"


def _iter_event_nodes(root: Any) -> list[dict[str, Any]]:
    """Collect every Event node reachable from `root`, in document order.

    Walks all nested lists and dict values so Event nodes are found regardless
    of the container that wraps them (`@graph`, `itemListElement`, `subEvent`).
    Breadth-first traversal keeps the provider's own ordering, which listing
    pages use to express relevance.
    """
    found: list[dict[str, Any]] = []
    queue: deque[Any] = deque([root])
    seen: set[int] = set()

    while queue:
        current = queue.popleft()
        if isinstance(current, list):
            queue.extend(current)
            continue
        if not isinstance(current, dict):
            continue

        # Guard against the self-referencing structures some sites emit.
        if id(current) in seen:
            continue
        seen.add(id(current))

        if _is_event_node(current):
            found.append(current)

        for value in current.values():
            if isinstance(value, (dict, list)):
                queue.append(value)

    return found


def _parse_location(
    location_raw: Any,
) -> tuple[bool, str | None, str | None, str | None, str | None]:
    if location_raw is None:
        return False, None, None, None, None
    if isinstance(location_raw, list):
        for item in location_raw:
            parsed = _parse_location(item)
            if parsed[1] is not None:
                return parsed
        return False, None, None, None, None
    if isinstance(location_raw, str):
        text = normalize_text(location_raw)
        return False, text or None, None, None, None
    if not isinstance(location_raw, dict):
        return False, None, None, None, None

    location_type = str(location_raw.get("@type") or "").lower()
    if location_type == "virtuallocation":
        name = normalize_text(location_raw.get("name")) or "Virtual"
        return True, name, None, None, None

    name = normalize_text(location_raw.get("name"))
    address = location_raw.get("address")
    city = region = country = None
    if isinstance(address, dict):
        city = normalize_text(address.get("addressLocality")) or None
        region = normalize_text(address.get("addressRegion")) or None
        country = normalize_text(address.get("addressCountry")) or None
    elif isinstance(address, str):
        name = name or normalize_text(address)
    location_text = ", ".join(v for v in [name, city, region, country] if v) or None
    return False, location_text, city, region, country


def _parse_cost_usd_cents(offers_raw: Any) -> int | None:
    offers = offers_raw[0] if isinstance(offers_raw, list) and offers_raw else offers_raw
    if not isinstance(offers, dict):
        return None
    price = offers.get("price")
    currency = str(offers.get("priceCurrency") or "USD").upper()
    if currency != "USD" or price is None:
        return None
    if isinstance(price, str) and price.strip().lower() in {"free", "0", "$0"}:
        return 0
    try:
        return int(float(str(price).replace("$", "").replace(",", "").strip()) * 100)
    except ValueError:
        return None


def _is_online_attendance_mode(value: Any) -> bool:
    if not value:
        return False
    mode = str(value).rsplit("/", maxsplit=1)[-1].lower()
    return mode in _ONLINE_ATTENDANCE_MODES


def _application_required(description: str) -> bool:
    haystack = description.lower()
    return any(phrase in haystack for phrase in _APPLICATION_REQUIRED_PHRASES)


def _parse_host_name(organizer_raw: Any) -> str | None:
    if isinstance(organizer_raw, dict):
        return normalize_text(organizer_raw.get("name")) or None
    if isinstance(organizer_raw, list):
        for item in organizer_raw:
            if isinstance(item, dict):
                name = normalize_text(item.get("name"))
                if name:
                    return name
    return None


def _build_discovered_event(
    event_node: dict[str, Any],
    source_url: str,
    *,
    source_name: str,
) -> DiscoveredEvent | None:
    name = normalize_text(event_node.get("name"))
    starts_at = parse_iso_datetime(event_node.get("startDate"))
    if not name or starts_at is None:
        return None

    ends_at = parse_iso_datetime(event_node.get("endDate"))
    event_url = normalize_text(event_node.get("url")) or source_url
    description = normalize_text(event_node.get("description"))
    host_name = _parse_host_name(event_node.get("organizer"))

    is_virtual, location_text, city, region, country = _parse_location(
        event_node.get("location")
    )
    if _is_online_attendance_mode(event_node.get("eventAttendanceMode")):
        is_virtual = True

    context_text = " ".join(
        value for value in [name, description, host_name or "", location_text or ""] if value
    )

    return DiscoveredEvent(
        source=source_name,
        source_id=_event_source_id(event_url, starts_at, name),
        name=name,
        description=description,
        url=event_url,
        host_name=host_name,
        starts_at=starts_at,
        ends_at=ends_at,
        timezone=str(event_node.get("eventSchedule"))
        if event_node.get("eventSchedule")
        else None,
        is_virtual=is_virtual,
        location_text=location_text,
        city=city,
        region=region,
        country=country,
        industry_tags=extract_tags(context_text, INDUSTRY_KEYWORDS),
        stage_tags=extract_tags(context_text, STAGE_KEYWORDS),
        benefit_tags=extract_tags(context_text, BENEFIT_KEYWORDS),
        attendee_types=extract_tags(context_text, ATTENDEE_KEYWORDS),
        cost_usd_cents=_parse_cost_usd_cents(event_node.get("offers")),
        application_required=_application_required(description),
        host_quality_score=host_quality_score(host_name),
        status="expired" if (ends_at or starts_at) < datetime.now(UTC) else "active",
        source_payload=event_node,
    )


def parse_jsonld_events(
    content: str,
    source_url: str,
    *,
    source_name: str = "web_jsonld",
) -> list[DiscoveredEvent]:
    """Extract every schema.org Event embedded in an HTML document."""
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
            event = _build_discovered_event(node, source_url, source_name=source_name)
            if event is None or event.source_id in seen_ids:
                continue
            events.append(event)
            seen_ids.add(event.source_id)
    return events
