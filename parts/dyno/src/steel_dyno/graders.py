"""Graders — the functions that turn (output, criterion) into a pass/fail with a reason."""

from __future__ import annotations

from steel_gateway import GatewayClient
from steel_manifest import RunContext
from pydantic import BaseModel

# Reasons end up in scorecards; cap embedded outputs so a chatty target stays readable.
_REASON_LIMIT = 200

JUDGE_SYSTEM_PROMPT = (
    "You are a strict evaluation judge. Apply the rubric to the candidate output. "
    "Reply with exactly one line: 'PASS: <short reason>' or 'FAIL: <short reason>'."
)


class GradeResult(BaseModel):
    """The verdict of one grader on one case."""

    passed: bool
    reason: str


def _short(text: str) -> str:
    return text if len(text) <= _REASON_LIMIT else text[: _REASON_LIMIT - 1] + "…"


def grade_exact(*, output: str, expected: str) -> GradeResult:
    if output == expected:
        return GradeResult(passed=True, reason="exact match")
    return GradeResult(
        passed=False, reason=f"expected {_short(expected)!r}, got {_short(output)!r}"
    )


def grade_contains(*, output: str, expected: str) -> GradeResult:
    if expected in output:
        return GradeResult(passed=True, reason=f"output contains {_short(expected)!r}")
    return GradeResult(
        passed=False, reason=f"{_short(expected)!r} not found in output {_short(output)!r}"
    )


def grade_llm_judge(
    gateway: GatewayClient,
    ctx: RunContext,
    *,
    output: str,
    rubric: str,
) -> GradeResult:
    """Ask the fast model group for a one-line PASS/FAIL verdict against the rubric.

    In gateway mock mode the proxy is keyless, so the judge is fed a canned 'PASS: mock'
    verdict via LiteLLM's mock_response passthrough.
    """
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": f"Rubric:\n{rubric}\n\nCandidate output:\n{output}"},
    ]
    mock_response = "PASS: mock" if gateway.mock else None
    response = gateway.complete(
        ctx, group="fast", messages=messages, max_tokens=100, mock_response=mock_response
    )
    return _parse_verdict(response.text)


def _parse_verdict(text: str) -> GradeResult:
    line = text.strip()
    head, _, tail = line.partition(":")
    verdict = head.strip().upper()
    reason = tail.strip() or line
    if verdict == "PASS":
        return GradeResult(passed=True, reason=reason)
    if verdict == "FAIL":
        return GradeResult(passed=False, reason=reason)
    return GradeResult(passed=False, reason=f"unparseable judge verdict: {_short(line)!r}")
