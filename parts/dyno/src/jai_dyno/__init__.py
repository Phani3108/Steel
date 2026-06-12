"""jai-dyno — the test bench: eval harness, graders, scorecards, and autonomy promotion
gates. An agent ships only with a passing scorecard."""

from jai_dyno.graders import GradeResult, grade_contains, grade_exact, grade_llm_judge
from jai_dyno.harness import run_suite
from jai_dyno.scorecard import CaseFailure, PromotionDecision, Scorecard, promotion_gate
from jai_dyno.suite import Case, Suite, load_suite

__version__ = "0.1.0"

__all__ = [
    "Case",
    "CaseFailure",
    "GradeResult",
    "PromotionDecision",
    "Scorecard",
    "Suite",
    "grade_contains",
    "grade_exact",
    "grade_llm_judge",
    "load_suite",
    "promotion_gate",
    "run_suite",
]
