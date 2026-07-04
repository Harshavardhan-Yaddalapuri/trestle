"""Core data types for the ingest framework.

SourceAdapter — structural Protocol that all adapters satisfy.
IngestedGrant — normalized shape every adapter produces.
IngestResult   — summary returned by the orchestration layer.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, AsyncIterator, ClassVar, Literal, Protocol, runtime_checkable

import httpx
from pydantic import BaseModel


class IngestedGrant(BaseModel):
    source: Literal["grantsgov", "sbirgov"]
    source_id: str
    name: str
    type: Literal["grant", "contest", "accelerator", "fellowship", "other"]
    description: str
    url: str
    application_url: str | None = None
    amount_min_usd_cents: int | None = None
    amount_max_usd_cents: int | None = None
    deadline: date | None = None
    rolling: bool = False
    stage: list[str] = []
    industry: list[str] = []
    location: list[str] = []
    eligibility: dict[str, Any] = {}
    provider_name: str
    provider_type: Literal[
        "government", "foundation", "corporate", "vc", "accelerator", "other"
    ] | None = None
    status: Literal["active", "expired", "archived"] = "active"
    source_payload: dict[str, Any] = {}


class IngestResult(BaseModel):
    source: str
    fetched: int
    inserted: int
    updated: int
    skipped: int
    archived: int
    duration_ms: int
    started_at: datetime
    finished_at: datetime


@runtime_checkable
class SourceAdapter(Protocol):
    source_name: ClassVar[str]

    def fetch_all(
        self,
        client: httpx.AsyncClient,
        settings: Any,
        since: datetime | None,
    ) -> AsyncIterator[IngestedGrant]: ...
