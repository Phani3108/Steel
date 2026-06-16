"""steel-governor — the speed governor (SAFETY system).

Versioned policy engine: pre-action checks an agent cannot reason its way around.
Pure Python + YAML — no database. Policies are files; decisions are returned to the
caller, who audits them (steel-blackbox in the assembled platform).

    from steel_governor import Governor, Decision

    gov = Governor()                       # loads <repo>/policies/procurement.yaml
    decision = gov.check(ctx, "rfx.award", {"total_usd": 120_000, "n_bids": 4})
    decision.allowed, decision.requires_gate, decision.reasons
"""

from steel_governor.engine import AWARD_GATE, INTAKE_GATE, Decision, Governor
from steel_governor.policy import PolicyFile, default_policy_path, load_policy

__version__ = "0.1.0"

__all__ = [
    "AWARD_GATE",
    "INTAKE_GATE",
    "Decision",
    "Governor",
    "PolicyFile",
    "default_policy_path",
    "load_policy",
]
