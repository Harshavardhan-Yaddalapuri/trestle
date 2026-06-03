"""Skills registry — in-memory catalog of available skills.

Skills are code-defined and ship with the backend; they are not added at
runtime by users. The registry is read-only after startup.

Forward-compat note: When skill dispatch is implemented, the chat orchestrator
will:
  1. Receive a tool_call SSE event whose name matches SkillDescriptor.tool_name.
  2. Look up the skill by tool_name in the registry.
  3. Validate the args against SkillInput definitions.
  4. Execute and emit tool_result.

For v1, tool_name is metadata only — no dispatch path exists yet.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SkillInput(BaseModel):
    name: str
    type: Literal["string", "number", "boolean", "array", "object"]
    required: bool = False
    description: str | None = None


class SkillDescriptor(BaseModel):
    id: str
    name: str
    version: str
    status: Literal["active", "deprecated"]
    description: str
    category: str
    inputs: list[SkillInput]
    example_prompts: list[str]
    tool_name: str | None = None


_REGISTRY: dict[tuple[str, str], SkillDescriptor] = {}


def register(skill: SkillDescriptor) -> None:
    _REGISTRY[(skill.version, skill.id)] = skill


def list_skills(version: str, status: str) -> list[SkillDescriptor]:
    skills = [
        s for (v, _), s in _REGISTRY.items()
        if v == version and (status == "all" or s.status == status)
    ]
    return sorted(skills, key=lambda s: (s.category, s.id))


def get_skill(version: str, skill_id: str) -> SkillDescriptor | None:
    return _REGISTRY.get((version, skill_id))
