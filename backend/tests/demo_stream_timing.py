"""Wall-clock SSE timing demo.

Starts an in-process uvicorn server wired to in-memory SQLite + fakeredis,
then makes a real HTTP request and prints each SSE event with its elapsed
timestamp. Real HTTP transport is required to observe streaming -- httpx's
ASGITransport buffers response bodies and would print all events at once.

Run with:
    .venv-scaffold\\Scripts\\python.exe -m backend.tests.demo_stream_timing
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import socket
import time

import httpx
import uvicorn
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.db.base import Base
from backend.db.session import get_db, get_db_factory
from backend.main import create_app
from backend.redis_client import get_redis


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
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

    port = _free_port()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        lifespan="on",
    )
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    # Wait for the server to become ready.
    for _ in range(50):
        if server.started:
            break
        await asyncio.sleep(0.05)

    base = f"http://127.0.0.1:{port}"

    try:
        async with httpx.AsyncClient(base_url=base, timeout=10.0) as client:
            start = time.perf_counter()
            print(f"{'elapsed':>10s}  event             data")
            print("-" * 80)

            async with client.stream(
                "POST",
                "/api/chat/message",
                json={"content": "stream timing please"},
                headers={"X-Session-Id": "demo-session"},
            ) as resp:
                assert resp.status_code == 200, await resp.aread()
                current_event = "message"
                current_data = ""
                async for line in resp.aiter_lines():
                    if line.startswith("event: "):
                        current_event = line[7:]
                    elif line.startswith("data: "):
                        current_data += line[6:]
                    elif line == "" and current_data:
                        elapsed_ms = (time.perf_counter() - start) * 1000
                        try:
                            parsed = json.loads(current_data)
                        except json.JSONDecodeError:
                            parsed = current_data
                        short = json.dumps(parsed)
                        if len(short) > 60:
                            short = short[:57] + "..."
                        print(
                            f"{elapsed_ms:9.1f}ms  {current_event:<17s} {short}"
                        )
                        current_event = "message"
                        current_data = ""
    finally:
        server.should_exit = True
        with contextlib.suppress(asyncio.CancelledError):
            await server_task
        try:
            await redis.aclose()
        except AttributeError:
            await redis.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
