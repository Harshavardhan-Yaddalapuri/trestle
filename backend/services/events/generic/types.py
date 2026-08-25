"""Transport types for generic event discovery; no database dependency."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

ExtractionMethod = Literal["custom_adapter", "api", "ics", "rss", "jsonld", "html", "browser", "llm"]


class ExtractedEvent(BaseModel):
    """A source-agnostic event candidate with evidence for every asserted field."""

    name: str | None = None
    description: str = ""
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = None
    venue: str | None = None
    address: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    is_virtual: bool | None = None
    registration_url: str | None = None
    organizer: str | None = None
    price_usd_cents: int | None = Field(default=None, ge=0)
    industry_tags: list[str] = Field(default_factory=list)
    stage_tags: list[str] = Field(default_factory=list)
    benefit_tags: list[str] = Field(default_factory=list)
    attendee_types: list[str] = Field(default_factory=list)
    source_identifier: str | None = None
    source_name: str | None = None
    field_confidences: dict[str, float] = Field(default_factory=dict)
    evidence: dict[str, str] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class ExtractionBatch(BaseModel):
    method: ExtractionMethod
    events: list[ExtractedEvent] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    status: Literal["accepted", "pending_review", "rejected"]
    errors: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
