"""Eligibility rules interpreter.

Import evaluate_eligibility and EligibilityResult from this package.
The package __init__ imports each rules_* module to trigger handler registration
in the shared RULE_HANDLERS registry before any caller reaches evaluate_eligibility.
"""
from backend.services.eligibility.interpreter import EligibilityResult, evaluate_eligibility  # noqa: F401

# Trigger @register decorators in each rule family module.
import backend.services.eligibility.rules_funding  # noqa: F401
import backend.services.eligibility.rules_industry  # noqa: F401
import backend.services.eligibility.rules_location  # noqa: F401
import backend.services.eligibility.rules_regulatory  # noqa: F401
import backend.services.eligibility.rules_stage  # noqa: F401
import backend.services.eligibility.rules_team  # noqa: F401

__all__ = ["evaluate_eligibility", "EligibilityResult"]
