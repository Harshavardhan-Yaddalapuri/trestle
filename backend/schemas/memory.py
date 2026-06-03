from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryIn(BaseModel):
    kind: Literal["preference", "constraint", "observation", "correction"]
    content: str = Field(min_length=1, max_length=500)
    structured: dict[str, Any] = {}
    conversation_id: UUID | None = None
    source_message_id: UUID | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    expires_at: datetime | None = None


class MemoryOut(BaseModel):
    id: UUID
    session_id: str
    kind: str
    content: str
    structured: dict[str, Any]
    conversation_id: UUID | None
    source_message_id: UUID | None
    confidence: float
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MemoryListResponse(BaseModel):
    items: list[MemoryOut]
    next_cursor: str | None


class MemoryContext(BaseModel):
    """Compact form for injecting into LLM prompts."""

    preferences: list[str]
    constraints: list[str]
    recent_observations: list[str]
    corrections: list[str]
