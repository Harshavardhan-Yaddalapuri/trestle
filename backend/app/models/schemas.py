"""Pydantic schemas for request/response validation."""
from __future__ import annotations

from datetime import datetime, date
from typing import Any, Dict, List, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ──────────────────────────────
# Resource
# ──────────────────────────────

class ResourceBase(BaseModel):
    name: str = Field(..., min_length=1)
    type: Literal[
        "grant", "accelerator", "pitch_competition", "coworking",
        "event", "mentorship", "tax_credit", "hiring_program",
        "filing", "learning_material", "networking", "other"
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
    status: Literal["active", "stale", "dead", "pending_review"] = "active"


class ResourceCreate(ResourceBase):
    pass


class ResourceResponse(ResourceBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    provenance: Optional[Dict[str, Any]] = None
    last_scraped: Optional[datetime] = None
    last_verified: Optional[datetime] = None
    source_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ──────────────────────────────
# Profile
# ──────────────────────────────

class ProfileBase(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    state: Optional[str] = None
    stage: Optional[str] = None
    industry: Optional[List[str]] = None
    demographics: Optional[List[str]] = None
    funding_need: Optional[str] = None
    goals: Optional[str] = None


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OnboardingStep(BaseModel):
    field: str
    question: str
    type: Literal["text", "select", "multiselect", "location"]
    options: Optional[List[str]] = None
    required: bool = True


# ──────────────────────────────
# Search / Intent
# ──────────────────────────────

class IntentResult(BaseModel):
    location: Optional[str] = None
    state: Optional[str] = None
    stage: Optional[str] = None
    need_type: Optional[str] = None
    timeline: Optional[str] = None
    industry: Optional[List[str]] = None
    demographics: Optional[List[str]] = None
    funding_range: Optional[str] = None
    keywords: Optional[List[str]] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    profile_id: Optional[UUID] = None
    session_id: Optional[str] = None
    state: Optional[str] = None
    limit: int = Field(10, ge=1, le=50)


class Citation(BaseModel):
    source: str
    url: str
    title: str
    last_verified: Optional[datetime] = None
    confidence: str  # verified | likely | unverified


class FitResult(BaseModel):
    resource: ResourceResponse
    fit_explanation: str
    next_step: str
    confidence_badge: str
    fit_score: float = Field(..., ge=0.0, le=1.0)
    citations: List[Citation] = []


class SearchResponse(BaseModel):
    query_parsed: IntentResult
    results: List[FitResult]
    total_found: int
    sources_queried: List[str]
    fresh_sources_scraped: Optional[int] = None


# ──────────────────────────────
# Scout / Agent
# ──────────────────────────────

class ScoutProfile(BaseModel):
    name: str = "Founder"
    location: Optional[str] = None
    state: Optional[str] = None
    stage: Optional[str] = None
    industry: Optional[List[str]] = None
    query: str = ""
    tags: Optional[List[str]] = None


class ScoutRunRequest(BaseModel):
    profile: ScoutProfile
    max_results: int = 10
    dry_run: bool = False


class FetchedResource(BaseModel):
    source: str
    title: str
    snippet: str
    url: str
    fetched_at: datetime


class FetchResult(BaseModel):
    status: str
    candidates: List[FetchedResource]
    sources: List[str]
    message: str


class MatchResult(BaseModel):
    status: str
    scored: List[Dict[str, Any]]
    top_score: float
    message: str


class ScoutChanges(BaseModel):
    resource_id: Optional[str] = None
    url: str
    change_type: Literal["added", "removed", "modified", "verified"]
    summary: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    detected_at: datetime


class ScoutRunResponse(BaseModel):
    run_id: str
    profile_name: str
    status: str
    sources_queried: List[str]
    new_candidates: List[Dict[str, Any]]
    changes_detected: List[ScoutChanges]
    summary: str
    duration_ms: int
    fresh_sources_scraped: int = 0


class ScoutStatus(BaseModel):
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    is_running: bool = False
    runs_today: int = 0


# ──────────────────────────────
# Memory
# ──────────────────────────────

class MemoryCreate(BaseModel):
    profile_id: Optional[UUID] = None
    session_id: Optional[str] = None
    category: str = Field(..., description="goal | preference | interaction | search | resource")
    content: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class MemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    profile_id: Optional[UUID] = None
    session_id: Optional[str] = None
    category: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


# ──────────────────────────────
# Auth
# ──────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserSignup(BaseModel):
    email: str
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: str
    password: str


class ChangeSummary(BaseModel):
    resource_id: str
    resource_name: str
    url: str
    change_type: str
    summary: str
    detected_at: datetime
    ai_verified: bool = False
