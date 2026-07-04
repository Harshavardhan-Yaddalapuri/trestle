from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IngestRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    triggered_by: str
    started_at: datetime
    finished_at: datetime | None
    records_fetched: int
    records_inserted: int
    records_updated: int
    records_skipped: int
    records_archived: int
    duplicates_found: int = 0
    error: str | None
    duration_ms: int | None


class IngestRunDetail(IngestRunSummary):
    triggered_session_id: str | None


class IngestRunsResponse(BaseModel):
    runs: list[IngestRunSummary]


class IngestTriggerResponse(BaseModel):
    run_id: uuid.UUID
    source: str
