"""Search endpoint — intent parse → discover → synthesize → cite."""
from __future__ import annotations
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from app.models.schemas import SearchRequest, SearchResponse, FitResult, Citation, IntentResult
from app.services.intent_parser import parse_intent
from app.services.resource_service import resource_service
from app.services.scraper_service import scraper_service
from app.services.source_router import select_sources, build_search_url
from app.services.llm_client import get_llm
from app.services.memory_service import memory_service

router = APIRouter()

_EXPLANATION_PROMPT = """Given this founder query and resource, write:
1. Why this resource fits (max 1 sentence)
2. Next step (max 1 sentence, specific action)
Keep under 50 words total.

Query: {query}
Resource: {name} ({type})
Description: {description}
Deadline: {deadline}
Funding: {funding}
Location: {location}
"""


@router.post("", response_model=SearchResponse)
async def search_resources(request: SearchRequest) -> SearchResponse:
    # 1. Parse intent
    intent = await parse_intent(request.query)

    # 2. Check local DB first (active resources matching intent)
    local_results = await resource_service.search_by_intent(intent.model_dump(), limit=20)

    # 3. If local results are thin, discover fresh ones via Tavily
    fresh_results: List[Dict[str, Any]] = []
    fresh_scraped = 0
    if len(local_results) < 5:
        discovered = await scraper_service.discover(intent.model_dump(), max_results=8)
        for d in discovered:
            # Scrape each discovered URL
            parsed = await scraper_service.scrape_new_resource(d["url"])
            if parsed and "resource" in parsed:
                fresh_results.append(parsed["resource"])
                fresh_scraped += 1

    # 4. Combine + rank
    all_resources = local_results + fresh_results
    scored: List[tuple[float, Any]] = []
    for i, r in enumerate(all_resources):
        score = max(0.5, 1.0 - (i * 0.05))
        if r.status == "active":
            score += 0.1
        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [r for _, r in scored[:request.limit]]

    # 5. Generate explanations + citations
    results: List[FitResult] = []
    llm = get_llm()
    for r in top:
        prompt = _EXPLANATION_PROMPT.format(
            query=request.query,
            name=r.name,
            type=r.type,
            description=r.description or "N/A",
            deadline=str(r.deadline) if r.deadline else "No deadline",
            funding=r.prize_amount or r.funding_range or "N/A",
            location=", ".join(r.location) if r.location else "N/A",
        )
        try:
            explanation = await llm.generate(prompt, max_tokens=120, temperature=0.3)
            sentences = [s.strip() for s in explanation.split(".") if s.strip()]
            fit_exp = sentences[0] + "." if sentences else f"{r.name} matches your search."
            next_step = sentences[1] + "." if len(sentences) > 1 else "Visit their site for details."
        except Exception:
            fit_exp = f"{r.name} is a {r.type} resource for founders in your area."
            next_step = "Check the details at their website."

        # Freshness badge
        if r.last_verified:
            from datetime import datetime, timezone
            days = (datetime.now(timezone.utc) - r.last_verified).days
            badge = f"Verified {days}d ago" if days < 30 else "Needs verification"
        else:
            badge = "Discovered today" if not r.id else "Never verified"

        citation = Citation(
            source=r.provenance.get("source", "web") if r.provenance else "web",
            url=r.url or "",
            title=r.name,
            last_verified=r.last_verified,
            confidence="verified" if r.last_verified else "unverified",
        )

        results.append(FitResult(
            resource=r,
            fit_explanation=fit_exp,
            next_step=next_step,
            confidence_badge=badge,
            fit_score=max(0.5, 1.0 - (i * 0.05)),
            citations=[citation],
        ))

    # 6. Store search memory
    if request.profile_id:
        try:
            await memory_service.create(
                profile_id=request.profile_id,
                session_id=request.session_id,
                content=f"Searched: {request.query}",
                category="search",
                metadata={"intent": intent.model_dump(), "result_count": len(results)},
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
