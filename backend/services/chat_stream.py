"""Redis Streams helpers backing the chat SSE endpoints.

Two keys per job:
- chat:stream:{job_id}  — Redis Stream of SSE events (event + data fields).
- chat:job:{job_id}     — string holding the owning session_id for authz.

TTL is 10min while a job is active, set to 60s when the `done` event fires so
clients can briefly resume via Last-Event-ID.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from redis.asyncio import Redis

ACTIVE_TTL = 600  # 10 minutes while a job is running
TERMINAL_TTL = 60  # 60 seconds after done — enough to resume


def stream_key(job_id: str) -> str:
    return f"chat:stream:{job_id}"


def job_key(job_id: str) -> str:
    return f"chat:job:{job_id}"


async def append_event(
    redis: Redis,
    key: str,
    event: str,
    data: dict[str, Any],
    *,
    ttl: int | None = None,
) -> str:
    """XADD an event onto the stream. Returns the stream entry id."""
    payload = json.dumps(data, default=str)
    entry_id = await redis.xadd(key, {"event": event, "data": payload})
    if ttl is not None:
        await redis.expire(key, ttl)
    return entry_id


async def set_terminal_ttl(
    redis: Redis, stream_k: str, job_k: str, ttl: int = TERMINAL_TTL
) -> None:
    """Drop TTL on both keys from active to terminal."""
    await redis.expire(stream_k, ttl)
    await redis.expire(job_k, ttl)


def format_sse(entry_id: str, event: str, data_json: str) -> bytes:
    """Format one SSE frame: id + event + data (JSON) + blank line."""
    return f"id: {entry_id}\nevent: {event}\ndata: {data_json}\n\n".encode("utf-8")


async def read_stream(
    redis: Redis,
    key: str,
    *,
    from_id: str = "0",
    block_ms: int = 5000,
    count: int = 100,
    terminate_event: str = "done",
    idle_backoff: float = 0.05,
) -> AsyncIterator[bytes]:
    """Yield SSE-formatted bytes from a Redis Stream until `terminate_event`.

    `from_id` is exclusive (XREAD semantics): pass "0" to replay from the start,
    or a Last-Event-ID to resume.

    If the stream key disappears (TTL expiry), the iterator returns.
    """
    cursor = from_id
    while True:
        result = await redis.xread({key: cursor}, block=block_ms, count=count)
        if not result:
            # XREAD timed out (real Redis) or returned empty (fakeredis when no
            # data yet). If the stream is gone, end. Otherwise, brief back-off
            # to avoid spinning when the underlying client doesn't actually block.
            if not await redis.exists(key):
                return
            await asyncio.sleep(idle_backoff)
            continue
        for _stream_name, entries in result:
            for entry_id, fields in entries:
                event = fields.get("event", "message")
                data = fields.get("data", "")
                yield format_sse(entry_id, event, data)
                cursor = entry_id
                if event == terminate_event:
                    return
