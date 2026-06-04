from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class AlertPreferencesIn(BaseModel):
    deadline_reminders: bool | None = None
    new_grant_matches: bool | None = None
    check_ins: bool | None = None


class AlertPreferencesOut(BaseModel):
    deadline_reminders: bool
    new_grant_matches: bool
    check_ins: bool


class AlertDeliverySummary(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id_prefix: str
    alert_kind: str
    grant_id: uuid.UUID | None
    key: str
    status: str
    failure_reason: str | None
    payload: dict
    created_at: datetime
    sent_at: datetime | None


class AlertDeliveriesResponse(BaseModel):
    deliveries: list[AlertDeliverySummary]


class TriggerAlertResponse(BaseModel):
    job_id: str
    alert_kind: str
