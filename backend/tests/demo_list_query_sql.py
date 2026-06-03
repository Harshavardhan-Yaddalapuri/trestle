"""Emit the actual SQL the conversations list endpoint runs.

Boots the same SQLite + fakeredis stack the test suite uses, populates two
conversations, then runs GET /api/conversations against an engine configured
with ``echo=True``. The point is to make it visible that the list is a single
SELECT with correlated subqueries for message_count and last_message_preview
— not an N+1.

Run with:
    .venv-scaffold\\Scripts\\python.exe -m backend.tests.demo_list_query_sql
"""
from __future__ import annotations

import asyncio
import logging
import sys

from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.db.base import Base
from backend.db.session import get_db, get_db_factory
from backend.main import create_app
from backend.redis_client import get_redis


async def main() -> None:
    # echo=True funnels every statement into the sqlalchemy.engine logger.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        echo=True,
    )

    # Route engine output to stdout so it lines up with the demo's own prints.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[sql] %(message)s"))
    engine_log = logging.getLogger("sqlalchemy.engine")
    engine_log.handlers.clear()
    engine_log.addHandler(handler)
    engine_log.setLevel(logging.INFO)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    redis = FakeAsyncRedis(decode_responses=True)

    app = create_app()

    async def _db():
        async with factory() as s:
            yield s

    async def _redis():
        yield redis

    def _factory():
        return factory

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_redis] = _redis
    app.dependency_overrides[get_db_factory] = _factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://demo") as client:
        # Seed two conversations so the subqueries have rows to operate on.
        for text in ("seed one", "seed two"):
            async with client.stream(
                "POST",
                "/api/chat/message",
                json={"content": text},
                headers={"X-Session-Id": "demo-list-sql"},
            ) as resp:
                async for _line in resp.aiter_lines():
                    pass

        print("\n=== executing GET /api/conversations ===\n", flush=True)
        res = await client.get(
            "/api/conversations",
            headers={"X-Session-Id": "demo-list-sql"},
        )
        print("\n=== response status:", res.status_code, "===\n", flush=True)
        print(res.json())

    try:
        await redis.aclose()
    except AttributeError:
        await redis.close()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
