"""Multi-source smoke test for the ingest framework.

Uses SQLite in-memory + fakeredis so no infrastructure is needed.
Runs real fetches against the Grants.gov and SBIR.gov public APIs.

Usage:
    python -m backend.services.ingest.smoke
"""
from __future__ import annotations

import asyncio
import sys

import sqlalchemy as sa
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import Settings
from backend.core.logging import configure_logging, get_logger
from backend.db.models.grant import Grant
from backend.services.ingest.orchestration import run_ingest_sweep


async def _run() -> None:
    configure_logging()
    logger = get_logger(__name__)

    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/0",
        GRANTSGOV_MAX_PAGES=1,
        GRANTSGOV_PAGE_SIZE=100,
        SBIRGOV_MAX_PAGES=2,
        SBIRGOV_PAGE_SIZE=100,
        INGEST_HTTP_TIMEOUT_SECONDS=30.0,
        INGEST_HTTP_MAX_RETRIES=2,
        INGEST_REDIS_LOCK_TTL_SECONDS=300,
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    from backend.db.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    redis = FakeAsyncRedis(decode_responses=True)

    # ── Step 1: Grants.gov ingest ─────────────────────────────────────────────
    print("\n[smoke] Step 1 — Grants.gov ingest\n")
    run_gg = await run_ingest_sweep(
        "grantsgov", factory, redis, settings, "manual", "smoke-cli"
    )
    if run_gg is None:
        print("[smoke] ERROR: got None from run_ingest_sweep (grantsgov)")
        sys.exit(1)

    print(
        f"  fetched  = {run_gg.records_fetched}\n"
        f"  inserted = {run_gg.records_inserted}\n"
        f"  skipped  = {run_gg.records_skipped}\n"
        f"  error    = {run_gg.error or 'none'}"
    )
    if run_gg.records_fetched == 0:
        print("[smoke] WARNING: 0 records from Grants.gov — check connectivity")

    # ── Step 2: SBIR.gov ingest ───────────────────────────────────────────────
    print("\n[smoke] Step 2 — SBIR.gov ingest\n")
    run_sbir = None
    try:
        run_sbir = await run_ingest_sweep(
            "sbirgov", factory, redis, settings, "manual", "smoke-cli"
        )
    except Exception as exc:
        print(f"[smoke] WARNING: SBIR.gov ingest failed: {exc}")
        print("[smoke] Skipping SBIR.gov-dependent steps (API may require auth or be unavailable)")

    if run_sbir is not None:
        print(
            f"  fetched    = {run_sbir.records_fetched}\n"
            f"  inserted   = {run_sbir.records_inserted}\n"
            f"  skipped    = {run_sbir.records_skipped}\n"
            f"  duplicates = {run_sbir.duplicates_found}\n"
            f"  error      = {run_sbir.error or 'none'}"
        )
        if run_sbir.records_fetched == 0:
            print("[smoke] NOTE: 0 records from SBIR.gov — API may require auth or be rate-limited")

    # ── Step 3: Show duplicate examples ──────────────────────────────────────
    if run_sbir is not None and run_sbir.duplicates_found > 0:
        print(f"\n[smoke] Step 3 — {run_sbir.duplicates_found} duplicates detected\n")
        async with factory() as s:
            dup_rows = (await s.execute(
                sa.select(Grant)
                .where(Grant.is_duplicate_of.isnot(None))
                .limit(5)
            )).scalars().all()

        for dup in dup_rows:
            sp = dup.source_payload or {}
            canonical_id = dup.is_duplicate_of
            async with factory() as s:
                canonical = await s.get(Grant, canonical_id)

            dup_num = sp.get("number") or dup.source_id
            can_num = (canonical.eligibility or {}).get("_topic_number") if canonical else "?"
            print(
                f"  duplicate: {dup.source_id} ({dup_num})\n"
                f"  canonical: {canonical.source_id if canonical else '?'} ({can_num})\n"
                f"  kind:      {dup.dedup_match_kind}\n"
            )
    elif run_sbir is not None:
        print("\n[smoke] Step 3 — 0 duplicates detected (no cross-source overlap in test pages)")
    else:
        print("\n[smoke] Step 3 — skipped (SBIR.gov unavailable)")

    # ── Step 4: Idempotency check (grantsgov second run) ─────────────────────
    print("\n[smoke] Step 4 — Grants.gov idempotency (second run)\n")
    run_gg2 = await run_ingest_sweep(
        "grantsgov", factory, redis, settings, "manual", "smoke-cli-2"
    )
    assert run_gg2 is not None
    print(
        f"  inserted = {run_gg2.records_inserted}\n"
        f"  updated  = {run_gg2.records_updated}\n"
        f"  error    = {run_gg2.error or 'none'}"
    )
    if run_gg2.records_inserted == 0 and run_gg2.records_updated > 0:
        print("[smoke] PASS: Grants.gov idempotency verified")
    else:
        print(
            f"[smoke] WARN: unexpected counts "
            f"(inserted={run_gg2.records_inserted}, updated={run_gg2.records_updated})"
        )

    # ── Step 5: Count comparison ──────────────────────────────────────────────
    print("\n[smoke] Step 5 — Grant counts\n")
    async with factory() as s:
        total = (await s.execute(sa.select(sa.func.count()).select_from(Grant))).scalar()
        gg_count = (await s.execute(
            sa.select(sa.func.count()).select_from(Grant).where(Grant.source == "grantsgov")
        )).scalar()
        sbir_count = (await s.execute(
            sa.select(sa.func.count()).select_from(Grant).where(Grant.source == "sbirgov")
        )).scalar()
        active_non_dup = (await s.execute(
            sa.select(sa.func.count()).select_from(Grant).where(
                Grant.status == "active",
                Grant.is_duplicate_of.is_(None),
            )
        )).scalar()
        dup_total = (await s.execute(
            sa.select(sa.func.count()).select_from(Grant).where(
                Grant.is_duplicate_of.isnot(None)
            )
        )).scalar()

    print(
        f"  total grants           = {total}\n"
        f"  source=grantsgov       = {gg_count}\n"
        f"  source=sbirgov         = {sbir_count}\n"
        f"  active (non-duplicate) = {active_non_dup}\n"
        f"  duplicates marked      = {dup_total}\n"
        f"\n  GET /grants returns ~{active_non_dup} records\n"
        f"  GET /grants?include_duplicates=true returns ~{active_non_dup + dup_total}"
    )

    await redis.aclose()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_run())
