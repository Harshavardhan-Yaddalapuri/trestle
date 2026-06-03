"""Two-stage intent classifier: regex fast-path → Deepseek LLM fallback.

v1 limitation: classifies on the single message only. The caller (Step 14
orchestrator) is responsible for passing conversation history if context-aware
classification is needed.
"""
from __future__ import annotations

import json

from backend.core.errors import UpstreamError
from backend.core.logging import get_logger
from backend.schemas.intent import ExtractedEntities, IntentResult
from backend.services.intent.regex_rules import RULES
from backend.services.llm.base import LLMClient
from backend.services.llm.types import LLMMessage

logger = get_logger(__name__)

_MAX_MESSAGE_CHARS = 2000

_SYSTEM_PROMPT = """You are an intent classifier for Trestle, a grant-discovery assistant for startup founders.

Classify the user message into exactly one intent label and extract entities. Return JSON only.

Intent labels:
- "greet": simple greetings ("hi", "hello", "hey")
- "discover": open-ended exploration ("what kinds of grants exist", "tell me about funding")
- "match_request": wants grant matches now ("find me grants", "what fits my company")
- "deep_dive": wants more info on a specific grant ("tell me more about NSF SBIR", "is the YC deadline soon")
- "profile_update": wants to update their profile ("we just incorporated in Delaware", "team size is 4 now")
- "profile_query": wants to see what Trestle knows ("what do you have on file for me")
- "lifecycle_action": track/untrack/dismiss a specific grant ("save this one", "I'm not interested in YC")
- "smalltalk": non-substantive ("thanks", "you're helpful")
- "out_of_scope": unrelated to grants/profile/founder work ("write me a poem", "what's the weather")
- "correction": user is correcting something the agent said ("no, we're seed not pre-seed", "that's wrong, we have 5 people")
- "unknown": cannot determine intent

Entity types to extract:
- grant_refs: list of grant names/slugs mentioned
- stage: company stage if mentioned (e.g. "pre-seed", "seed", "series-a")
- location: country/state/region if mentioned (e.g. "US-DE", "California", "UK")
- industries: list of industry tags if mentioned
- funding_amount_usd_cents: dollar amount in USD cents if mentioned
- team_size: integer if mentioned
- action: for lifecycle_action only — one of "track", "untrack", "dismiss", "undismiss"

Respond with this exact JSON structure (no markdown, no explanation):
{
  "intent": "<label>",
  "confidence": <0.0-1.0>,
  "entities": {
    "grant_refs": [],
    "stage": null,
    "location": null,
    "industries": [],
    "funding_amount_usd_cents": null,
    "team_size": null,
    "action": null
  }
}

Examples:
User: "Tell me more about the Activate Fellowship"
{"intent":"deep_dive","confidence":0.92,"entities":{"grant_refs":["activate-fellowship"],"stage":null,"location":null,"industries":[],"funding_amount_usd_cents":null,"team_size":null,"action":null}}

User: "We just incorporated in Delaware and have 4 people now"
{"intent":"profile_update","confidence":0.95,"entities":{"grant_refs":[],"stage":null,"location":"US-DE","industries":[],"funding_amount_usd_cents":null,"team_size":4,"action":null}}

User: "Find me grants for AI safety startups raising $500k"
{"intent":"match_request","confidence":0.9,"entities":{"grant_refs":[],"stage":null,"location":null,"industries":["ai-safety"],"funding_amount_usd_cents":50000000,"team_size":null,"action":null}}

User: "I'm not interested in YC W25"
{"intent":"lifecycle_action","confidence":0.88,"entities":{"grant_refs":["yc-w25"],"stage":null,"location":null,"industries":[],"funding_amount_usd_cents":null,"team_size":null,"action":"dismiss"}}

User: "What kinds of government grants are out there for climate tech?"
{"intent":"discover","confidence":0.85,"entities":{"grant_refs":[],"stage":null,"location":null,"industries":["climate-tech"],"funding_amount_usd_cents":null,"team_size":null,"action":null}}

User: "Save the NSF SBIR grant for later"
{"intent":"lifecycle_action","confidence":0.9,"entities":{"grant_refs":["nsf-sbir"],"stage":null,"location":null,"industries":[],"funding_amount_usd_cents":null,"team_size":null,"action":"track"}}
"""


async def classify(message: str, llm_client: LLMClient) -> IntentResult:
    """Classify a single user message into an intent with extracted entities."""
    if not message or not message.strip():
        return IntentResult(
            intent="unknown",
            confidence=0.0,
            entities=ExtractedEntities(),
            classified_by="regex",
        )

    truncated = message[:_MAX_MESSAGE_CHARS]

    # Stage 1: regex fast path
    best_rule = None
    for rule in RULES:
        if rule.pattern.search(truncated):
            if best_rule is None or rule.confidence > best_rule.confidence:
                best_rule = rule

    if best_rule is not None:
        entities = best_rule.entity_extractor(truncated)
        return IntentResult(
            intent=best_rule.intent,
            confidence=best_rule.confidence,
            entities=entities,
            classified_by="regex",
        )

    # Stage 2: LLM fallback
    messages = [
        LLMMessage(role="system", content=_SYSTEM_PROMPT),
        LLMMessage(role="user", content=truncated),
    ]

    response = await llm_client.complete(
        messages,
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    raw_text = response.content or ""
    try:
        parsed = json.loads(raw_text)
    except (json.JSONDecodeError, ValueError):
        logger.warning("intent_llm_parse_failed", raw=raw_text[:200])
        return IntentResult(
            intent="unknown",
            confidence=0.0,
            entities=ExtractedEntities(),
            classified_by="llm",
            raw_llm_response={"raw": raw_text},
        )

    try:
        entities_raw = parsed.get("entities", {})
        entities = ExtractedEntities(**entities_raw)
    except Exception:
        entities = ExtractedEntities()

    return IntentResult(
        intent=parsed.get("intent", "unknown"),
        confidence=float(parsed.get("confidence", 0.0)),
        entities=entities,
        classified_by="llm",
        raw_llm_response=parsed,
    )
