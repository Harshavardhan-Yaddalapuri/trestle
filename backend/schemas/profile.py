from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    team_size: Optional[int] = None
    has_technical_cofounder: Optional[bool] = None
    funding_raised_usd_cents: Optional[int] = None
    funding_target_usd_cents: Optional[int] = None
    incorporated: Optional[bool] = None
    incorporation_country: Optional[str] = None
    incorporation_state: Optional[str] = None
    regulatory_status: Optional[dict[str, Any]] = None

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

    @field_validator("incorporation_country", "incorporation_state")
    @classmethod
    def validate_country_state_code(cls, v):
        if v is not None and (len(v) != 2 or not v.isalpha()):
            raise ValueError("must be a 2-character alphabetic code (e.g. 'US', 'CA')")
        return v.upper() if v is not None else v

    @field_validator("funding_raised_usd_cents", "funding_target_usd_cents")
    @classmethod
    def validate_funding_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("funding amounts must be >= 0")
        return v

    @field_validator("team_size")
    @classmethod
    def validate_team_size(cls, v):
        if v is not None and v < 1:
            raise ValueError("team_size must be >= 1")
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
    team_size: Optional[int] = None
    has_technical_cofounder: Optional[bool] = None
    funding_raised_usd_cents: Optional[int] = None
    funding_target_usd_cents: Optional[int] = None
    incorporated: Optional[bool] = None
    incorporation_country: Optional[str] = None
    incorporation_state: Optional[str] = None
    regulatory_status: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
