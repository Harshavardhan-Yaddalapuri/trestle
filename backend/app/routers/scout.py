"""Scout router — agent runs: verify → discover → match → summarize."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter
from app.models.schemas import ScoutRunRequest, ScoutRunResponse, ScoutStatus, ScoutChanges
from app.services.scraper_service import scraper_service
from app.services.source_router import select_sources
from app.services.resource_service import resource_service
from app.services.llm_client import get_llm

router = APIRouter()

_last_run: datetime | None = None
_runs_today: int = 0


@router.post("/run", response_model=ScoutRunResponse)
async def scout_run(request: ScoutRunRequest) -> ScoutRunResponse:
    global _last_run, _runs_today
    import time, uuid

    t0 = time.monotonic()
    intent = {
        "location": request.profile.location,
        "state": request.profile.state,
        "stage": request.profile.stage,
        "need_type": None,
        "keywords": (request.profile.tags or []) + [request.profile.query],
    }

    # 1. Select sources
    sources = select_sources(request.profile, max_sources=5)

    # 2. Discover fresh URLs
    discovered = await scraper_service.discover(intent, max_results=8)

    # 3. Check known URLs for changes
    known = await resource_service.get_all(limit=200)
    changes: list = []
    for k in known[:20]:  # Check top 20 known resources
        change = await scraper_service.diff_url(k.url or "")
        if change:
            changes.append(change)

    # 4. Scrape new candidates
    new_candidates: list = []
    for d in discovered:
        parsed = await scraper_service.scrape_new_resource(d["url"])
        if parsed and "resource" in parsed:
            new_candidates.append({
                "title": parsed["resource"].name,
                "url": parsed["resource"].url,
                "type": parsed["resource"].type,
            })

    # 5. Compose summary
    llm = get_llm()
    summary_prompt = f"""Summarize a scout run for {request.profile.name}.
    Sources checked: {', '.join(sources)}
    New candidates found: {len(new_candidates)}
    Changes detected: {len(changes)}

    Write 2-3 plain-English sentences. Mention if anything important changed."""
    try:
        summary = await llm.generate(summary_prompt, max_tokens=200)
    except Exception:
        summary = f"Scout checked {len(sources)} sources, found {len(new_candidates)} new candidates, and detected {len(changes)} changes."

    _last_run = datetime.now(timezone.utc)
    _runs_today += 1

    return ScoutRunResponse(
        run_id=str(uuid.uuid4()),
        profile_name=request.profile.name,
        status="completed",
        sources_queried=sources,
        new_candidates=new_candidates,
        changes_detected=changes,
        summary=summary.strip(),
        duration_ms=int((time.monotonic() - t0) * 1000),
        fresh_sources_scraped=len(new_candidates),
    )


@router.get("/status", response_model=ScoutStatus)
async def scout_status() -> ScoutStatus:
    return ScoutStatus(
        last_run=_last_run,
        next_run=None,
        is_running=False,
        runs_today=_runs_today,
    )
