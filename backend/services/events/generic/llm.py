"""Schema-guided, opt-in LLM extraction for pages without reliable structure."""
from __future__ import annotations

import json

from backend.services.events.generic.types import ExtractedEvent, ExtractionBatch
from backend.services.llm.base import LLMClient
from backend.services.llm.types import LLMMessage

_PROMPT = """Extract only explicitly supported upcoming events from this web page.
Return JSON exactly as {{"events":[...]}}. Do not invent missing values. Each event
may contain: name, description, starts_at, ends_at, timezone, venue, address,
city, region, country, is_virtual, registration_url, organizer, price_usd_cents,
industry_tags, stage_tags, benefit_tags, attendee_types, source_identifier,
field_confidences (0..1), evidence (field -> exact source text).
Reject non-event content and any event whose name or start date is unavailable.
SOURCE URL: {source_url}
PAGE TEXT:
{page_text}"""


async def extract_with_llm(llm: LLMClient, page_text: str, source_url: str) -> ExtractionBatch:
    response = await llm.complete(
        [LLMMessage(role="system", content=_PROMPT.format(source_url=source_url, page_text=page_text))],
        response_format={"type": "json_object"},
        temperature=0,
    )
    try:
        payload = json.loads(response.content or "{}")
    except json.JSONDecodeError:
        return ExtractionBatch(method="llm", diagnostics={"error": "invalid_json"})
    raw_events = payload.get("events")
    if not isinstance(raw_events, list):
        return ExtractionBatch(method="llm", diagnostics={"error": "events_not_list"})
    events: list[ExtractedEvent] = []
    for item in raw_events:
        if not isinstance(item, dict):
            continue
        try:
            events.append(ExtractedEvent(**item))
        except Exception:
            continue
    return ExtractionBatch(method="llm", events=events, diagnostics={"usage_tokens": response.usage.total_tokens})
