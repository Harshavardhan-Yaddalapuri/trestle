from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── DTOs returned to the client ───────────────────────────────────────────


class MessageOut(BaseModel):
    """One persisted message, used by the conversation detail endpoint."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    # The ORM Python attribute is `meta` (because `metadata` collides with
    # DeclarativeBase). Output JSON uses the field name `metadata`.
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="meta")
    created_at: datetime


class ConversationSummary(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message_preview: str | None


class ConversationDetail(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut]


class ConversationListResponse(BaseModel):
    items: list[ConversationSummary]
    next_cursor: str | None


# ── Internal cursor payload ───────────────────────────────────────────────


class CursorPayload(BaseModel):
    """Decoded keyset-pagination cursor. `u` is updated_at ISO, `i` is the
    conversation id."""

    u: str
    i: str

    def parsed(self) -> tuple[datetime, UUID]:
        return datetime.fromisoformat(self.u), UUID(self.i)


def encode_cursor(updated_at: datetime, conversation_id: UUID) -> str:
    raw = json.dumps({"u": updated_at.isoformat(), "i": str(conversation_id)})
    return (
        base64.urlsafe_b64encode(raw.encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )


def decode_cursor(cursor: str) -> CursorPayload:
    """Decode an opaque cursor. Raises ValueError on any failure — the route
    handler maps that to a 400 ValidationError(code=invalid_cursor)."""
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
        return CursorPayload.model_validate(json.loads(raw))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("invalid cursor") from exc
