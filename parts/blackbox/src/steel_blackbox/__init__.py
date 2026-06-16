"""steel-blackbox — the flight recorder: a hash-chained, append-only, tamper-evident audit
trail for every agent action (EU AI Act Article 12-grade by construction)."""

from steel_blackbox.chain import GENESIS_HASH, BlackBox, VerifyResult

__version__ = "0.1.0"

__all__ = ["GENESIS_HASH", "BlackBox", "VerifyResult"]
