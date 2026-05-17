"""Parse founder natural-language queries into structured search intent."""
from __future__ import annotations

from typing import Any, Dict

from app.services.llm_client import get_llm
from app.models.schemas import IntentResult

_INTENT_PROMPT_TEMPLATE = """Extract structured search criteria from the founder's query.
Return ONLY valid JSON matching this exact schema:
{
    "location": "city name or null",
    "state": "state name or null",
    "stage": "startup stage (idea, pre-revenue, seed, series-a, growth) or null",
    "need_type": "type of resource needed (grant, accelerator, event, coworking, mentorship, hiring_program) or null",
    "timeline": "timeframe (30_days, 90_days, 6_months, ongoing) or null",
    "industry": ["industry_1", "industry_2"],
    "demographics": ["demographic_tags"],
    "funding_range": "funding amount string or null"
}

Rules:
- Location: "Detroit, MI" → location="Detroit", state="Michigan"
- Stage: map words like "just starting", "idea stage" → "idea"
- Need type: "grants" → "grant", "funding" → "grant", "workshop" → "event"
- Industry: extract from query; if "AI" → ["artificial_intelligence"]
- Demographics: extract e.g. "Black woman founder", "veteran", "student"
- If a field can't be inferred, use null or empty array

Query: {query}
"""


def _normalize_location(raw: Any) -> tuple[str | None, str | None]:
    """Extract city and state from a raw location string."""
    if not raw:
        return None, None
    s = str(raw).lower().strip()
    # Michigan cities
    michigan_cities = [
        "detroit", "ann arbor", "grand rapids", "lansing", "kalamazoo",
        "flint", "saginaw", "muskegon", "traverse city", "bay city",
        "holland", "porthuron", "royal oak", "sterling heights", "warren",
        "madison heights", "ferndale", "hamtramck", "corktown", "midtown",
        "downtown detroit", "new center", "eastern market", "campus martius",
    ]
    for city in michigan_cities:
        if city in s:
            # Capitalize each word
            return city.title(), "Michigan"
    # Default Michigan if state mentioned
    if "michigan" in s or "mi" in s.split():
        words = s.replace(",", " ").split()
        if len(words) > 1:
            return words[0].title(), "Michigan"
        return None, "Michigan"
    return s.title(), None


def _normalize_stage(raw: Any) -> str | None:
    """Normalize startup stage strings."""
    if not raw:
        return None
    s = str(raw).lower()
    if any(w in s for w in ["just starting", "idea", "concept", "brainstorm"]):
        return "idea"
    if any(w in s for w in ["pre-revenue", "early stage", "early-stage", "building"]):
        return "pre-revenue"
    if any(w in s for w in ["seed", "angel", "friends"]):
        return "seed"
    if any(w in s for w in ["series a", "series-a"]):
        return "series-a"
    if any(w in s for w in ["series b", "growth", "scale"]):
        return "growth"
    return raw


def _normalize_need_type(raw: Any) -> str | None:
    """Map query terms to resource types."""
    if not raw:
        return None
    s = str(raw).lower()
    mapping = {
        "grant": ["grant", "funding", "money", "fund", "non-dilutive", "non dilutive"],
        "accelerator": ["accelerator", "incubator", "program"],
        "event": ["event", "workshop", "conference", "meetup", "networking event"],
        "coworking": ["coworking", "office", "space", "workspace"],
        "mentorship": ["mentor", "advisor", "advisory", "guidance", "coach"],
        "hiring_program": ["hire", "recruit", "talent", "workforce", "employee"],
        "pitch_competition": ["pitch", "competition", "contest", "demo day"],
        "tax_credit": ["tax credit", "incentive", "tax relief"],
        "learning_material": ["learn", "course", "education", "training", "book"],
        "networking": ["network", "connection", "community", "peer"],
    }
    for need_type, terms in mapping.items():
        if any(t in s for t in terms):
            return need_type
    return raw


async def parse_intent(query: str) -> IntentResult:
    """Parse a founder query into structured search criteria using LLM."""
    llm = get_llm()
    try:
        raw = await llm.parse_json(_INTENT_PROMPT_TEMPLATE.format(query=query))
    except Exception:
        # Fallback: use keyword extraction if LLM fails
        raw = {
            "location": "Detroit" if "detroit" in query.lower() else None,
            "state": "Michigan" if any(w in query.lower() for w in ["michigan", "mi"]) else None,
            "stage": _normalize_stage(query),
            "need_type": _normalize_need_type(query),
            "timeline": "90_days" if "90" in query or "three months" in query.lower() else "6_months" if "6" in query or "six months" in query.lower() else None,
            "industry": [],
            "demographics": ["Black woman founder"] if "black" in query.lower() and "woman" in query.lower() else [],
            "funding_range": None,
        }

    loc, state = _normalize_location(raw.get("location"))
    if state is None:
        state = "Michigan" if any(w in query.lower() for w in ["michigan", "mi", "detroit", "ann arbor", "grand rapids"]) else None

    return IntentResult(
        location=loc or state,
        state=state,
        stage=_normalize_stage(raw.get("stage")),
        need_type=_normalize_need_type(raw.get("need_type")),
        timeline=str(raw.get("timeline")).replace("_", " ") if raw.get("timeline") else None,
        industry=[str(i).lower().replace(" ", "_") for i in raw.get("industry", [])] if raw.get("industry") else None,
        demographics=[str(d).lower() for d in raw.get("demographics", [])] if raw.get("demographics") else None,
        funding_range=raw.get("funding_range"),
    )
