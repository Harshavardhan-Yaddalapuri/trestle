from typing import AsyncIterator

from redis.asyncio import Redis, from_url

from backend.core.config import get_settings

_redis: Redis | None = None


def init_redis() -> Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


def get_redis_client() -> Redis:
    if _redis is None:
        return init_redis()
    return _redis


async def get_redis() -> AsyncIterator[Redis]:
    yield get_redis_client()
