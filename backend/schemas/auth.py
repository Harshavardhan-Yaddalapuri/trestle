from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class MagicLinkSendIn(BaseModel):
    email: EmailStr


class MagicLinkSendOut(BaseModel):
    sent: bool
    expires_in_seconds: int


class MagicLinkVerifyIn(BaseModel):
    token: str


class UserOut(BaseModel):
    id: UUID
    email: str
    email_verified: bool
    display_name: str | None
    created_at: datetime
    last_login_at: datetime | None


class MergeSummary(BaseModel):
    no_op: bool = False
    profile_moved: int = 0
    profile_merged: int = 0
    profile_fields_filled_from_anon: int = 0
    conversations_moved: int = 0
    grant_tracks_moved: int = 0
    grant_tracks_merged: int = 0
    grant_dismissals_moved: int = 0
    grant_dismissals_merged: int = 0
    agent_memories_moved: int = 0
    lifecycle_events_moved: int = 0
    # First 8 chars only — safe to log, never exposes the full anon session id.
    from_session_id_prefix: str


class MagicLinkVerifyOut(BaseModel):
    user: UserOut
    session_merged: bool
    merge_summary: MergeSummary | None = None


class MergeSessionIn(BaseModel):
    anon_session_id: str = Field(min_length=1, max_length=128)


class MergeSessionOut(BaseModel):
    merged: bool
    summary: MergeSummary
