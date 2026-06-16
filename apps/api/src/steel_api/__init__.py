"""steel-api — the STEEL control plane: the read-only FastAPI surface the console reads.

Costs from ``meter.task_ledger``, runs and events from ``blackbox.audit_events``,
independent audit-chain verification, and health — consumed over the parts'
published table contracts. Strictly read-only: this app never writes a row.
"""

from steel_api.main import create_app, serve

__version__ = "0.1.0"

__all__ = ["create_app", "serve"]
