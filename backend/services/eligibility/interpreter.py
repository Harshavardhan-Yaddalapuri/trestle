from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from backend.core.logging import get_logger
from backend.schemas.match import MatchProfile, RuleFailure

logger = get_logger(__name__)

RuleHandler = Callable[[Any, MatchProfile], "RuleResult"]

RULE_HANDLERS: dict[str, RuleHandler] = {}


def register(key: str) -> Callable[[RuleHandler], RuleHandler]:
    def deco(fn: RuleHandler) -> RuleHandler:
        RULE_HANDLERS[key] = fn
        return fn
    return deco


@dataclass
class RuleResult:
    passed: bool
    code: str | None = None
    detail: str | None = None


@dataclass
class EligibilityResult:
    passed: bool
    hard_fails: list[RuleFailure]


def evaluate_eligibility(eligibility: dict[str, Any], profile: MatchProfile) -> EligibilityResult:
    """Evaluate all eligibility rules against a profile.

    All rules are evaluated even after the first failure — callers receive the full
    list so the user sees every blocking issue in one response.
    """
    hard_fails: list[RuleFailure] = []

    for key, value in eligibility.items():
        handler = RULE_HANDLERS.get(key)
        if handler is None:
            logger.debug("unknown_eligibility_key", key=key)
            continue
        result = handler(value, profile)
        if not result.passed:
            hard_fails.append(
                RuleFailure(
                    rule=key,
                    code=result.code or "failed",
                    detail=result.detail or f"Rule '{key}' failed.",
                )
            )

    return EligibilityResult(passed=len(hard_fails) == 0, hard_fails=hard_fails)
