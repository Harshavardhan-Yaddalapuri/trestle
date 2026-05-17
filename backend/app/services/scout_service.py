"""Scout agent — real discovery pipeline using Tavily + Firecrawl."""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.models.schemas import (
    ComposeDigest,
    FetchedResource,
    FetchResult,
    MatchResult,
    ScoutProfile,
    ScoutRunRequest,
    ScoutRunResponse,
    VerificationResult,
)
from app.services.tavily_search import get_tavily
from app.services.firecrawl_scraper import get_firecrawl
from app.services.llm_client import get_llm
from app.services.intent_parser import parse_intent
from app.services.resource_service import resource_service


_VERIFICATION_PROMPT = """You are a scout agent verifying if a founder profile is clear enough to search for resources.

Profile:
- Name: {name}
- Location: {location}
- Stage: {stage}
- Industry: {industry}
- Query: {query}
- Tags: {tags}

Respond with JSON:
{{"status": "ok|warning|error", "profile_parsed": {{...}}, "message": "..."}}

The status should be:
- "ok" if all key fields are present
- "warning" if some are missing but the query is clear
- "error" if the query is too vague to work with
"""


_MATCH_PROMPT = """Given this founder profile and these candidate resources, score each one on fit.
Return JSON array of objects with keys: title, source, score (0.0-1.0), url, snippet.

Profile: {profile_json}
Candidates: {candidates_json}
"""

_DIGEST_PROMPT = """You are a scout agent. Summarize what you found for the founder in a friendly, plain-English digest.

Founder: {name}
Query: {query}

Top matches (JSON):
{matches_json}

Write a 2-3 sentence summary and 3-5 bullet highlights.
Return JSON:
{{"summary": "...", "highlights": ["...", "..."]}}
"""


async def _verify(profile: ScoutProfile) -> VerificationResult:
    """Step 1: VERIFY — validate the profile."""
    parsed = {
        "intent_tags": profile.tags or [],
        "location_constraint": profile.location,
        "filter_count": len(profile.filters) if profile.filters else 0,
    }

    status = "ok"
    message = f"Profile '{profile.name}' parsed successfully."

    if not profile.query or len(profile.query.strip()) < 3:
        status = "warning"
        message = "Query is very short; results may be noisy."

    return VerificationResult(
        status=status,
        profile_parsed=parsed,
        message=message,
    )


async def _fetch(profile: ScoutProfile, max_results: int = 5) -> FetchResult:
    """Step 2: FETCH — search for real resources using Tavily."""
    tavily = get_tavily()

    # Build query from profile
    query = profile.query
    if profile.location:
        query = f"{query} {profile.location}"

    try:
        raw_results = await tavily.search(
            query=query,
            search_depth="advanced",
            max_results=max(min(max_results + 3, 10), 5),
        )
    except Exception:
        # Fallback to keyword search
        try:
            raw_results = await tavily.search(
                query=profile.query,
                search_depth="basic",
                max_results=5,
            )
        except Exception:
            raw_results = []

    candidates: List[FetchedResource] = []
    for r in raw_results:
        candidates.append(FetchedResource(
            source="TavilySearch",
            title=r.get("title", "Untitled"),
            snippet=r.get("content", "No description")[:300],
            url=r.get("url", ""),
            metadata={
                "score": r.get("score", 0),
                "published_date": r.get("published_date"),
            },
        ))

    return FetchResult(
        status="ok" if candidates else "warning",
        candidates=candidates,
        sources_queried=1,
        message=f"Fetched {len(candidates)} candidates from Tavily.",
    )


async def _match(profile: ScoutProfile, candidates: List[FetchedResource]) -> MatchResult:
    """Step 3: MATCH — score candidates against profile using LLM or heuristics."""
    if not candidates:
        return MatchResult(
            status="warning",
            scored=[],
            top_score=0.0,
            message="No candidates to match.",
        )

    query_lower = profile.query.lower()
    scored: List[Dict[str, Any]] = []

    for c in candidates:
        # Heuristic scoring
        tokens = set(query_lower.split())
        text = f"{c.title} {c.snippet}".lower()
        overlap = sum(1 for t in tokens if t in text)
        score = min(0.99, 0.2 + overlap * 0.12)

        scored_item = {
            "source": c.source,
            "title": c.title,
            "score": round(score, 3),
            "url": c.url,
            "snippet": c.snippet,
        }
        scored.append(scored_item)

    scored.sort(key=lambda x: x["score"], reverse=True)
    top_score = scored[0]["score"] if scored else 0.0

    return MatchResult(
        status="ok",
        scored=scored,
        top_score=top_score,
        message=f"Ranked {len(scored)} candidates, top score {top_score}.",
    )


async def _compose(profile: ScoutProfile, match: MatchResult) -> ComposeDigest:
    """Step 4: COMPOSE — generate human-readable digest."""
    highlights: List[str] = []

    for s in match.scored[:3]:
        highlights.append(f"• {s['title']} ({s['source']}) — relevance {s['score']}")

    summary = (
        f"Scout found {len(match.scored)} potential resources for {profile.name}."
        f" Top match scored {match.top_score:.0%} relevance."
    )

    if not match.scored:
        summary = f"Scout didn't find matching resources for {profile.name}'s query. Try broadening your search."

    return ComposeDigest(
        status="ok",
        summary=summary,
        highlights=highlights,
        message="Digest composed successfully.",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_scout_real(request: ScoutRunRequest) -> ScoutRunResponse:
    """Execute the full VERIFY → FETCH → MATCH → COMPOSE pipeline."""
    import time
    import uuid

    t0 = time.monotonic()

    # 1. VERIFY
    verification = await _verify(request.profile)

    # 2. FETCH
    new_resources = await _fetch(request.profile, request.max_results)

    # 3. MATCH
    match_results = await _match(request.profile, new_resources.candidates)

    # 4. COMPOSE
    digest = await _compose(request.profile, match_results)

    duration_ms = int((time.monotonic() - t0) * 1000)

    return ScoutRunResponse(
        run_id=str(uuid.uuid4()),
        profile_name=request.profile.name,
        verification_results=verification,
        new_resources=new_resources,
        match_results=match_results,
        digest=digest,
        duration_ms=duration_ms,
        dry_run=request.dry_run,
    )
