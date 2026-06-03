from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from backend.schemas.match import MatchProfile
from backend.schemas.question import QuestionResponseOption


@dataclass
class GapDef:
    field: str
    base_weight: float
    template_key: str
    options: list[QuestionResponseOption] | None = None
    depends_on: Callable[[MatchProfile], bool] | None = None


@dataclass
class Gap:
    field: str
    base_weight: float
    question_text: str
    response_options: list[QuestionResponseOption]
    # Set by suggest_question; 0.0 from analyze_gaps
    priority_score: float = 0.0


def _is_gap(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, list) and not value:
        return True
    return False


def stage_options() -> list[QuestionResponseOption]:
    return [
        QuestionResponseOption(label="Idea", value="idea"),
        QuestionResponseOption(label="Pre-seed", value="pre_seed"),
        QuestionResponseOption(label="Seed", value="seed"),
        QuestionResponseOption(label="Series A", value="series_a"),
        QuestionResponseOption(label="Series B+", value="series_b_plus"),
        QuestionResponseOption(label="Other", value="other"),
    ]


def yes_no_options() -> list[QuestionResponseOption]:
    return [
        QuestionResponseOption(label="Yes", value="true"),
        QuestionResponseOption(label="No", value="false"),
    ]


def funding_range_options() -> list[QuestionResponseOption]:
    return [
        QuestionResponseOption(label="$0", value="0"),
        QuestionResponseOption(label="< $50k", value="lt_50k"),
        QuestionResponseOption(label="$50k–$250k", value="50k_250k"),
        QuestionResponseOption(label="$250k–$1M", value="250k_1m"),
        QuestionResponseOption(label="$1M–$5M", value="1m_5m"),
        QuestionResponseOption(label="> $5M", value="gt_5m"),
    ]


def country_options() -> list[QuestionResponseOption]:
    return [
        QuestionResponseOption(label="United States", value="US"),
        QuestionResponseOption(label="United Kingdom", value="GB"),
        QuestionResponseOption(label="Canada", value="CA"),
        QuestionResponseOption(label="Germany", value="DE"),
        QuestionResponseOption(label="France", value="FR"),
        QuestionResponseOption(label="Other", value="other"),
    ]


GAP_DEFINITIONS: list[GapDef] = [
    GapDef(
        field="company_stage",
        base_weight=0.95,
        options=stage_options(),
        template_key="company_stage",
    ),
    GapDef(
        field="incorporation_country",
        base_weight=0.85,
        options=country_options(),
        template_key="incorporation_country",
    ),
    GapDef(
        field="incorporation_state",
        base_weight=0.5,
        options=None,
        template_key="incorporation_state",
        depends_on=lambda p: p.incorporation_country == "US",
    ),
    GapDef(
        field="industry",
        base_weight=0.8,
        options=None,
        template_key="industry",
    ),
    GapDef(
        field="team_size",
        base_weight=0.6,
        options=None,
        template_key="team_size",
    ),
    GapDef(
        field="has_technical_cofounder",
        base_weight=0.4,
        options=yes_no_options(),
        template_key="has_technical_cofounder",
    ),
    GapDef(
        field="funding_raised_usd_cents",
        base_weight=0.55,
        options=funding_range_options(),
        template_key="funding_raised",
    ),
    GapDef(
        field="funding_target_usd_cents",
        base_weight=0.45,
        options=funding_range_options(),
        template_key="funding_target",
    ),
    GapDef(
        field="one_liner",
        base_weight=0.3,
        options=None,
        template_key="one_liner",
    ),
    GapDef(
        field="company_name",
        base_weight=0.7,
        options=None,
        template_key="company_name",
    ),
    GapDef(
        field="founder_name",
        base_weight=0.6,
        options=None,
        template_key="founder_name",
    ),
]
