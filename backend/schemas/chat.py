from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Request / response DTOs ───────────────────────────────────────────────

class ChatMessageIn(BaseModel):
    conversation_id: UUID | None = None
    content: str = Field(min_length=1)


class ChatMessageOut(BaseModel):
    """Persisted message row, suitable for the conversation get endpoint
    landing in Step 3."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    created_at: datetime


# ── SSE event payloads (one model per event variant) ──────────────────────

class JobStartedEvent(BaseModel):
    job_id: str
    conversation_id: str
    created_at: str


class TokenEvent(BaseModel):
    delta: str


class ToolCallEvent(BaseModel):
    name: str
    args: dict[str, Any]


class ToolResultEvent(BaseModel):
    name: str
    result: Any


class MessageSavedEvent(BaseModel):
    message_id: str
    role: Literal["assistant"]
    content: str
    created_at: str


class ErrorEvent(BaseModel):
    code: str
    message: str


class DoneEvent(BaseModel):
    finish_reason: str
