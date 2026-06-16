"""AuditEvent — the contract for the platform's tamper-evident audit trail.

The envelope is defined here (contract layer); the hash chain itself is written and
verified by steel-blackbox. Every event records identity, authorization context, policy
version, action, and outcome — the fields EU AI Act Article 12-grade logging requires.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Outcome = Literal["ok", "denied", "error", "escalated", "pending_approval"]


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:20]}")
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tenant_id: str
    actor_id: str
    actor_role: str
    agent: str | None = None
    run_id: str
    trace_id: str
    action: str                      # e.g. "model.call", "tool.call", "approval.decision"
    outcome: Outcome
    policy_version: str | None = None
    input_sha256: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


def canonical_json(event: AuditEvent) -> str:
    """Deterministic serialization — the byte string the hash chain is computed over."""
    payload = event.model_dump(mode="json")
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()
