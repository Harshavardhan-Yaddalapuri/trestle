"""Health check endpoints — public, no auth required."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from jwt import PyJWKClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.db.session import get_db
from backend.redis_client import get_redis

root_router = APIRouter()
api_router = APIRouter()


@root_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@root_router.get("/health/deep")
async def health_deep(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    settings = get_settings()

    db_status = await _check_db(db)
    redis_status = await _check_redis(redis)
    supabase_jwks = await _check_supabase_jwks(settings)

    results = {
        "database": db_status,
        "redis": redis_status,
        "supabase_jwks": supabase_jwks,
    }
    overall = (
        "deep_check_complete"
        if all(r.get("status") == "ok" for r in results.values())
        else "degraded"
    )
    return {
        "status": overall,
        "results": results,
    }


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


async def _check_supabase_jwks(settings) -> dict[str, Any]:
    if not settings.SUPABASE_URL:
        return {"status": "skipped", "reason": "SUPABASE_URL not set"}
    try:
        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        client = PyJWKClient(jwks_url, cache_keys=True, cache_jwk_set=True)
        # Just verify we can fetch the JWKS
        keys = client.fetch_data()
        return {"status": "ok", "keys_found": len(keys.get("keys", []))}
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
        "database": db_status,
        "redis": redis_status,
    }
