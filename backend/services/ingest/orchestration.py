"""Ingest orchestration — coordinates fetch → filter → upsert → audit.

run_ingest_sweep mirrors run_verification_sweep / run_lifecycle_auto_sweep:
Redis-lock-guarded, one audit row per run, per-source locks so adapters
don't block each other.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import Settings
from backend.core.errors import ConflictError, ValidationError
from backend.core.logging import get_logger
from backend.db.models.ingest_run import IngestRun
from backend.services.ingest.dedup import run_dedup_pass
from backend.services.ingest.filters import startup_relevance_filter
from backend.services.ingest.registry import get_adapter
from backend.services.ingest.upsert import archive_missing_grants, upsert_ingested_grants

logger = get_logger(__name__)

_BATCH_SIZE = 100


def _lock_key(source: str) -> str:
    return f"ingest:{source}:lock"


async def run_ingest_sweep(
    source: str,
    session_factory: async_sessionmaker[AsyncSession],
    redis: object,
    settings: Settings,
    triggered_by: str,
    triggered_session_id: str | None = None,
    pre_run_id: uuid.UUID | None = None,
) -> IngestRun | None:
    lock_key = _lock_key(source)
    run_id = pre_run_id or uuid.uuid4()
    log = logger.bind(job_id=str(run_id), source=source, triggered_by=triggered_by)

    # Validate source before acquiring lock
    adapter_class = get_adapter(source)
    if adapter_class is None:
        raise ValidationError(f"Unknown ingest source: {source}", code="unknown_source")

    if source == "grantsgov" and not settings.GRANTSGOV_ENABLED:
        raise ValidationError(
            f"Ingest source disabled: {source}", code="source_disabled"
        )
    if source == "sbirgov" and not settings.SBIRGOV_ENABLED:
        raise ValidationError(
            f"Ingest source disabled: {source}", code="source_disabled"
        )

    acquired = await redis.set(  # type: ignore[union-attr]
        lock_key,
        str(run_id),
        nx=True,
        ex=settings.INGEST_REDIS_LOCK_TTL_SECONDS,
    )
    if not acquired:
        in_progress = await redis.get(lock_key)  # type: ignore[union-attr]
        log.info("ingest_skipped_locked", in_progress_run_id=in_progress)
        if triggered_by == "manual":
            raise ConflictError(
                "Ingest already in progress",
                code="ingest_in_progress",
                extra={"run_id": in_progress},
            )
        return None

    started_at = datetime.now(timezone.utc)
    log.info("ingest_sweep_started")

    async with session_factory() as s:
        run = IngestRun(
            id=run_id,
            source=source,
            triggered_by=triggered_by,
            triggered_session_id=triggered_session_id,
            started_at=started_at,
        )
        s.add(run)
        await s.commit()

    counters: dict[str, int] = {
        "fetched": 0,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "archived": 0,
        "duplicates_found": 0,
    }
    run_error: str | None = None
    fetched_at = started_at
    fresh_source_ids: set[str] = set()
    buffer: list = []

    async def _flush() -> None:
        if not buffer:
            return
        async with session_factory() as s:
            ins, upd = await upsert_ingested_grants(s, source, list(buffer), fetched_at)
        counters["inserted"] += ins
        counters["updated"] += upd
        buffer.clear()

    adapter = adapter_class()

    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": settings.INGEST_USER_AGENT},
            timeout=settings.INGEST_HTTP_TIMEOUT_SECONDS,
        ) as http_client:
            async for record in adapter.fetch_all(http_client, settings, since=None):
                counters["fetched"] += 1

                kept, skip_reason = startup_relevance_filter(record)
                if not kept:
                    counters["skipped"] += 1
                    log.debug(
                        "ingest_record_filtered",
                        source_id=record.source_id,
                        reason=skip_reason,
                    )
                    continue

                fresh_source_ids.add(record.source_id)
                buffer.append(record)

                if len(buffer) >= _BATCH_SIZE:
                    await _flush()

        await _flush()

        if counters["fetched"] == 0:
            log.warning("ingest_archive_sweep_skipped_empty_fetch", source=source)
        else:
            async with session_factory() as s:
                archived = await archive_missing_grants(
                    s, source, fresh_source_ids, fetched_at
                )
            counters["archived"] = archived

            async with session_factory() as s:
                dedup_result = await run_dedup_pass(s, source, fresh_source_ids)
            counters["duplicates_found"] = dedup_result.duplicates_found

    except Exception as exc:
        run_error = str(exc)[:500]
        log.exception("ingest_sweep_error")
        if triggered_by == "manual":
            raise

    finally:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        try:
            async with session_factory() as s:
                db_run = await s.get(IngestRun, run_id)
                if db_run is not None:
                    db_run.finished_at = finished_at
                    db_run.records_fetched = counters["fetched"]
                    db_run.records_inserted = counters["inserted"]
                    db_run.records_updated = counters["updated"]
                    db_run.records_skipped = counters["skipped"]
                    db_run.records_archived = counters["archived"]
                    db_run.duplicates_found = counters["duplicates_found"]
                    db_run.duration_ms = duration_ms
                    db_run.error = run_error
                    await s.commit()
        except Exception:
            log.exception("ingest_run_finalize_error")

        await redis.delete(lock_key)  # type: ignore[union-attr]
        log.info("ingest_sweep_finished", duration_ms=duration_ms, **counters)

    async with session_factory() as s:
        return await s.get(IngestRun, run_id)
