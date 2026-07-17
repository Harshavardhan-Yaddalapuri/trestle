from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: str
    source: str
    name: str
    description: str
    url: str
    host_name: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    timezone: str | None = None
    is_virtual: bool = False
    location_text: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    industry_tags: list[str] = Field(default_factory=list)
    stage_tags: list[str] = Field(default_factory=list)
    benefit_tags: list[str] = Field(default_factory=list)
    attendee_types: list[str] = Field(default_factory=list)
    cost_usd_cents: int | None = None
    application_required: bool = False
    host_quality_score: float = 0.5
    status: str = "active"

    @field_validator("industry_tags", "stage_tags", "benefit_tags", "attendee_types", mode="before")
    @classmethod
    def _none_to_empty_list(cls, value):
        return [] if value is None else value


class EventMatchRequest(BaseModel):
    stage: str | None = None
    industry: list[str] | None = None
    location: str | None = None
    goals: list[str] | None = None
    limit: int = Field(default=10, ge=1, le=50)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    include_virtual: bool = True
    include_expired: bool = False


class EventMatchProfile(BaseModel):
    company_stage: str | None = None
    industry: list[str] | None = None
    location: str | None = None
    goals: list[str] = Field(default_factory=list)


class EventMatchResult(BaseModel):
    event: EventSummary
    score: float
    matched_on: list[str]
    missing_or_mismatched: list[str]
    explanation: str


class EventMatchResponse(BaseModel):
    match_profile: EventMatchProfile
    results: list[EventMatchResult]
    total_evaluated: int
    total_returned: int


class EventListResponse(BaseModel):
    items: list[EventSummary]


class EventDiscoveryResponse(BaseModel):
    discovered: int
    inserted: int
    updated: int
    sources_scanned: int


class EventSeed(BaseModel):
    source_id: str
    source: str = "seed_demo"
    source_payload: dict = Field(default_factory=dict)
    name: str
    description: str = ""
    url: str
    host_name: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    timezone: str | None = None
    is_virtual: bool = False
    location_text: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    industry_tags: list[str] | None = None
    stage_tags: list[str] | None = None
    benefit_tags: list[str] | None = None
    attendee_types: list[str] | None = None
    cost_usd_cents: int | None = None
    application_required: bool = False
    host_quality_score: float = 0.5
    status: str = "active"
