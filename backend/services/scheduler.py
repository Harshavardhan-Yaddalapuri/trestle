"""In-process scheduler for background jobs.

Two independent loops:
- url_verify_scheduler: weekly URL verification sweep
- lifecycle_auto_scheduler: daily automated lifecycle transitions

Each loop has its own Redis lock and independent jitter so they don't
wake on exactly the same second.
"""
from __future__ import annotations

import asyncio
import random

from backend.core.config import get_settings
from backend.core.logging import get_logger
from backend.db.session import get_session_factory
from backend.redis_client import get_redis_client
from backend.services.ingest.orchestration import run_ingest_sweep
from backend.services.ingest.registry import get_enabled_sources
from backend.services.lifecycle.auto_transitions import run_lifecycle_auto_sweep
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


async def lifecycle_auto_scheduler() -> None:
    settings = get_settings()
    jitter = random.uniform(0, 60)
    logger.info("lifecycle_auto_scheduler_started", jitter_seconds=round(jitter, 1))

    await asyncio.sleep(jitter)

    while True:
        if settings.LIFECYCLE_AUTO_TRANSITIONS_ENABLED:
            try:
                factory = get_session_factory()
                redis = get_redis_client()
                await run_lifecycle_auto_sweep(
                    factory, redis, settings, triggered_by="schedule"
                )
            except Exception:
                logger.exception("lifecycle_auto_scheduler_run_failed")

        await asyncio.sleep(settings.LIFECYCLE_AUTO_INTERVAL_HOURS * 3600)


async def ingest_scheduler() -> None:
    settings = get_settings()
    jitter = random.uniform(0, 60)
    logger.info("ingest_scheduler_started", jitter_seconds=round(jitter, 1))

    await asyncio.sleep(jitter)

    while True:
        if settings.INGEST_ENABLED:
            for source_name in get_enabled_sources(settings):
                try:
                    factory = get_session_factory()
                    redis = get_redis_client()
                    await run_ingest_sweep(
                        source_name, factory, redis, settings, triggered_by="schedule"
                    )
                except Exception:
                    logger.exception(
                        "ingest_scheduler_run_failed", source=source_name
                    )

        await asyncio.sleep(settings.INGEST_INTERVAL_HOURS * 3600)
