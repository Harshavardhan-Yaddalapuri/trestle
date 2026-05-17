"""Search API — founder queries resource discovery."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.models.schemas import SearchRequest, SearchResponse, FitResult
from app.services.intent_parser import parse_intent
from app.services.resource_service import resource_service
from app.services.llm_client import get_llm
from app.services.memory_service import memory_service

router = APIRouter(prefix="/api/search", tags=["search"])

_EXPLANATION_PROMPT = """Given this founder profile and this resource, write a concise 2-sentence explanation.

1. Why this resource fits the founder (what about their profile matches the resource)
2. The very next step they should take (apply, attend, register, call, etc.)

Keep it under 80 words. No marketing speak. Plain English.

Founder query: {query}
Resource: {resource_name} ({resource_type})
Description: {description}
Deadline: {deadline}
Funding/Prize: {funding}
Location: {location}
Eligibility: {eligibility}
"""


async def _generate_explanation(query: str, resource: Any) -> Dict[str, str]:
    """Use LLM to generate personalized fit explanation."""
    prompt = _EXPLANATION_PROMPT.format(
        query=query,
        resource_name=resource.name,
        resource_type=resource.type,
        description=resource.description or "N/A",
        deadline=str(resource.deadline) if resource.deadline else "No deadline listed",
        funding=resource.prize_amount or resource.funding_range or "N/A",
        location=", ".join(resource.location) if resource.location else "N/A",
        eligibility=json.dumps(resource.eligibility) if resource.eligibility else "N/A",
    )
    try:
        llm = get_llm()
        text = await llm.generate(prompt, max_tokens=200, temperature=0.3)
        # Split into why_fit and next_step
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        if len(sentences) >= 2:
            return {
                "fit_explanation": ". ".join(sentences[:2]) + ".",
                "next_step": ". ".join(sentences[2:3]) + "." if len(sentences) > 2 else "Visit the resource link for details.",
            }
        return {"fit_explanation": text, "next_step": "Visit the resource link for details."}
    except Exception:
        return {
            "fit_explanation": f"{resource.name} supports {resource.type.replace('_', ' ')} for founders in {', '.join(resource.location) if resource.location else 'your area'}.",
            "next_step": f"Check the details at {resource.url or 'their website'} to apply or register.",
        }


@router.post("", response_model=SearchResponse)
async def search_resources(request: SearchRequest) -> SearchResponse:
    """Main search endpoint — parse query, find resources, explain fit."""
    # 1. Parse intent
    intent = await parse_intent(request.query)

    # 2. Search resources
    resources = await resource_service.search_by_query_parsed(
        intent.model_dump(), limit=request.limit
    )

    # 3. Store memory of this query
    memory_refs = []
    if request.profile_id:
        try:
            mem = await memory_service.create(
                profile_id=request.profile_id,
                content=f"Searched: {request.query}. Intent: {intent.model_dump_json()}",
                category="search",
                session_id=request.session_id,
                metadata={"intent": intent.model_dump(), "result_count": len(resources)},
            )
            memory_refs.append(str(mem.get("id", "")))
        except Exception:
            pass

    # 4. Generate explanations for top results
    results: List[FitResult] = []
    for i, resource in enumerate(resources):
        try:
            explanation = await _generate_explanation(request.query, resource)
        except Exception:
            explanation = {
                "fit_explanation": f"{resource.name} matches your search criteria.",
                "next_step": f"Visit their site for details.",
            }

        # Calculate confidence badge
        days_ago = 30  # default
        if resource.updated_at:
            from datetime import datetime, timezone
            try:
                updated = datetime.fromisoformat(str(resource.updated_at).replace("Z", "+00:00"))
                days_ago = max(1, (datetime.now(timezone.utc) - updated).days)
            except Exception:
                pass

        if days_ago <= 7:
            confidence = f"Verified this week"
        elif days_ago <= 30:
            confidence = f"Verified {days_ago} days ago"
        else:
            confidence = "Needs verification"

        # Fit score from search
        fit_score = max(0.5, 1.0 - (i * 0.05))  # Simple decay

        results.append(FitResult(
            resource=resource,
            fit_explanation=explanation["fit_explanation"],
            next_step=explanation["next_step"],
            confidence_badge=confidence,
            fit_score=fit_score,
        ))

    return SearchResponse(
        query_parsed=intent,
        results=results,
        total_found=len(results),
        memory_used=memory_refs if memory_refs else None,
    )
