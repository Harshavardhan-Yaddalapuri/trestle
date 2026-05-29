from __future__ import annotations

import base64
import binascii
import json
import uuid
import warnings
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field, model_validator

GRANT_TYPES = ("grant", "contest", "accelerator", "fellowship", "other")
PROVIDER_TYPES = ("government", "foundation", "corporate", "vc", "accelerator", "other")
GRANT_STATUSES = ("active", "expired", "archived")
SOURCE_STATUSES = ("unknown", "ok", "redirect", "gone", "error")


def _fmt_amount(amount_min: int | None, amount_max: int | None) -> str:
    if amount_min is None and amount_max is None:
        return "Unspecified"
    if amount_min is not None and amount_max is not None:
        return f"${amount_min // 100:,}–${amount_max // 100:,}"
    if amount_min is not None:
        return f"${amount_min // 100:,}+"
    return f"Up to ${amount_max // 100:,}"  # type: ignore[operator]


class GrantSeed(BaseModel):
    """Deserialised from a YAML seed file. Mirrors table columns minus generated fields."""

    source_id: str
    name: str
    type: Literal["grant", "contest", "accelerator", "fellowship", "other"]
    description: str
    url: str
    application_url: str | None = None
    amount_min: int | None = None
    amount_max: int | None = None
    deadline: date | None = None
    rolling: bool = False
    stage: list[str] | None = None
    industry: list[str] | None = None
    location: list[str] | None = None
    eligibility: dict[str, Any] = {}
    provider_name: str
    provider_type: Literal[
        "government", "foundation", "corporate", "vc", "accelerator", "other"
    ] | None = None
    status: Literal["active", "expired", "archived"] = "active"

    @model_validator(mode="after")
    def _check_amounts(self) -> "GrantSeed":
        if self.amount_min is not None and self.amount_max is not None:
            if self.amount_min > self.amount_max:
                raise ValueError("amount_min must be ≤ amount_max")
        return self

    @model_validator(mode="after")
    def _warn_stale_deadline(self) -> "GrantSeed":
        if (
            self.deadline is not None
            and self.deadline < date.today()
            and self.status not in ("expired", "archived")
        ):
            warnings.warn(
                f"Grant '{self.source_id}' has a past deadline ({self.deadline}) "
                f"but status is '{self.status}'",
                stacklevel=2,
            )
        return self

    @computed_field
    @property
    def amount_display(self) -> str:
        return _fmt_amount(self.amount_min, self.amount_max)


class GrantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: str
    name: str
    type: str
    provider_name: str
    deadline: date | None
    rolling: bool
    amount_min: int | None
    amount_max: int | None
    stage: list[str] | None
    industry: list[str] | None
    location: list[str] | None
    status: str

    @computed_field
    @property
    def amount_display(self) -> str:
        return _fmt_amount(self.amount_min, self.amount_max)


class GrantDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: str
    name: str
    type: str
    description: str
    url: str
    application_url: str | None
    amount_min: int | None
    amount_max: int | None
    deadline: date | None
    rolling: bool
    stage: list[str] | None
    industry: list[str] | None
    location: list[str] | None
    eligibility: dict[str, Any]
    provider_name: str
    provider_type: str | None
    status: str
    last_verified_at: datetime | None
    source_status: str
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def amount_display(self) -> str:
        return _fmt_amount(self.amount_min, self.amount_max)


class GrantListResponse(BaseModel):
    items: list[GrantSummary]
    next_cursor: str | None
    total_estimate: int | None


# ── Cursor helpers ────────────────────────────────────────────────────────────


def encode_grant_cursor(deadline: date | None, grant_id: uuid.UUID) -> str:
    raw = json.dumps({"d": deadline.isoformat() if deadline else None, "i": str(grant_id)})
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_grant_cursor(cursor: str) -> tuple[date | None, uuid.UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + padding).encode())
        payload = json.loads(raw)
        deadline = date.fromisoformat(payload["d"]) if payload.get("d") else None
        return deadline, uuid.UUID(payload["i"])
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
        raise ValueError("invalid cursor") from exc
