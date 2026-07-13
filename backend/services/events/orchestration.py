"""Events discovery orchestration.

Follows the same lock-guarded scheduler/manual pattern used by grant ingest:
- one Redis lock to prevent overlapping runs
- schedule runs skip if locked
- manual runs raise ConflictError if locked
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import Settings
from backend.core.errors import ConflictError
from backend.core.logging import get_logger
from backend.services.events.discovery import discover_events_from_web, upsert_discovered_events

logger = get_logger(__name__)
_LOCK_KEY = "events:discover:lock"


@dataclass(slots=True)
class EventsDiscoveryRunResult:
    discovered: int
    inserted: int
    updated: int
    sources_scanned: int


async def run_events_discovery_sweep(
    session_factory: async_sessionmaker[AsyncSession],
    redis: object,
    settings: Settings,
    triggered_by: str,
    triggered_session_id: str | None = None,
) -> EventsDiscoveryRunResult | None:
    run_id = uuid.uuid4()
    log = logger.bind(
        job_id=str(run_id),
        triggered_by=triggered_by,
        triggered_session_id=triggered_session_id,
    )
    acquired = await redis.set(  # type: ignore[union-attr]
        _LOCK_KEY,
        str(run_id),
        nx=True,
        ex=settings.EVENTS_REDIS_LOCK_TTL_SECONDS,
    )
    if not acquired:
        in_progress = await redis.get(_LOCK_KEY)  # type: ignore[union-attr]
        log.info("events_discovery_skipped_locked", in_progress_run_id=in_progress)
        if triggered_by == "manual":
            raise ConflictError(
                "Events discovery already in progress",
                code="events_discovery_in_progress",
                extra={"run_id": in_progress},
            )
        return None

    started_at = datetime.now(UTC)
    log.info("events_discovery_started")
    try:
        discovered = await discover_events_from_web(settings)
        async with session_factory() as session:
            inserted, updated = await upsert_discovered_events(
                session,
                discovered,
                datetime.now(UTC),
            )
        result = EventsDiscoveryRunResult(
            discovered=len(discovered),
            inserted=inserted,
            updated=updated,
            sources_scanned=len(settings.EVENT_SOURCE_URLS_LIST),
        )
        duration_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
        log.info(
            "events_discovery_finished",
            duration_ms=duration_ms,
            discovered=result.discovered,
            inserted=result.inserted,
            updated=result.updated,
            sources_scanned=result.sources_scanned,
        )
        return result
    except Exception:
        log.exception("events_discovery_failed")
        if triggered_by == "manual":
            raise
        return None
    finally:
        await redis.delete(_LOCK_KEY)  # type: ignore[union-attr]
