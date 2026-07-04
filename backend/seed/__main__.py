"""CLI entry point for the grant seed loader.

Usage: python -m backend.seed
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import get_settings
from backend.core.logging import configure_logging, get_logger
from backend.seed.loader import load_grants_from_dir, upsert_grants

GRANTS_DIR = Path(__file__).parent / "grants"


async def _run() -> None:
    configure_logging()
    logger = get_logger(__name__)

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, future=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        grants = load_grants_from_dir(GRANTS_DIR)
        async with factory() as session:
            inserted, updated = await upsert_grants(session, grants)
        logger.info("seed_complete", inserted=inserted, updated=updated)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_run())
