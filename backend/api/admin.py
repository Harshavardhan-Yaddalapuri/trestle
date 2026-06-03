"""Admin endpoints — no auth gate.

TODO: Add authentication before any production deploy.
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import Settings, get_settings
from backend.core.errors import ConflictError
from backend.core.logging import get_logger
from backend.db.models.verification_run import VerificationRun
from backend.db.session import get_db, get_db_factory
from backend.redis_client import get_redis
from backend.schemas.verification import (
    TriggerResponse,
    VerificationRunsResponse,
    VerificationRunSummary,
)
from backend.services.url_verify import _LOCK_KEY, run_verification_sweep

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)

_MAX_RUNS = 20


@router.get("/verification/runs", response_model=VerificationRunsResponse)
async def list_verification_runs(
    db: AsyncSession = Depends(get_db),
) -> VerificationRunsResponse:
    result = await db.execute(
        sa.select(VerificationRun)
        .order_by(VerificationRun.started_at.desc())
        .limit(_MAX_RUNS)
    )
    runs = [VerificationRunSummary.model_validate(r) for r in result.scalars().all()]
    return VerificationRunsResponse(runs=runs)


@router.post("/verification/run", status_code=202, response_model=TriggerResponse)
async def trigger_verification_run(
    request: Request,
    background_tasks: BackgroundTasks,
    db_factory: async_sessionmaker[AsyncSession] = Depends(get_db_factory),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> TriggerResponse:
    existing = await redis.get(_LOCK_KEY)
    if existing:
        raise ConflictError(
            "Verification already in progress",
            code="verification_in_progress",
            extra={"run_id": existing},
        )

    run_id = uuid.uuid4()
    session_id = getattr(request.state, "session_id", None)

    logger.info(
        "verification_run_triggered",
        run_id=str(run_id),
        session_id=session_id,
    )

    background_tasks.add_task(
        run_verification_sweep,
        db_factory,
        redis,
        settings,
        "manual",
        session_id,
        run_id,
    )

    return TriggerResponse(run_id=run_id)
