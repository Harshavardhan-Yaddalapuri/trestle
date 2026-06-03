from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union


@dataclass
class LLMTokenEvent:
    delta: str


@dataclass
class ToolCallEvent:
    name: str
    args: dict[str, Any]


@dataclass
class ToolResultEvent:
    name: str
    result: dict[str, Any]


@dataclass
class QuestionEvent:
    question_text: str
    profile_field: str | None = None
    options: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class FinishEvent:
    reason: str


OrchestratorEvent = Union[LLMTokenEvent, ToolCallEvent, ToolResultEvent, QuestionEvent, FinishEvent]
