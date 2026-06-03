from __future__ import annotations

import base64
import binascii
import json
import uuid
from datetime import datetime, timezone
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import NotFoundError, ValidationError
from backend.core.logging import get_logger
from backend.db.models.memory import AgentMemory
from backend.db.session import get_db
from backend.schemas.memory import MemoryContext, MemoryIn, MemoryListResponse, MemoryOut
from backend.services.memory import build_memory_context

router = APIRouter(prefix="/memory", tags=["memory"])
logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Cursor helpers ────────────────────────────────────────────────────────


def _encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
    raw = json.dumps({"c": created_at.isoformat(), "i": str(row_id)})
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + padding).encode())
        payload = json.loads(raw)
        return datetime.fromisoformat(payload["c"]), uuid.UUID(payload["i"])
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
        raise ValueError("invalid cursor") from exc


# ── Model → schema ────────────────────────────────────────────────────────


def _to_out(m: AgentMemory) -> MemoryOut:
    return MemoryOut(
        id=m.id,
        session_id=m.session_id,
        kind=m.kind,
        content=m.content,
        structured=m.structured or {},
        conversation_id=m.conversation_id,
        source_message_id=m.source_message_id,
        confidence=m.confidence,
        expires_at=m.expires_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.post("", status_code=201, response_model=MemoryOut)
async def create_memory(
    request: Request,
    body: MemoryIn,
    db: AsyncSession = Depends(get_db),
) -> MemoryOut:
    session_id = request.state.session_id
    mem = AgentMemory(
        session_id=session_id,
        conversation_id=body.conversation_id,
        kind=body.kind,
        content=body.content,
        structured=body.structured,
        source_message_id=body.source_message_id,
        confidence=body.confidence,
        expires_at=body.expires_at,
    )
    db.add(mem)
    await db.commit()
    await db.refresh(mem)
    return _to_out(mem)


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    request: Request,
    kind: str | None = Query(default=None),
    conversation_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> MemoryListResponse:
    session_id = request.state.session_id
    now = _utcnow()

    stmt = select(AgentMemory).where(
        AgentMemory.session_id == session_id,
        AgentMemory.deleted_at.is_(None),
        sa.or_(AgentMemory.expires_at.is_(None), AgentMemory.expires_at > now),
    )

    if kind is not None:
        stmt = stmt.where(AgentMemory.kind == kind)

    if conversation_id is not None:
        # Include memories linked to this conversation OR session-wide (NULL).
        stmt = stmt.where(
            sa.or_(
                AgentMemory.conversation_id == conversation_id,
                AgentMemory.conversation_id.is_(None),
            )
        )

    if cursor:
        try:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
        except ValueError as exc:
            raise ValidationError("Invalid cursor", code="invalid_cursor", status_code=400) from exc
        stmt = stmt.where(
            sa.or_(
                AgentMemory.created_at < cursor_created_at,
                sa.and_(
                    AgentMemory.created_at == cursor_created_at,
                    AgentMemory.id < cursor_id,
                ),
            )
        )

    stmt = stmt.order_by(AgentMemory.created_at.desc(), AgentMemory.id.desc()).limit(limit + 1)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    rows = list(rows[:limit])

    next_cursor = _encode_cursor(rows[-1].created_at, rows[-1].id) if has_more else None
    return MemoryListResponse(items=[_to_out(m) for m in rows], next_cursor=next_cursor)


@router.get("/context", response_model=MemoryContext)
async def get_memory_context(
    request: Request,
    conversation_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> MemoryContext:
    session_id = request.state.session_id
    now = _utcnow()

    stmt = select(AgentMemory).where(
        AgentMemory.session_id == session_id,
        AgentMemory.deleted_at.is_(None),
        sa.or_(AgentMemory.expires_at.is_(None), AgentMemory.expires_at > now),
    )

    if conversation_id is not None:
        stmt = stmt.where(
            sa.or_(
                AgentMemory.conversation_id == conversation_id,
                AgentMemory.conversation_id.is_(None),
            )
        )

    result = await db.execute(stmt)
    memories = list(result.scalars().all())
    return build_memory_context(memories)


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    request: Request,
    memory_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    session_id = request.state.session_id

    result = await db.execute(
        sa.update(AgentMemory)
        .where(
            AgentMemory.id == memory_id,
            AgentMemory.session_id == session_id,
            AgentMemory.deleted_at.is_(None),
        )
        .values(deleted_at=_utcnow())
    )
    if result.rowcount == 0:
        raise NotFoundError("Memory not found")
    await db.commit()
    return Response(status_code=204)
