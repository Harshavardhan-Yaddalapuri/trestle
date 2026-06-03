from __future__ import annotations

from pydantic import BaseModel

from backend.services.skills_registry import SkillDescriptor, SkillInput


class SkillsListResponse(BaseModel):
    skills: list[SkillDescriptor]
    version: str
    count: int


__all__ = ["SkillDescriptor", "SkillInput", "SkillsListResponse"]
