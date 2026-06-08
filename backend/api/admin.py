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
from backend.core.errors import ConflictError, NotFoundError, ValidationError
from backend.core.logging import get_logger
from backend.db.models.alert_delivery import AlertDelivery
from backend.db.models.ingest_run import IngestRun
from backend.db.models.lifecycle_auto_run import LifecycleAutoRun
from backend.db.models.verification_run import VerificationRun
from backend.db.session import get_db, get_db_factory
from backend.redis_client import get_redis
from backend.schemas.alerts import AlertDeliveriesResponse, AlertDeliverySummary, TriggerAlertResponse
from backend.schemas.ingest import (
    IngestRunDetail,
    IngestRunsResponse,
    IngestRunSummary,
    IngestTriggerResponse,
)
from backend.schemas.lifecycle_auto import (
    LifecycleAutoRunsResponse,
    LifecycleAutoRunSummary,
    TriggerLifecycleAutoResponse,
)
from backend.schemas.verification import (
    TriggerResponse,
    VerificationRunsResponse,
    VerificationRunSummary,
)
from backend.services.email.dependency import get_email_client
from backend.services.ingest.orchestration import run_ingest_sweep
from backend.services.ingest.registry import get_adapter
from backend.services.jobs.checkin_alerts import (
    enqueue_checkin_alerts,
    send_checkin_alert,
)
from backend.services.jobs.deadline_alerts import (
    enqueue_deadline_alerts,
    send_deadline_alert,
)
from backend.services.jobs.new_grant_alerts import (
    enqueue_new_grant_alerts,
    send_new_grant_alert,
)
from backend.services.lifecycle.auto_transitions import (
    _LOCK_KEY as _LIFECYCLE_LOCK_KEY,
    run_lifecycle_auto_sweep,
)
from backend.services.url_verify import _LOCK_KEY, run_verification_sweep

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)

_MAX_RUNS = 20
_ALERT_KINDS = {"deadline_reminder", "new_grant_match", "check_in"}

_SCAN_FN = {
    "deadline_reminder": enqueue_deadline_alerts,
    "new_grant_match": enqueue_new_grant_alerts,
    "check_in": enqueue_checkin_alerts,
}
_SEND_FN = {
    "deadline_reminder": send_deadline_alert,
    "new_grant_match": send_new_grant_alert,
    "check_in": send_checkin_alert,
}


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



@router.get("/lifecycle/runs", response_model=LifecycleAutoRunsResponse)
async def list_lifecycle_runs(
    db: AsyncSession = Depends(get_db),
) -> LifecycleAutoRunsResponse:
    result = await db.execute(
        sa.select(LifecycleAutoRun)
        .order_by(LifecycleAutoRun.started_at.desc())
        .limit(_MAX_RUNS)
    )
    runs = [LifecycleAutoRunSummary.model_validate(r) for r in result.scalars().all()]
    return LifecycleAutoRunsResponse(runs=runs)


@router.post("/lifecycle/run", status_code=202, response_model=TriggerLifecycleAutoResponse)
async def trigger_lifecycle_run(
    request: Request,
    background_tasks: BackgroundTasks,
    db_factory: async_sessionmaker[AsyncSession] = Depends(get_db_factory),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> TriggerLifecycleAutoResponse:
    existing = await redis.get(_LIFECYCLE_LOCK_KEY)
    if existing:
        raise ConflictError(
            "Lifecycle auto-transition already in progress",
            code="lifecycle_auto_in_progress",
            extra={"run_id": existing},
        )

    run_id = uuid.uuid4()
    session_id = getattr(request.state, "session_id", None)

    logger.info(
        "lifecycle_run_triggered",
        run_id=str(run_id),
        session_id=session_id,
    )

    background_tasks.add_task(
        run_lifecycle_auto_sweep,
        db_factory,
        redis,
        settings,
        "manual",
        session_id,
        None,  # now — use real wall clock for manual triggers
        run_id,
    )

    return TriggerLifecycleAutoResponse(run_id=run_id)


# ── Alert admin endpoints ─────────────────────────────────────────────────────


@router.get("/alerts/recent", response_model=AlertDeliveriesResponse)
async def list_recent_alerts(
    db: AsyncSession = Depends(get_db),
) -> AlertDeliveriesResponse:
    """Last 50 alert deliveries. user_id truncated to first 8 chars (PII minimization).

    TODO: Add authentication before production deploy.
    """
    result = await db.execute(
        sa.select(AlertDelivery)
        .order_by(AlertDelivery.created_at.desc())
        .limit(50)
    )
    rows = result.scalars().all()
    deliveries = [
        AlertDeliverySummary(
            id=d.id,
            user_id_prefix=str(d.user_id)[:8],
            alert_kind=d.alert_kind,
            grant_id=d.grant_id,
            key=d.key,
            status=d.status,
            failure_reason=d.failure_reason,
            payload=d.payload,
            created_at=d.created_at,
            sent_at=d.sent_at,
        )
        for d in rows
    ]
    return AlertDeliveriesResponse(deliveries=deliveries)


@router.post(
    "/alerts/trigger/{alert_kind}",
    status_code=202,
    response_model=TriggerAlertResponse,
)
async def trigger_alert_scan(
    alert_kind: str,
    background_tasks: BackgroundTasks,
    db_factory: async_sessionmaker[AsyncSession] = Depends(get_db_factory),
    settings: Settings = Depends(get_settings),
) -> TriggerAlertResponse:
    """Manually trigger an alert scan and run sends inline (for testing and recovery).

    TODO: Add authentication before production deploy.
    """
    if alert_kind not in _ALERT_KINDS:
        raise ValidationError(
            f"alert_kind must be one of: {', '.join(sorted(_ALERT_KINDS))}",
            code="invalid_alert_kind",
        )

    job_id = str(uuid.uuid4())
    scan_fn = _SCAN_FN[alert_kind]
    send_fn = _SEND_FN[alert_kind]
    email_client = get_email_client()

    logger.info("alert_scan_triggered", alert_kind=alert_kind, job_id=job_id)

    async def _run_inline() -> None:
        queued: list[str] = []

        class _InlineRedis:
            async def enqueue_job(self, func_name: str, delivery_id: str) -> None:
                queued.append(delivery_id)

        ctx = {
            "session_factory": db_factory,
            "settings": settings,
            "email_client": email_client,
            "redis": _InlineRedis(),
        }
        try:
            await scan_fn(ctx)
        except Exception:
            logger.exception("alert_scan_failed", alert_kind=alert_kind, job_id=job_id)
            return

        for delivery_id in queued:
            try:
                await send_fn(ctx, delivery_id)
            except Exception:
                logger.exception(
                    "alert_send_failed",
                    alert_kind=alert_kind,
                    delivery_id=delivery_id,
                )

    background_tasks.add_task(_run_inline)
    return TriggerAlertResponse(job_id=job_id, alert_kind=alert_kind)


# ── Ingest admin endpoints ────────────────────────────────────────────────────


@router.get("/ingest/runs", response_model=IngestRunsResponse)
async def list_ingest_runs(
    source: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> IngestRunsResponse:
    """Last 20 ingest runs, optionally filtered by source.

    TODO: Add authentication before production deploy.
    """
    query = (
        sa.select(IngestRun)
        .order_by(IngestRun.started_at.desc())
        .limit(_MAX_RUNS)
    )
    if source is not None:
        query = query.where(IngestRun.source == source)
    result = await db.execute(query)
    runs = [IngestRunSummary.model_validate(r) for r in result.scalars().all()]
    return IngestRunsResponse(runs=runs)


@router.get("/ingest/runs/{run_id}", response_model=IngestRunDetail)
async def get_ingest_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> IngestRunDetail:
    """Full detail for a single ingest run.

    TODO: Add authentication before production deploy.
    """
    run = await db.get(IngestRun, run_id)
    if run is None:
        raise NotFoundError("Ingest run not found")
    return IngestRunDetail.model_validate(run)


@router.post(
    "/ingest/trigger/{source}",
    status_code=202,
    response_model=IngestTriggerResponse,
)
async def trigger_ingest_run(
    source: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db_factory: async_sessionmaker[AsyncSession] = Depends(get_db_factory),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> IngestTriggerResponse:
    """Manually trigger an ingest run for the given source. Returns 202 immediately.

    409 if the source is already ingesting.
    404 if the source name is unknown.

    TODO: Add authentication before production deploy.
    """
    if get_adapter(source) is None:
        raise NotFoundError(f"Unknown ingest source: {source}")

    lock_key = f"ingest:{source}:lock"
    existing = await redis.get(lock_key)
    if existing:
        raise ConflictError(
            "Ingest already in progress",
            code="ingest_in_progress",
            extra={"run_id": existing},
        )

    run_id = uuid.uuid4()
    session_id = getattr(request.state, "session_id", None)

    logger.info(
        "ingest_trigger",
        source=source,
        run_id=str(run_id),
        session_id=session_id,
    )

    background_tasks.add_task(
        run_ingest_sweep,
        source,
        db_factory,
        redis,
        settings,
        "manual",
        session_id,
        run_id,
    )

    return IngestTriggerResponse(run_id=run_id, source=source)
