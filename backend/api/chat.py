from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import Settings, get_settings
from backend.core.errors import GoneError, NotFoundError
from backend.core.logging import get_logger
from backend.db.models.chat import Conversation, Message
from backend.db.session import get_db, get_db_factory
from backend.middleware.auth import get_identity, owner_clause
from backend.redis_client import get_redis
from backend.schemas.chat import ChatMessageIn
from backend.services.chat_stream import (
    ACTIVE_TTL,
    TERMINAL_TTL,
    append_event,
    format_sse,
    job_key,
    read_stream,
    set_terminal_ttl,
    stream_key,
)
from backend.services.llm.base import LLMClient
from backend.services.llm.dependency import get_llm_client
from backend.services.llm_stub import stub_token_stream

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger(__name__)

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _resolve_conversation(
    db: AsyncSession, user_id: str | None, session_id: str, conversation_id: uuid.UUID | None
) -> Conversation:
    """Load an existing conversation for this user/session, or create a new one."""
    if conversation_id is None:
        convo = Conversation(user_id=user_id, session_id=session_id)
        db.add(convo)
        await db.flush()
        return convo

    convo = await db.get(Conversation, conversation_id)
    # Return a 404 (not 403) for any access failure to avoid leaking existence.
    if convo is None or convo.deleted_at is not None:
        raise NotFoundError("Conversation not found")
    # Re-check ownership
    if user_id:
        if convo.user_id != user_id and convo.session_id != session_id:
            raise NotFoundError("Conversation not found")
    else:
        if convo.session_id != session_id:
            raise NotFoundError("Conversation not found")
    return convo


async def _run_producer(
    redis: Redis,
    session_factory: async_sessionmaker[AsyncSession],
    job_id: str,
    conversation_id: uuid.UUID,
    user_content: str,
    user_id: str | None,
    session_id: str,
    llm_client: LLMClient | None,
    settings: Settings,
) -> None:
    """Background producer: emits tokens → persists assistant message →
    emits message_saved → emits done → drops TTL to TERMINAL_TTL.

    On client disconnect (CancelledError), generation stops but persistence +
    done + TTL transition are shielded so they still complete.
    """
    s_key = stream_key(job_id)
    j_key = job_key(job_id)
    full_text = ""
    finish_reason = "stop"
    error_emitted = False

    try:
        if settings.CHAT_USE_ORCHESTRATOR:
            if llm_client is None:
                raise RuntimeError("llm_client_not_available")
            from backend.services.orchestrator import run_turn
            from backend.services.orchestrator.events import (
                FinishEvent,
                LLMTokenEvent,
                QuestionEvent,
                ToolCallEvent,
                ToolResultEvent,
            )

            async for event in run_turn(
                session_id=session_id,
                conversation_id=conversation_id,
                user_message=user_content,
                llm_client=llm_client,
                session_factory=session_factory,
                settings=settings,
            ):
                if isinstance(event, LLMTokenEvent):
                    await append_event(redis, s_key, "token", {"delta": event.delta})
                    full_text += event.delta
                elif isinstance(event, ToolCallEvent):
                    await append_event(
                        redis, s_key, "tool_call", {"name": event.name, "args": event.args}
                    )
                elif isinstance(event, ToolResultEvent):
                    await append_event(
                        redis, s_key, "tool_result", {"name": event.name, "result": event.result}
                    )
                elif isinstance(event, QuestionEvent):
                    prefix = "\n\n"
                    await append_event(redis, s_key, "token", {"delta": prefix})
                    full_text += prefix
                    await append_event(redis, s_key, "token", {"delta": event.question_text})
                    full_text += event.question_text
                    await append_event(
                        redis,
                        s_key,
                        "question_suggested",
                        {
                            "field": event.profile_field,
                            "question": event.question_text,
                            "options": event.options,
                        },
                    )
                elif isinstance(event, FinishEvent):
                    finish_reason = event.reason
        else:
            # Stub fallback — used when CHAT_USE_ORCHESTRATOR=False
            async for delta in stub_token_stream(user_content):
                await append_event(redis, s_key, "token", {"delta": delta})
                full_text += delta

    except asyncio.CancelledError:
        # Client disconnected — keep whatever we have and persist it.
        finish_reason = "stop"
    except asyncio.TimeoutError:
        finish_reason = "error"
        try:
            await append_event(
                redis,
                s_key,
                "error",
                {"code": "orchestrator_timeout", "message": "Turn took too long"},
            )
            error_emitted = True
        except Exception:  # noqa: BLE001
            pass
        logger.warning("orchestrator_timeout", job_id=job_id)
    except Exception as exc:  # noqa: BLE001
        finish_reason = "error"
        try:
            await append_event(
                redis,
                s_key,
                "error",
                {"code": "internal", "message": type(exc).__name__},
            )
            error_emitted = True
        except Exception:  # noqa: BLE001
            pass
        logger.exception("chat_producer_failed", job_id=job_id)

    async def _finalize() -> None:
        nonlocal finish_reason
        msg_id: str | None = None
        created_at_iso: str | None = None
        content_persisted = full_text
        try:
            async with session_factory() as db:
                msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_text,
                )
                db.add(msg)
                await db.execute(
                    sa.update(Conversation)
                    .where(Conversation.id == conversation_id)
                    .values(updated_at=datetime.now(timezone.utc))
                )
                await db.commit()
                await db.refresh(msg)
                msg_id = str(msg.id)
                created_at_iso = (
                    msg.created_at.isoformat() if msg.created_at else _utcnow_iso()
                )
            await append_event(
                redis,
                s_key,
                "message_saved",
                {
                    "message_id": msg_id,
                    "role": "assistant",
                    "content": content_persisted,
                    "created_at": created_at_iso,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("chat_persistence_failed", job_id=job_id)
            if not error_emitted:
                try:
                    await append_event(
                        redis,
                        s_key,
                        "error",
                        {
                            "code": "persistence_failed",
                            "message": type(exc).__name__,
                        },
                    )
                except Exception:  # noqa: BLE001
                    pass
            if finish_reason == "stop":
                finish_reason = "error"

        await append_event(redis, s_key, "done", {"finish_reason": finish_reason})
        await set_terminal_ttl(redis, s_key, j_key, TERMINAL_TTL)

    # Shield so a cancellation arriving during finalize still lets it complete.
    await asyncio.shield(_finalize())


@router.post("/message")
async def post_message(
    request: Request,
    body: ChatMessageIn,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_db_factory),
    llm_client: LLMClient = Depends(get_llm_client),
) -> StreamingResponse:
    user_id, session_id = get_identity(request)
    settings = get_settings()

    convo = await _resolve_conversation(db, user_id, session_id, body.conversation_id)

    # Persist the user message before streaming starts.
    user_msg = Message(
        conversation_id=convo.id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    await db.execute(
        sa.update(Conversation)
        .where(Conversation.id == convo.id)
        .values(updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    await db.refresh(convo)

    job_id = str(uuid.uuid4())
    s_key = stream_key(job_id)
    j_key = job_key(job_id)

    # Owner record for the resume endpoint.
    owner = user_id or session_id
    await redis.set(j_key, owner, ex=ACTIVE_TTL)

    # Emit job_started synchronously so the stream exists before we hand the
    # consumer a response — avoids the consumer racing ahead of an empty key.
    await append_event(
        redis,
        s_key,
        "job_started",
        {
            "job_id": job_id,
            "conversation_id": str(convo.id),
            "created_at": _utcnow_iso(),
        },
        ttl=ACTIVE_TTL,
    )

    producer = asyncio.create_task(
        _run_producer(
            redis,
            session_factory,
            job_id,
            convo.id,
            body.content,
            user_id,
            session_id,
            llm_client,
            settings,
        ),
        name=f"chat-producer:{job_id}",
    )

    async def body_iter():
        try:
            async for chunk in read_stream(redis, s_key, from_id="0"):
                yield chunk
        finally:
            if not producer.done():
                producer.cancel()

    return StreamingResponse(
        body_iter(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get("/stream/{job_id}")
async def stream_resume(
    request: Request,
    job_id: str,
    redis: Redis = Depends(get_redis),
) -> StreamingResponse:
    user_id, session_id = get_identity(request)
    s_key = stream_key(job_id)
    j_key = job_key(job_id)

    owner = await redis.get(j_key)
    stream_exists = await redis.exists(s_key)

    if owner is None or not stream_exists:
        # TTL has expired (or the job never existed). Either way the stream
        # backlog is gone — clients can't resume.
        raise GoneError("Stream no longer available")

    expected_owner = user_id or session_id
    if owner != expected_owner:
        # Wrong session: return 404 to avoid letting callers enumerate job ids.
        raise NotFoundError("Stream not found")

    last_event_id = request.headers.get("Last-Event-ID") or "0"

    async def body_iter():
        async for chunk in read_stream(redis, s_key, from_id=last_event_id):
            yield chunk

    return StreamingResponse(
        body_iter(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


__all__ = ["router", "format_sse"]