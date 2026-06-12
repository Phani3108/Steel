"""Suite — the declarative shape of an eval suite: named cases, each with a grader."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

Grader = Literal["exact", "contains", "llm_judge"]


class Case(BaseModel):
    """One eval case: an input for the target and the criterion its output is graded by.

    role/tenant_id let permission-aware targets impersonate a persona per case;
    expect_refusal cases pass iff the output starts with "REFUSED:" — refusals are a
    graded behavior, not an error.
    """

    id: str
    input: str
    expected: str | None = None
    grader: Grader = "exact"
    judge_rubric: str | None = None
    role: str = "category_manager"
    tenant_id: str | None = None
    expect_refusal: bool = False

    @model_validator(mode="after")
    def _grader_requirements(self) -> Case:
        if self.expect_refusal:
            return self  # graded by the refusal contract, not by expected/rubric
        if self.grader in ("exact", "contains") and self.expected is None:
            raise ValueError(f"case {self.id!r}: grader {self.grader!r} requires 'expected'")
        if self.grader == "llm_judge" and self.judge_rubric is None:
            raise ValueError(f"case {self.id!r}: grader 'llm_judge' requires 'judge_rubric'")
        return self


class Suite(BaseModel):
    """A named collection of cases. The unit jai-dyno runs and scores."""

    name: str
    description: str = ""
    cases: list[Case] = Field(min_length=1)


def load_suite(path: str | Path) -> Suite:
    """Load and validate a suite YAML file."""
    raw = yaml.safe_load(Path(path).read_text())
    return Suite.model_validate(raw)
