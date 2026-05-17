"""Scout API — agent run endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter

from app.models.schemas import ScoutProfile, ScoutRunRequest, ScoutRunResponse, ScoutStatus
from app.services.scout_service import run_scout_real

router = APIRouter(prefix="/scout", tags=["scout"])

# In-memory status (demo only — no persistence)
_last_run: datetime | None = None
_runs_today: int = 0


@router.post("/run", response_model=ScoutRunResponse)
async def scout_run(request: ScoutRunRequest) -> ScoutRunResponse:
    """Execute a scout run — VERIFY → FETCH → MATCH → COMPOSE pipeline."""
    global _last_run, _runs_today

    result = await run_scout_real(request)

    _last_run = datetime.now(timezone.utc)
    _runs_today += 1

    return result


@router.get("/status", response_model=ScoutStatus)
async def scout_status() -> ScoutStatus:
    """Get current scout agent status."""
    return ScoutStatus(
        last_run=_last_run,
        next_run=None,  # Demo — no scheduled runs
        is_running=False,
        runs_today=_runs_today,
    )
