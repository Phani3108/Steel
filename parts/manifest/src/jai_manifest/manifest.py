"""AgentManifest — the part drawing every agent is built from.

A manifest is the complete, framework-free definition of an agent: identity, autonomy
level, model policy, tool references, guardrails, human gates, and metric targets.
Runtimes (jai-engine's LangGraph compiler, the miniloop, anything future) compile
manifests; nothing else in the platform ever defines an agent in code.
"""

from __future__ import annotations

from enum import IntEnum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class AutonomyLevel(IntEnum):
    """How much the agent may do without a human. Promotion between levels is gated by
    jai-dyno scorecards — an agent is promoted when it proves itself, never by edit."""

    L1_SUGGEST = 1          # may only propose; human executes
    L2_ASSIST = 2           # may execute read-only actions
    L3_GATED = 3            # may execute writes behind HITL gates
    L4_SUPERVISED = 4       # acts autonomously, human reviews after the fact
    L5_AUTONOMOUS = 5       # fully autonomous within mandate


class ModelPolicy(BaseModel):
    """Which gateway model group the agent uses and what it may spend."""

    group: str = "reasoning"            # gateway model group, never a provider model id
    max_tokens: int = 4096
    budget_usd_per_task: float = 0.50   # enforced pre-dispatch by the gateway client


class PromptRef(BaseModel):
    """Prompts are versioned files, never inline strings (ADR-001)."""

    path: str                            # relative to the manifest file
    version: str = "1"


class ToolRef(BaseModel):
    """A reference to an MCP server tool. Tools are protocol references, never imports."""

    server: str                          # MCP server name, e.g. "supplier-master"
    tool: str = "*"                      # specific tool or "*" for all the role allows


class HITLGate(BaseModel):
    """A named checkpoint where the run pauses for human approval (jai-brakes)."""

    name: str
    description: str = ""
    approver_roles: list[str] = Field(default_factory=lambda: ["category_manager"])


class GuardrailsConfig(BaseModel):
    input_screening: bool = True         # injection heuristics + fast-model classifier
    output_validation: bool = True       # structured output + business-rule checks
    policies: list[str] = Field(default_factory=list)  # policy ids checked pre-action


class Mandate(BaseModel):
    """Hard limits the agent cannot exceed regardless of reasoning (negotiator pattern:
    bounded delegation). Violations are blocked by jai-governor and audited, not retried."""

    max_spend_usd: float | None = None
    max_rounds: int | None = None
    notes: str = ""


class MetricTargets(BaseModel):
    """Scorecard thresholds. No scorecard → no ship; below target → no promotion."""

    eval_pass_rate: float = 0.90
    max_policy_violations: int = 0
    max_cost_usd_per_task_p95: float | None = None


class AgentManifest(BaseModel):
    api_version: Literal["jai/v1"] = "jai/v1"
    name: str
    description: str
    autonomy_level: AutonomyLevel = AutonomyLevel.L1_SUGGEST
    model: ModelPolicy = Field(default_factory=ModelPolicy)
    prompt: PromptRef
    tools: list[ToolRef] = Field(default_factory=list)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    hitl_gates: list[HITLGate] = Field(default_factory=list)
    mandate: Mandate = Field(default_factory=Mandate)
    metrics: MetricTargets = Field(default_factory=MetricTargets)
    a2a_card: str | None = None          # path to the A2A agent card (P3)
    # Which engine graph shape this agent compiles to. "direct" = guard→model→guard;
    # "rag" = guard→retrieve→synthesize→guard (requires an injected retriever);
    # "sourcing" = the durable, gated RFx workflow (requires tools/governor/brakes).
    pipeline: Literal["direct", "rag", "sourcing"] = "direct"

    @field_validator("name")
    @classmethod
    def _name_is_kebab_agent(cls, v: str) -> str:
        import re

        if not re.fullmatch(r"agent-[a-z0-9][a-z0-9-]*", v):
            raise ValueError("agent name must match agent-<kebab-case>")
        return v


def load_manifest(path: str | Path) -> AgentManifest:
    """Load and validate a manifest YAML file."""
    raw = yaml.safe_load(Path(path).read_text())
    return AgentManifest.model_validate(raw)
