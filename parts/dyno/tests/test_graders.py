"""Grader unit tests — including the LLM judge against a faked gateway (zero network)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from jai_dyno.graders import grade_contains, grade_exact, grade_llm_judge
from jai_manifest import Actor, RunContext


class FakeGateway:
    """Quacks like GatewayClient.complete; echoes mock_response the way LiteLLM does."""

    def __init__(self, text: str = "FAIL: canned", mock: bool = False) -> None:
        self.mock = mock
        self.text = text
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        ctx: RunContext,
        *,
        group: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 1024,
        mock_response: str | None = None,
    ) -> SimpleNamespace:
        self.calls.append(
            {
                "ctx": ctx,
                "group": group,
                "messages": messages,
                "max_tokens": max_tokens,
                "mock_response": mock_response,
            }
        )
        text = mock_response if mock_response is not None else self.text
        return SimpleNamespace(text=text)


@pytest.fixture()
def ctx() -> RunContext:
    return RunContext(tenant_id="t1", actor=Actor(id="u1", role="system"))


def test_grade_exact() -> None:
    assert grade_exact(output="abc", expected="abc").passed
    result = grade_exact(output="abc", expected="abd")
    assert not result.passed
    assert "'abd'" in result.reason and "'abc'" in result.reason


def test_grade_contains() -> None:
    assert grade_contains(output="the brown fox", expected="brown").passed
    result = grade_contains(output="the brown fox", expected="purple")
    assert not result.passed
    assert "'purple'" in result.reason


def test_llm_judge_pass_verdict(ctx: RunContext) -> None:
    gateway = FakeGateway(text="PASS: rubric satisfied")
    result = grade_llm_judge(gateway, ctx, output="fine answer", rubric="be fine")
    assert result.passed
    assert result.reason == "rubric satisfied"


def test_llm_judge_fail_verdict(ctx: RunContext) -> None:
    gateway = FakeGateway(text="FAIL: missed the point")
    result = grade_llm_judge(gateway, ctx, output="bad answer", rubric="be fine")
    assert not result.passed
    assert result.reason == "missed the point"


def test_llm_judge_unparseable_verdict_fails_closed(ctx: RunContext) -> None:
    gateway = FakeGateway(text="MAYBE? hard to say")
    result = grade_llm_judge(gateway, ctx, output="x", rubric="y")
    assert not result.passed
    assert "unparseable judge verdict" in result.reason


def test_llm_judge_uses_fast_group_and_carries_rubric(ctx: RunContext) -> None:
    gateway = FakeGateway(text="PASS: ok")
    grade_llm_judge(gateway, ctx, output="the output", rubric="the rubric")
    (call,) = gateway.calls
    assert call["group"] == "fast"
    assert call["mock_response"] is None  # live gateway: no canned verdict
    user_message = call["messages"][-1]["content"]
    assert "the rubric" in user_message and "the output" in user_message


def test_llm_judge_mock_mode_sends_canned_pass(ctx: RunContext) -> None:
    gateway = FakeGateway(mock=True)
    result = grade_llm_judge(gateway, ctx, output="anything", rubric="anything")
    (call,) = gateway.calls
    assert call["mock_response"] == "PASS: mock"
    assert result.passed
    assert result.reason == "mock"
