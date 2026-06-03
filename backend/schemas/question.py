from __future__ import annotations

from pydantic import BaseModel


class QuestionResponseOption(BaseModel):
    label: str
    value: str


class QuestionRequest(BaseModel):
    field: str
    question: str
    reason: str
    intent_context: str
    response_options: list[QuestionResponseOption] = []
    free_form_ok: bool = True
    priority_score: float


class QuestionEngineConfig(BaseModel):
    min_priority_to_ask: float = 0.3
    max_questions_per_turn: int = 1
