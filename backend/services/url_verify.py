"""URL verification service.

Checks grant source URLs via HEAD (falling back to GET on 405), maps HTTP
results to source_status, and auto-archives grants with repeated 404/410.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import Settings
from backend.core.errors import ConflictError
from backend.core.logging import get_logger
from backend.db.models.grant import Grant
from backend.db.models.verification_run import VerificationRun

logger = get_logger(__name__)

_LOCK_KEY = "url_verify:lock"


@dataclass
class VerifyResult:
    source_status: str  # ok | redirect | gone | error
    last_verification_error: str | None
    new_consecutive_failures: int
    should_archive: bool


async def _try_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    settings: Settings,
) -> tuple[httpx.Response | None, str | None]:
    try:
        response = await client.request(
            method,
            url,
            follow_redirects=True,
            headers={"User-Agent": settings.URL_VERIFY_USER_AGENT},
            timeout=settings.URL_VERIFY_TIMEOUT_SECONDS,
        )
        return response, None
    except httpx.TimeoutException:
        return None, "timeout"
    except httpx.ConnectError as exc:
        msg = str(exc).lower()
        if any(k in msg for k in ("ssl", "certificate", "tls", "handshake")):
            return None, "SSL error"
        return None, "connection error"
    except httpx.RemoteProtocolError:
        return None, "protocol error"
    except Exception as exc:
        return None, type(exc).__name__


async def verify_grant_url(
    client: httpx.AsyncClient,
    grant: Grant,
    settings: Settings,
) -> VerifyResult:
    response, error = await _try_request(client, "HEAD", grant.url, settings)

    if response is not None and response.status_code == 405:
        # Some servers refuse HEAD — retry with GET
        response, error = await _try_request(client, "GET", grant.url, settings)

    if response is None:
        return VerifyResult(
            source_status="error",
            last_verification_error=error,
            new_consecutive_failures=grant.consecutive_failures,  # unchanged
            should_archive=False,
        )

    status = response.status_code

    if status in (404, 410):
        new_failures = grant.consecutive_failures + 1
        return VerifyResult(
            source_status="gone",
            last_verification_error=None,
            new_consecutive_failures=new_failures,
            should_archive=new_failures >= settings.URL_VERIFY_GONE_THRESHOLD,
        )

    if status == 200:
        had_redirects = len(response.history) > 0
        if had_redirects:
            logger.info(
                "grant_url_redirected",
                grant_id=str(grant.id),
                source_id=grant.source_id,
                final_url=str(response.url),
            )
            return VerifyResult(
                source_status="redirect",
                last_verification_error=None,
                new_consecutive_failures=grant.consecutive_failures,  # healthy — leave unchanged
                should_archive=False,
            )
        return VerifyResult(
            source_status="ok",
            last_verification_error=None,
            new_consecutive_failures=0,  # reset on success
            should_archive=False,
        )

    # 4xx (not 404/410/405) or 5xx — both transient-enough to not increment
    return VerifyResult(
        source_status="error",
        last_verification_error=f"HTTP {status}",
        new_consecutive_failures=grant.consecutive_failures,  # unchanged
        should_archive=False,
    )


async def run_verification_sweep(
    session_factory: async_sessionmaker[AsyncSession],
    redis,
    settings: Settings,
    triggered_by: str,
    triggered_session_id: str | None = None,
    pre_run_id: uuid.UUID | None = None,
) -> VerificationRun | None:
    run_id = pre_run_id or uuid.uuid4()
    log = logger.bind(job_id=str(run_id), triggered_by=triggered_by)

    acquired = await redis.set(
        _LOCK_KEY,
        str(run_id),
        nx=True,
        ex=settings.URL_VERIFY_REDIS_LOCK_TTL_SECONDS,
    )
    if not acquired:
        in_progress = await redis.get(_LOCK_KEY)
        log.info("url_verify_skipped_locked", in_progress_run_id=in_progress)
        if triggered_by == "manual":
            raise ConflictError(
                "Verification already in progress",
                code="verification_in_progress",
                extra={"run_id": in_progress},
            )
        return None

    started_at = datetime.now(timezone.utc)
    log.info("url_verify_started")

    async with session_factory() as s:
        run = VerificationRun(
            id=run_id,
            started_at=started_at,
            triggered_by=triggered_by,
            triggered_session_id=triggered_session_id,
        )
        s.add(run)
        await s.commit()

    counters = {"checked": 0, "ok": 0, "failed": 0, "archived": 0}
    run_error: str | None = None

    try:
        async with session_factory() as s:
            result = await s.execute(
                sa.select(Grant).where(Grant.status == "active")
            )
            grants = list(result.scalars().all())

        sem = asyncio.Semaphore(settings.URL_VERIFY_CONCURRENCY)

        async def _process(grant: Grant) -> None:
            async with sem:
                async with httpx.AsyncClient(max_redirects=5) as http_client:
                    verify_result = await verify_grant_url(http_client, grant, settings)

                async with session_factory() as s:
                    db_grant = await s.get(Grant, grant.id)
                    if db_grant is None:
                        return
                    db_grant.source_status = verify_result.source_status
                    db_grant.last_verified_at = datetime.now(timezone.utc)
                    db_grant.last_verification_error = verify_result.last_verification_error
                    db_grant.consecutive_failures = verify_result.new_consecutive_failures
                    db_grant.updated_at = datetime.now(timezone.utc)
                    if verify_result.should_archive:
                        db_grant.status = "archived"
                        log.warning(
                            "grant_archived",
                            grant_id=str(grant.id),
                            source_id=grant.source_id,
                            consecutive_failures=verify_result.new_consecutive_failures,
                        )
                        counters["archived"] += 1
                    await s.commit()

                counters["checked"] += 1
                if verify_result.source_status in ("ok", "redirect"):
                    counters["ok"] += 1
                else:
                    counters["failed"] += 1

        await asyncio.gather(*[_process(g) for g in grants])

    except Exception as exc:
        run_error = str(exc)[:500]
        log.exception("url_verify_sweep_error")

    finally:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        try:
            async with session_factory() as s:
                db_run = await s.get(VerificationRun, run_id)
                if db_run is not None:
                    db_run.finished_at = finished_at
                    db_run.grants_checked = counters["checked"]
                    db_run.grants_ok = counters["ok"]
                    db_run.grants_failed = counters["failed"]
                    db_run.grants_archived = counters["archived"]
                    db_run.duration_ms = duration_ms
                    db_run.error = run_error
                    await s.commit()
        except Exception:
            log.exception("url_verify_run_finalize_error")

        await redis.delete(_LOCK_KEY)
        log.info("url_verify_finished", duration_ms=duration_ms, **counters)

    async with session_factory() as s:
        return await s.get(VerificationRun, run_id)
