from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GrantVerificationStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_status: str
    last_verified_at: datetime | None
    consecutive_failures: int
    last_verification_error: str | None


class VerificationRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    started_at: datetime
    finished_at: datetime | None
    triggered_by: str
    triggered_session_id: str | None
    grants_checked: int
    grants_ok: int
    grants_failed: int
    grants_archived: int
    error: str | None
    duration_ms: int | None


class VerificationRunsResponse(BaseModel):
    runs: list[VerificationRunSummary]


class TriggerResponse(BaseModel):
    run_id: UUID
