from __future__ import annotations

from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, field_validator

COMPANY_STAGES = ("idea", "pre_seed", "seed", "series_a", "series_b_plus", "other")


class ProfileIn(BaseModel):
    """All fields optional. PUT with partial body performs partial update (PATCH semantics):
    only fields present in the request body are written; omitted fields are left unchanged."""

    founder_name: Optional[str] = None
    company_name: Optional[str] = None
    company_stage: Optional[str] = None
    industry: Optional[list[str]] = None
    location: Optional[str] = None
    website: Optional[str] = None
    one_liner: Optional[str] = None
    goals: Optional[str] = None

    @field_validator("founder_name", "company_name", "location", "goals", "one_liner", mode="before")
    @classmethod
    def trim_text(cls, v):
        if isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        return v

    @field_validator("one_liner")
    @classmethod
    def one_liner_max_length(cls, v):
        if v is not None and len(v) > 280:
            raise ValueError("one_liner must be at most 280 characters")
        return v

    @field_validator("website", mode="before")
    @classmethod
    def validate_website(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return None
            parsed = urlparse(stripped)
            if not (parsed.scheme in ("http", "https") and parsed.netloc):
                raise ValueError("website must be a valid URL")
            return stripped
        return v

    @field_validator("company_stage")
    @classmethod
    def validate_company_stage(cls, v):
        if v is not None and v not in COMPANY_STAGES:
            raise ValueError(f"company_stage must be one of {COMPANY_STAGES}")
        return v


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    founder_name: Optional[str] = None
    company_name: Optional[str] = None
    company_stage: Optional[str] = None
    industry: Optional[list[str]] = None
    location: Optional[str] = None
    website: Optional[str] = None
    one_liner: Optional[str] = None
    goals: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
