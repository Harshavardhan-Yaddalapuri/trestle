"""Search endpoint — intent parse → hybrid retrieval (structured + semantic) → rank → explain → cite."""
from __future__ import annotations
from typing import Any, Dict, List, Tuple
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from app.models.schemas import SearchRequest, SearchResponse, FitResult, Citation, IntentResult
from app.services.intent_parser import parse_intent
from app.services.resource_service import resource_service
from app.services.scraper_service import scraper_service
from app.services.source_router import select_sources, build_search_url
from app.services.llm_client import get_llm
from app.services.memory_service import memory_service
from app.services.semantic_service import score_candidates
from app.models.schemas import MemoryCreate

router = APIRouter()

# ── Scoring weights ──
_STRUCTURED_WEIGHT = 0.35   # field-match heuristic
_SEMANTIC_WEIGHT = 0.65     # LLM relevance scoring

_EXPLANATION_PROMPT = """Given this founder query and resource, write:
1. Why this resource fits (max 1 sentence)
2. Next step (max 1 sentence, specific action)
Keep under 50 words total. Be direct — no fluff.

Query: {query}
Resource: {name} ({type})
Description: {description}
Deadline: {deadline}
Funding: {funding}
Location: {location}
Fit score: {fit_score:.0%}
"""


def _freshness_badge(r: Any) -> str:
    """Derive a confidence badge based on verification state."""
    if r.last_verified:
        days = (datetime.now(timezone.utc) - r.last_verified).days
        if days < 7:
            return "Verified recently"
        elif days < 30:
            return f"Verified {days}d ago"
        else:
            return "Needs verification"
    elif not r.id:
        return "Discovered today"
    else:
        return "Never verified"


def _confidence_from_badge(badge: str) -> str:
    if badge.startswith("Verified"):
        return "verified"
    elif badge == "Discovered today":
        return "likely"
    else:
        return "unverified"


@router.post("", response_model=SearchResponse)
async def search_resources(request: SearchRequest) -> SearchResponse:
    # ── 1. Parse intent ──
    intent = await parse_intent(request.query)

    # ── 2. Structured retrieval from local DB ──
    local_results = await resource_service.search_by_intent(
        intent.model_dump(), limit=30
    )
    # Compute structured (positional) scores — service returns pre-sorted
    structured_scores: Dict[str, float] = {}
    total_structured = max(len(local_results), 1)
    for i, r in enumerate(local_results):
        structured_scores[str(r.id) if r.id else r.url or str(i)] = (
            1.0 - (i / total_structured) * 0.5
        )

    # ── 3. Fresh discovery if local results are thin ──
    fresh_results: List[Dict[str, Any]] = []
    fresh_scraped = 0
    if len(local_results) < 5:
        discovered = await scraper_service.discover(
            intent.model_dump(), max_results=8
        )
        for d in discovered:
            parsed = await scraper_service.scrape_new_resource(d["url"])
            if parsed and "resource" in parsed:
                fresh_results.append(parsed["resource"])
                fresh_scraped += 1
        # Fresh results get mid-range structured scores
        for i, _ in enumerate(fresh_results):
            structured_scores[f"fresh_{i}"] = 0.65

    # ── 4. Combine candidates ──
    all_candidates: List[Any] = list(local_results) + fresh_results
    if not all_candidates:
        return SearchResponse(
            query_parsed=intent,
            results=[],
            total_found=0,
            sources_queried=select_sources(intent),
            fresh_sources_scraped=0,
        )

    # Build candidate dicts for semantic scoring
    candidate_dicts: List[Dict[str, Any]] = []
    candidate_keys: List[str] = []
    for i, r in enumerate(all_candidates):
        key = str(r.id) if hasattr(r, "id") and r.id else f"fresh_{i - len(local_results)}"
        candidate_keys.append(key)
        candidate_dicts.append({
            "name": r.name if hasattr(r, "name") else r.get("name", ""),
            "type": r.type if hasattr(r, "type") else r.get("type", "other"),
            "description": (
                r.description if hasattr(r, "description")
                else r.get("description", "")
            ),
            "location": (
                r.location if hasattr(r, "location")
                else r.get("location", [])
            ),
            "stage": (
                r.stage if hasattr(r, "stage")
                else r.get("stage", [])
            ),
            "deadline": (
                str(r.deadline) if hasattr(r, "deadline") and r.deadline
                else str(r.get("deadline", "None"))
            ),
        })

    # ── 5. Semantic scoring ──
    semantic_scores = await score_candidates(request.query, candidate_dicts)

    # ── 6. Hybrid blend + rank ──
    scored: List[tuple[float, int, Any]] = []
    for i, r in enumerate(all_candidates):
        key = candidate_keys[i]
        structured = structured_scores.get(key, 0.5)
        semantic = semantic_scores[i] if i < len(semantic_scores) else 0.5
        hybrid = _STRUCTURED_WEIGHT * structured + _SEMANTIC_WEIGHT * semantic
        # Boost active resources
        status = r.status if hasattr(r, "status") else r.get("status", "active")
        if status == "active":
            hybrid += 0.03
        scored.append((hybrid, i, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_count = min(request.limit, len(scored))
    top = [(score, resource) for score, _, resource in scored[:top_count]]

    # ── 7. Generate explanations + build results ──
    llm = get_llm()
    results: List[FitResult] = []

    for rank, (score, r) in enumerate(top):
        # Normalize resource to dict-like access
        name = r.name if hasattr(r, "name") else r.get("name", "Unknown")
        rtype = r.type if hasattr(r, "type") else r.get("type", "other")
        desc = r.description if hasattr(r, "description") else r.get("description", "")
        deadline = (
            str(r.deadline)
            if hasattr(r, "deadline") and r.deadline
            else str(r.get("deadline") or "")
        )
        funding = (
            r.prize_amount or r.funding_range
            if hasattr(r, "prize_amount")
            else r.get("prize_amount") or r.get("funding_range", "N/A")
        )
        location = (
            r.location if hasattr(r, "location")
            else r.get("location", [])
        )

        prompt = _EXPLANATION_PROMPT.format(
            query=request.query,
            name=name,
            type=rtype,
            description=desc or "N/A",
            deadline=deadline or "No deadline",
            funding=funding or "N/A",
            location=", ".join(location) if location else "N/A",
            fit_score=score,
        )
        try:
            explanation = await llm.generate(prompt, max_tokens=120, temperature=0.3)
            sentences = [s.strip() for s in explanation.split(".") if s.strip()]
            fit_exp = (
                sentences[0] + "."
                if sentences
                else f"{name} matches your search."
            )
            next_step = (
                sentences[1] + "."
                if len(sentences) > 1
                else "Visit their site for details."
            )
        except Exception:
            fit_exp = f"{name} is a {rtype} resource for founders in your area."
            next_step = "Check the details at their website."

        badge = _freshness_badge(r)
        confidence = _confidence_from_badge(badge)

        provenance = (
            r.provenance if hasattr(r, "provenance")
            else r.get("provenance", {})
        )
        citation = Citation(
            source=provenance.get("source", "web") if provenance else "web",
            url=r.url if hasattr(r, "url") and r.url else r.get("url", "") or "",
            title=name,
            last_verified=(
                r.last_verified
                if hasattr(r, "last_verified")
                else r.get("last_verified")
            ),
            confidence=confidence,
        )

        results.append(
            FitResult(
                resource=r,
                fit_explanation=fit_exp,
                next_step=next_step,
                confidence_badge=badge,
                fit_score=round(score, 3),
                citations=[citation],
            )
        )

    # ── 8. Store search memory ──
    if request.profile_id:
        try:
            await memory_service.create(
                profile_id=request.profile_id,
                session_id=request.session_id,
                content=f"Searched: {request.query}",
                category="search",
                metadata={
                    "intent": intent.model_dump(),
                    "result_count": len(results),
                },
            )
        except Exception:
            pass

    sources_queried = select_sources(intent)
    return SearchResponse(
        query_parsed=intent,
        results=results,
        total_found=len(results),
        sources_queried=sources_queried,
        fresh_sources_scraped=fresh_scraped,
    )
