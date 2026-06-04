"""Arq WorkerSettings — run with: arq backend.services.jobs.settings.WorkerSettings"""
from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings

from backend.core.config import get_settings
from backend.core.logging import configure_logging, get_logger
from backend.db.session import dispose_engine, get_session_factory, init_engine
from backend.services.email.dependency import get_email_client
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

logger = get_logger(__name__)


async def on_startup(ctx: dict) -> None:
    configure_logging()
    init_engine()
    settings = get_settings()
    ctx["session_factory"] = get_session_factory()
    ctx["email_client"] = get_email_client()
    ctx["settings"] = settings
    logger.info(
        "arq_worker_started",
        queue=settings.ARQ_QUEUE_NAME,
        max_jobs=10,
    )


async def on_shutdown(ctx: dict) -> None:
    await dispose_engine()
    logger.info("arq_worker_stopped")


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().REDIS_URL)


class WorkerSettings:
    functions = [
        enqueue_deadline_alerts,
        send_deadline_alert,
        enqueue_new_grant_alerts,
        send_new_grant_alert,
        enqueue_checkin_alerts,
        send_checkin_alert,
    ]
    cron_jobs = [
        # Daily at 13:00 UTC
        cron(enqueue_deadline_alerts, hour=13, minute=0),
        # Every 6 hours
        cron(enqueue_new_grant_alerts, hour={0, 6, 12, 18}, minute=0),
        # Monday at 14:00 UTC (weekday=0 = Monday in arq/ISO convention)
        cron(enqueue_checkin_alerts, weekday=0, hour=14, minute=0),
    ]
    redis_settings = _redis_settings()
    queue_name = get_settings().ARQ_QUEUE_NAME
    max_jobs = 10
    job_timeout = get_settings().ARQ_JOB_TIMEOUT_SECONDS
    max_tries = get_settings().ARQ_MAX_TRIES
    on_startup = on_startup
    on_shutdown = on_shutdown
