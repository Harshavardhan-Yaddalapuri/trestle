from __future__ import annotations

import backend.services.skills  # noqa: F401 — populates registry at import time

from fastapi import APIRouter, Query

from backend.core.errors import NotFoundError
from backend.schemas.skill import SkillDescriptor, SkillsListResponse
from backend.services.skills_registry import get_skill, list_skills

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=SkillsListResponse)
async def list_skills_endpoint(
    version: str = Query(default="v1"),
    status: str = Query(default="active"),
) -> SkillsListResponse:
    skills = list_skills(version=version, status=status)
    return SkillsListResponse(skills=skills, version=version, count=len(skills))


@router.get("/{skill_id}", response_model=SkillDescriptor)
async def get_skill_endpoint(
    skill_id: str,
    version: str = Query(default="v1"),
) -> SkillDescriptor:
    skill = get_skill(version=version, skill_id=skill_id)
    if skill is None:
        raise NotFoundError(f"Skill '{skill_id}' not found")
    return skill
