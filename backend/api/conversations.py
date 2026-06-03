from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import NotFoundError, ValidationError
from backend.core.logging import get_logger
from backend.db.models.chat import Conversation, Message
from backend.db.session import get_db
from backend.schemas.conversation import (
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
    MessageOut,
    decode_cursor,
    encode_cursor,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = get_logger(__name__)

MESSAGE_PREVIEW_CHARS = 120
MAX_MESSAGES_PER_CONVERSATION_BEFORE_PAGINATION_WARNING = 500


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ConversationListResponse:
    session_id = request.state.session_id

    # Correlated subqueries: counted-message and latest-message-preview attach
    # directly to each conversation row, so the whole listing is one round-trip
    # instead of N+1.
    message_count_subq = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    last_preview_subq = (
        select(func.substr(Message.content, 1, MESSAGE_PREVIEW_CHARS))
        .where(Message.conversation_id == Conversation.id)
        .order_by(Message.created_at.desc())
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )

    stmt = select(
        Conversation.id,
        Conversation.title,
        Conversation.created_at,
        Conversation.updated_at,
        message_count_subq.label("message_count"),
        last_preview_subq.label("last_message_preview"),
    ).where(
        Conversation.session_id == session_id,
        Conversation.deleted_at.is_(None),
    )

    if cursor:
        try:
            payload = decode_cursor(cursor)
            cursor_updated_at, cursor_id = payload.parsed()
        except ValueError as exc:
            raise ValidationError(
                "Invalid cursor",
                code="invalid_cursor",
                status_code=400,
            ) from exc
        # Keyset pagination: row-by-row "<" on the (updated_at, id) tuple.
        stmt = stmt.where(
            sa.or_(
                Conversation.updated_at < cursor_updated_at,
                sa.and_(
                    Conversation.updated_at == cursor_updated_at,
                    Conversation.id < cursor_id,
                ),
            )
        )

    # Fetch limit+1 to detect "is there a next page" without a second query.
    stmt = stmt.order_by(
        Conversation.updated_at.desc(), Conversation.id.desc()
    ).limit(limit + 1)

    result = await db.execute(stmt)
    rows = result.all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [
        ConversationSummary(
            id=row.id,
            title=row.title,
            created_at=row.created_at,
            updated_at=row.updated_at,
            message_count=row.message_count or 0,
            last_message_preview=row.last_message_preview,
        )
        for row in rows
    ]

    next_cursor = (
        encode_cursor(rows[-1].updated_at, rows[-1].id) if has_more else None
    )

    return ConversationListResponse(items=items, next_cursor=next_cursor)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    request: Request,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    session_id = request.state.session_id

    convo = await db.get(Conversation, conversation_id)
    # 404 covers all three "no" cases: missing, soft-deleted, wrong session.
    # Returning the same error means callers can't enumerate ids by behavior.
    if convo is None or convo.deleted_at is not None or convo.session_id != session_id:
        raise NotFoundError("Conversation not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == convo.id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    if len(messages) > MAX_MESSAGES_PER_CONVERSATION_BEFORE_PAGINATION_WARNING:
        # TODO: paginate messages when this gets exercised in real traffic.
        logger.warning(
            "conversation_messages_over_threshold",
            conversation_id=str(convo.id),
            count=len(messages),
        )

    return ConversationDetail(
        id=convo.id,
        title=convo.title,
        created_at=convo.created_at,
        updated_at=convo.updated_at,
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    request: Request,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    session_id = request.state.session_id

    # One atomic UPDATE — combines existence, ownership, and not-yet-deleted
    # checks. rowcount == 0 means at least one of those failed; we return 404
    # uniformly so callers can't distinguish "wrong session" from "already
    # gone".
    result = await db.execute(
        sa.update(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.session_id == session_id,
            Conversation.deleted_at.is_(None),
        )
        .values(deleted_at=func.now())
    )
    if result.rowcount == 0:
        raise NotFoundError("Conversation not found")
    await db.commit()
    return Response(status_code=204)
