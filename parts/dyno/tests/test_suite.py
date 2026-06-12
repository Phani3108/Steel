"""Suite model and YAML loading tests — including the repo smoke suite and the CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jai_dyno.cli import main
from jai_dyno.suite import Case, Suite, load_suite
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[3]
SMOKE_SUITE = REPO_ROOT / "evals" / "suite0_smoke" / "smoke.yaml"


def test_load_repo_smoke_suite() -> None:
    suite = load_suite(SMOKE_SUITE)
    assert suite.name == "suite0_smoke"
    assert len(suite.cases) == 4
    assert {c.grader for c in suite.cases} == {"exact", "contains"}
    for case in suite.cases:
        if case.grader == "exact":
            assert case.input == case.expected


def test_unknown_grader_rejected() -> None:
    with pytest.raises(ValidationError):
        Case(id="x", input="a", expected="a", grader="vibes")  # type: ignore[arg-type]


def test_exact_case_requires_expected() -> None:
    with pytest.raises(ValidationError, match="requires 'expected'"):
        Case(id="x", input="a", grader="exact")


def test_llm_judge_case_requires_rubric() -> None:
    with pytest.raises(ValidationError, match="requires 'judge_rubric'"):
        Case(id="x", input="a", grader="llm_judge")


def test_suite_requires_at_least_one_case() -> None:
    with pytest.raises(ValidationError):
        Suite(name="empty", cases=[])


def test_cli_smoke_run_echo_passes(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["run", str(SMOKE_SUITE), "--target", "echo"])
    assert exit_code == 0
    scorecard = json.loads(capsys.readouterr().out)
    assert scorecard["pass_rate"] == 1.0
    assert scorecard["n_cases"] == 4
    assert scorecard["failures"] == []


def test_cli_exit_1_below_smoke_threshold(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "name: bad\n"
        "cases:\n"
        "  - {id: a, input: x, expected: never, grader: exact}\n"
        "  - {id: b, input: y, expected: never, grader: exact}\n"
        "  - {id: c, input: z, expected: z, grader: exact}\n"
    )
    exit_code = main(["run", str(bad)])
    assert exit_code == 1
    scorecard = json.loads(capsys.readouterr().out)
    assert scorecard["pass_rate"] == pytest.approx(1 / 3)
