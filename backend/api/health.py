from typing import Any

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.redis_client import get_redis

root_router = APIRouter()
api_router = APIRouter()


@root_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def _check_db(db: AsyncSession) -> dict[str, Any]:
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "error": str(exc.__class__.__name__)}


async def _check_redis(redis: Redis) -> dict[str, Any]:
    try:
        pong = await redis.ping()
        return {"status": "ok" if pong else "error"}
    except Exception as exc:
        return {"status": "error", "error": str(exc.__class__.__name__)}


@api_router.get("/health")
async def api_health(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    db_status = await _check_db(db)
    redis_status = await _check_redis(redis)
    overall = (
        "ok"
        if db_status["status"] == "ok" and redis_status["status"] == "ok"
        else "degraded"
    )
    return {
        "status": overall,
        "db": db_status,
        "redis": redis_status,
    }
