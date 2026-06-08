from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LifecycleAutoRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    started_at: datetime
    finished_at: datetime | None
    triggered_by: str
    triggered_session_id: str | None
    tracks_scanned: int
    transitions_submitted_to_review: int
    transitions_to_abandoned: int
    error: str | None
    duration_ms: int | None


class LifecycleAutoRunsResponse(BaseModel):
    runs: list[LifecycleAutoRunSummary]


class TriggerLifecycleAutoResponse(BaseModel):
    run_id: UUID
