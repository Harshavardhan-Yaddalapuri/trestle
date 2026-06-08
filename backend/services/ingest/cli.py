"""Manual ingest CLI for local testing.

Usage:
    python -m backend.services.ingest.cli grantsgov
    python -m backend.services.ingest.cli grantsgov --dry-run
"""
from __future__ import annotations

import asyncio
import sys

from backend.core.config import get_settings
from backend.core.logging import configure_logging, get_logger
from backend.db.session import dispose_engine, get_session_factory, init_engine
from backend.redis_client import close_redis, init_redis
from backend.services.ingest.orchestration import run_ingest_sweep


async def _run(source: str) -> None:
    init_engine()
    init_redis()

    settings = get_settings()
    factory = get_session_factory()
    redis = init_redis()

    logger = get_logger(__name__)
    logger.info("ingest_cli_start", source=source)

    try:
        run = await run_ingest_sweep(
            source,
            factory,
            redis,
            settings,
            triggered_by="manual",
            triggered_session_id="cli",
        )
        if run is None:
            print(f"[ingest-cli] Skipped — lock already held for source '{source}'")
            return

        print(
            f"[ingest-cli] {source} complete:\n"
            f"  run_id   = {run.id}\n"
            f"  fetched  = {run.records_fetched}\n"
            f"  inserted = {run.records_inserted}\n"
            f"  updated  = {run.records_updated}\n"
            f"  skipped  = {run.records_skipped}\n"
            f"  archived = {run.records_archived}\n"
            f"  duration = {run.duration_ms} ms\n"
            f"  error    = {run.error or 'none'}"
        )
    finally:
        await close_redis()
        await dispose_engine()


def main() -> None:
    configure_logging()
    if len(sys.argv) < 2:
        print("Usage: python -m backend.services.ingest.cli <source>")
        sys.exit(1)
    source = sys.argv[1]
    asyncio.run(_run(source))


if __name__ == "__main__":
    main()
