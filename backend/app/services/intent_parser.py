"""Intent parser — founder query → structured criteria via local LLM, with keyword fallback."""
from __future__ import annotations
from typing import Any
from app.services.llm_client import get_llm
from app.models.schemas import IntentResult

_INTENT_PROMPT = """Extract structured search criteria from the founder's query.
Return ONLY valid JSON matching this exact schema:
{
    "location": "city name or null",
    "state": "state name or null",
    "stage": "startup stage (idea, pre-revenue, seed, series-a, growth) or null",
    "need_type": "type of resource needed (grant, accelerator, event, coworking, mentorship, hiring_program, pitch_competition, tax_credit, other) or null",
    "timeline": "timeframe (30_days, 90_days, 6_months, ongoing) or null",
    "industry": ["industry_1", "industry_2"],
    "demographics": ["demographic_tags"],
    "funding_range": "funding amount string or null",
    "keywords": ["additional keywords for search"]
}

Rules:
- Location: "Detroit, MI" → location="Detroit", state="Michigan"
- Stage: map "just starting", "idea stage" → "idea"
- Need type: "grants" → "grant", "funding" → "grant", "workshop" → "event"
- Industry: extract from query; if "AI" → ["artificial_intelligence"]
- Demographics: extract e.g. "Black woman founder", "veteran", "student"
- Keywords: extract additional terms that should be searched
- If a field can't be inferred, use null or empty array

Query: {query}
"""


def _normalize_location(raw: Any) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    s = str(raw).lower().strip()
    state_cities = {
        "michigan": ["detroit", "ann arbor", "grand rapids", "lansing", "kalamazoo", "flint"],
        "illinois": ["chicago", "springfield", "champaign", "urbana", "rockford"],
        "ohio": ["cleveland", "columbus", "cincinnati", "dayton", "toledo"],
        "wisconsin": ["milwaukee", "madison", "green bay", "kenosha"],
    }
    for state, cities in state_cities.items():
        if any(city in s for city in cities):
            return next(c.title() for c in cities if c in s), state.title()
        if state in s:
            return None, state.title()
    return s.title(), None


def _normalize_stage(raw: Any) -> str | None:
    if not raw:
        return None
    s = str(raw).lower()
    mapping = {
        "idea": ["just starting", "idea", "concept", "brainstorm"],
        "pre-revenue": ["pre-revenue", "early stage", "early-stage", "building"],
        "seed": ["seed", "angel", "friends"],
        "series-a": ["series a", "series-a"],
        "growth": ["series b", "growth", "scale"],
    }
    for stage, terms in mapping.items():
        if any(t in s for t in terms):
            return stage
    return raw


def _normalize_need_type(raw: Any) -> str | None:
    if not raw:
        return None
    s = str(raw).lower()
    mapping = {
        "grant": ["grant", "funding", "money", "fund", "non-dilutive", "non dilutive"],
        "accelerator": ["accelerator", "incubator", "program"],
        "event": ["event", "workshop", "conference", "meetup"],
        "coworking": ["coworking", "office", "space", "workspace"],
        "mentorship": ["mentor", "advisor", "advisory", "guidance", "coach"],
        "hiring_program": ["hire", "recruit", "talent", "workforce"],
        "pitch_competition": ["pitch", "competition", "contest", "demo day"],
        "tax_credit": ["tax credit", "incentive", "tax relief"],
        "other": ["learn", "course", "education", "training", "network"],
    }
    for need_type, terms in mapping.items():
        if any(t in s for t in terms):
            return need_type
    return raw


async def parse_intent(query: str) -> IntentResult:
    llm = get_llm()
    try:
        raw = await llm.parse_json(_INTENT_PROMPT.format(query=query))
    except Exception:
        raw = {}

    loc, state = _normalize_location(raw.get("location"))
    if state is None:
        state = "Michigan" if any(w in query.lower() for w in ["michigan", "mi", "detroit", "ann arbor"]) else None

    return IntentResult(
        location=loc or state,
        state=state,
        stage=_normalize_stage(raw.get("stage")),
        need_type=_normalize_need_type(raw.get("need_type")),
        timeline=str(raw.get("timeline")).replace("_", " ") if raw.get("timeline") else None,
        industry=[str(i).lower().replace(" ", "_") for i in raw.get("industry", [])] if raw.get("industry") else None,
        demographics=[str(d).lower() for d in raw.get("demographics", [])] if raw.get("demographics") else None,
        funding_range=raw.get("funding_range"),
        keywords=[str(k).lower() for k in raw.get("keywords", [])] if raw.get("keywords") else None,
    )
