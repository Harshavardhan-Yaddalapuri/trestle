"""Arq queue pool for enqueueing jobs from FastAPI request handlers."""
from __future__ import annotations

from arq.connections import ArqRedis, RedisSettings, create_pool

from backend.core.config import get_settings

_arq_pool: ArqRedis | None = None


async def get_arq_queue() -> ArqRedis:
    global _arq_pool
    if _arq_pool is None:
        settings = get_settings()
        _arq_pool = await create_pool(
            RedisSettings.from_dsn(settings.REDIS_URL),
            default_queue_name=settings.ARQ_QUEUE_NAME,
        )
    return _arq_pool
