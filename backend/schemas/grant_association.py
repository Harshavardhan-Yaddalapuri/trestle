from __future__ import annotations

import base64
import binascii
import json
import uuid
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.grant import GrantSummary

DISMISSAL_REASONS = (
    "not_eligible",
    "not_interested",
    "already_applied",
    "too_competitive",
    "other",
)

DismissalReason = Literal[
    "not_eligible", "not_interested", "already_applied", "too_competitive", "other"
]


class GrantTrackIn(BaseModel):
    grant_id: str
    note: str | None = Field(default=None, max_length=500)


class GrantTrackOut(BaseModel):
    id: UUID
    grant: GrantSummary
    note: str | None
    created_at: datetime
    updated_at: datetime


class GrantTrackListResponse(BaseModel):
    items: list[GrantTrackOut]
    next_cursor: str | None


class GrantDismissalIn(BaseModel):
    grant_id: str
    reason: DismissalReason | None = None


class GrantDismissalOut(BaseModel):
    id: UUID
    grant_id: UUID
    reason: str | None
    created_at: datetime


class GrantDismissalItem(BaseModel):
    id: UUID
    grant: GrantSummary
    reason: str | None
    created_at: datetime


class GrantDismissalListResponse(BaseModel):
    items: list[GrantDismissalItem]
    next_cursor: str | None


def encode_assoc_cursor(ts: datetime, row_id: uuid.UUID) -> str:
    raw = json.dumps({"u": ts.isoformat(), "i": str(row_id)})
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def decode_assoc_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
        payload = json.loads(raw)
        return datetime.fromisoformat(payload["u"]), uuid.UUID(payload["i"])
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
        raise ValueError("invalid cursor") from exc
