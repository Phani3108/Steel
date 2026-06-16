import pytest
from steel_manifest import (
    AgentManifest,
    AuditEvent,
    AutonomyLevel,
    RunContext,
    canonical_json,
)
from pydantic import ValidationError

MINIMAL = {
    "name": "agent-echo",
    "description": "echoes",
    "prompt": {"path": "prompts/echo.md"},
}


def test_minimal_manifest_validates_with_safe_defaults():
    m = AgentManifest.model_validate(MINIMAL)
    assert m.autonomy_level == AutonomyLevel.L1_SUGGEST
    assert m.model.group == "reasoning"
    assert m.metrics.max_policy_violations == 0
    assert m.guardrails.input_screening is True


def test_agent_name_must_be_kebab_with_prefix():
    with pytest.raises(ValidationError):
        AgentManifest.model_validate({**MINIMAL, "name": "Echo Agent"})


def test_run_context_child_keeps_tenant_and_trace():
    ctx = RunContext(tenant_id="t1", actor={"id": "u1", "role": "cpo"})
    child = ctx.child(agent="agent-echo")
    assert child.tenant_id == ctx.tenant_id
    assert child.trace_id == ctx.trace_id
    assert child.agent == "agent-echo"
    assert ctx.agent is None  # parent unchanged


def test_metadata_tags_cover_metering_dimensions():
    ctx = RunContext(tenant_id="t1", actor={"id": "u1", "role": "requester"})
    tags = ctx.metadata_tags()
    assert {"tenant_id", "actor_role", "agent", "run_id", "trace_id"} <= set(tags)


def test_canonical_json_is_deterministic():
    e = AuditEvent(
        tenant_id="t1",
        actor_id="u1",
        actor_role="system",
        run_id="r1",
        trace_id="tr1",
        action="model.call",
        outcome="ok",
        detail={"b": 2, "a": 1},
    )
    assert canonical_json(e) == canonical_json(e.model_copy(deep=True))
    assert '"a":1,"b":2' in canonical_json(e)
