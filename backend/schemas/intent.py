from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

IntentLabel = Literal[
    "greet",
    "discover",
    "match_request",
    "deep_dive",
    "profile_update",
    "profile_query",
    "lifecycle_action",
    "smalltalk",
    "out_of_scope",
    "correction",
    "unknown",
]


class ExtractedEntities(BaseModel):
    grant_refs: list[str] = []
    stage: str | None = None
    location: str | None = None
    industries: list[str] = []
    funding_amount_usd_cents: int | None = None
    team_size: int | None = None
    action: Literal["track", "untrack", "dismiss", "undismiss"] | None = None


class IntentResult(BaseModel):
    intent: IntentLabel
    confidence: float
    entities: ExtractedEntities = ExtractedEntities()
    classified_by: Literal["regex", "llm"]
    raw_llm_response: dict[str, Any] | None = None
