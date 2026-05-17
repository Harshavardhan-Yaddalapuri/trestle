"""Pydantic models for request/response validation."""
from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, List, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# --- Base resource shape ---

class ResourceBase(BaseModel):
    name: str = Field(..., min_length=1)
    type: Literal[
        "grant",
        "accelerator",
        "pitch_competition",
        "coworking",
        "event",
        "mentorship",
        "tax_credit",
        "hiring_program",
        "filing",
        "learning_material",
        "networking",
    ]
    description: Optional[str] = None
    url: Optional[str] = None
    application_url: Optional[str] = None
    location: Optional[List[str]] = None
    industry: Optional[List[str]] = None
    stage: Optional[List[str]] = None
    demographics: Optional[List[str]] = None
    funding_range: Optional[str] = None
    deadline: Optional[date] = None
    prize_amount: Optional[str] = None
    eligibility: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    status: Literal["active", "stale", "dead", "pending_review"] = "active"


class ResourceCreate(ResourceBase):
    pass


class ResourceInDB(ResourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    embedding: Optional[List[float]] = None
    provenance: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: str
    description: Optional[str] = None
    url: Optional[str] = None
    application_url: Optional[str] = None
    location: Optional[List[str]] = None
    industry: Optional[List[str]] = None
    stage: Optional[List[str]] = None
    demographics: Optional[List[str]] = None
    funding_range: Optional[str] = None
    deadline: Optional[date] = None
    prize_amount: Optional[str] = None
    eligibility: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    provenance: Optional[Dict[str, Any]] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# --- Memory / founder context ---

class MemoryCreate(BaseModel):
    profile_id: Optional[UUID] = None
    session_id: Optional[str] = None
    category: str = Field(..., description="e.g. goal, preference, interaction, lead")
    content: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class MemoryInDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_id: Optional[UUID] = None
    session_id: Optional[str] = None
    category: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


# --- Profiles ---

class ProfileBase(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    stage: Optional[str] = None
    industry: Optional[List[str]] = None
    demographics: Optional[List[str]] = None
    funding_need: Optional[str] = None
    goals: Optional[str] = None
    notification_freq: str = "daily"


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfileInDB(ProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID] = None
    created_at: Optional[datetime] = None


# --- Search / intent ---

class IntentResult(BaseModel):
    location: Optional[str] = None
    state: Optional[str] = None
    stage: Optional[str] = None
    need_type: Optional[str] = None
    timeline: Optional[str] = None
    industry: Optional[List[str]] = None
    demographics: Optional[List[str]] = None
    funding_range: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language founder query")
    profile_id: Optional[UUID] = None
    session_id: Optional[str] = None
    limit: int = Field(10, ge=1, le=50)


class FitResult(BaseModel):
    resource: ResourceResponse
    fit_explanation: str
    next_step: str
    confidence_badge: str
    fit_score: float = Field(..., ge=0.0, le=1.0)


class SearchResponse(BaseModel):
    query_parsed: IntentResult
    results: List[FitResult]
    total_found: int
    memory_used: Optional[List[str]] = None  # references to memory entries that shaped results


# --- Scout pipeline ---

class ScoutProfile(BaseModel):
    name: str = "Founder"
    location: Optional[str] = None
    stage: Optional[str] = None
    industry: Optional[List[str]] = None
    query: str = ""
    tags: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None


class ScoutRunRequest(BaseModel):
    profile: ScoutProfile
    max_results: int = 5
    dry_run: bool = False


class VerificationResult(BaseModel):
    status: str
    profile_parsed: Dict[str, Any]
    message: str


class FetchedResource(BaseModel):
    source: str
    title: str
    snippet: str
    url: str
    metadata: Optional[Dict[str, Any]] = None


class FetchResult(BaseModel):
    status: str
    candidates: List[FetchedResource]
    sources_queried: int
    message: str


class MatchResult(BaseModel):
    status: str
    scored: List[Dict[str, Any]]
    top_score: float
    message: str


class ComposeDigest(BaseModel):
    status: str
    summary: str
    highlights: List[str]
    message: str


class ScoutRunResponse(BaseModel):
    run_id: str
    profile_name: str
    verification_results: VerificationResult
    new_resources: FetchResult
    match_results: MatchResult
    digest: ComposeDigest
    duration_ms: int
    dry_run: bool


class ScoutStatus(BaseModel):
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    is_running: bool = False
    runs_today: int = 0
