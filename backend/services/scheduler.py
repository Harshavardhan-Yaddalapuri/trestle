"""In-process scheduler for background jobs.

Launches an asyncio task that runs url_verify_sweep on a weekly interval.
The Redis lock in run_verification_sweep prevents duplicate sweeps when
multiple workers are running.
"""
from __future__ import annotations

import asyncio
import random

from backend.core.config import get_settings
from backend.core.logging import get_logger
from backend.db.session import get_session_factory
from backend.redis_client import get_redis_client
from backend.services.url_verify import run_verification_sweep

logger = get_logger(__name__)


async def url_verify_scheduler() -> None:
    settings = get_settings()
    jitter = random.uniform(0, 60)
    logger.info("url_verify_scheduler_started", jitter_seconds=round(jitter, 1))

    await asyncio.sleep(jitter)

    while True:
        if settings.URL_VERIFY_ENABLED:
            try:
                factory = get_session_factory()
                redis = get_redis_client()
                await run_verification_sweep(
                    factory, redis, settings, triggered_by="schedule"
                )
            except Exception:
                logger.exception("scheduler_run_failed")

        await asyncio.sleep(settings.URL_VERIFY_INTERVAL_HOURS * 3600)
