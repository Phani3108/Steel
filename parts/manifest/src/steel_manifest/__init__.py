"""steel-manifest — the contract layer of the STEEL platform.

The part drawing: declarative agent specs (AgentManifest), the identity/budget envelope
(RunContext), and the audit event contract (AuditEvent). Every part may import this
package; this package imports no other part (enforced in CI).
"""

from steel_manifest.context import Actor, Role, RunContext
from steel_manifest.events import AuditEvent, Outcome, canonical_json, sha256_hex
from steel_manifest.manifest import (
    AgentManifest,
    AutonomyLevel,
    GuardrailsConfig,
    HITLGate,
    Mandate,
    MetricTargets,
    ModelPolicy,
    PromptRef,
    ToolRef,
    load_manifest,
)

__version__ = "0.1.0"

__all__ = [
    "Actor",
    "AgentManifest",
    "AuditEvent",
    "AutonomyLevel",
    "GuardrailsConfig",
    "HITLGate",
    "Mandate",
    "MetricTargets",
    "ModelPolicy",
    "Outcome",
    "PromptRef",
    "Role",
    "RunContext",
    "ToolRef",
    "canonical_json",
    "load_manifest",
    "sha256_hex",
]
