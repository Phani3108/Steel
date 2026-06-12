"""Policy file loading and validation.

A policy is a versioned YAML artifact (default: ``<repo>/policies/procurement.yaml``)
validated into a pydantic model at load time. A malformed policy fails loudly at
Governor construction — never silently at check time.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_POLICY_RELPATH = Path("policies") / "procurement.yaml"


class ThreeBidRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_bids: int = Field(ge=1)
    exempt_below_usd: float = Field(ge=0)


class SourcingRules(BaseModel):
    model_config = ConfigDict(extra="forbid")

    create_roles: list[str]


class MandateRules(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hard_deny_over_pct: float = Field(default=1.0, gt=0)


class PolicyFile(BaseModel):
    """The validated shape of policies/procurement.yaml."""

    model_config = ConfigDict(extra="forbid")

    version: str
    approval_thresholds_usd: dict[str, float]
    three_bid_rule: ThreeBidRule
    sourcing: SourcingRules
    mandate: MandateRules = Field(default_factory=MandateRules)


def default_policy_path() -> Path:
    """Locate <repo>/policies/procurement.yaml by walking up from this file."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / DEFAULT_POLICY_RELPATH
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"no {DEFAULT_POLICY_RELPATH} found above {Path(__file__).resolve()}; "
        "pass policy_path explicitly"
    )


def load_policy(path: str | Path) -> PolicyFile:
    """Read and validate a policy YAML file. Raises on missing file or bad shape."""
    raw = yaml.safe_load(Path(path).read_text())
    return PolicyFile.model_validate(raw)
