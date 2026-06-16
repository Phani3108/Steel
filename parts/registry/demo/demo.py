"""Standalone steel-registry demo: build the real fleet roster, then pause and revive.

Syncs every agent under parts/agents/ and every scorecard under evals/results/ into
the registry, prints the roster, pauses agent-sourcing (showing the status flip and the
status_log entry that records who/why), then revives it.

Requires Postgres (from the repo root: docker compose up -d postgres), or point
POSTGRES_URL at any Postgres you own.

Run: python parts/registry/demo/demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg
from steel_registry import Registry
from steel_registry.cli import SYSTEMS
from psycopg.rows import dict_row

_REPO_ROOT = Path(__file__).resolve().parents[3]
_AGENTS_DIR = _REPO_ROOT / "parts" / "agents"
_RESULTS_DIR = _REPO_ROOT / "evals" / "results"


def _print_roster(registry: Registry) -> None:
    print(f"\n{'NAME':<24} {'SYSTEM':<11} {'L':<2} {'PIPELINE':<11} {'STATUS':<8} SCORECARD")
    for r in registry.list():
        if r.scorecard and "pass_rate" in r.scorecard:
            sc = f"{r.scorecard.get('suite', '?')} {r.scorecard['pass_rate'] * 100:.0f}%"
        else:
            sc = "-"
        print(
            f"{r.name:<24} {r.system:<11} {r.autonomy_level:<2} "
            f"{r.pipeline:<11} {r.status:<8} {sc}"
        )


def main() -> int:
    registry = Registry()
    try:
        registry.ensure_schema()
    except Exception as exc:
        print(f"Cannot reach Postgres ({exc}).")
        print("Start it with: docker compose up -d postgres")
        return 1

    n_agents = registry.sync_agents(_AGENTS_DIR, SYSTEMS)
    n_cards = registry.load_scorecards(_RESULTS_DIR)
    print(f"synced {n_agents} agent(s) from {_AGENTS_DIR}")
    print(f"attached {n_cards} scorecard(s) from {_RESULTS_DIR}")
    _print_roster(registry)

    print("\n--- pausing agent-sourcing (kill switch hit by the CPO) ---")
    paused = registry.set_status(
        "agent-sourcing", "paused", by="u-cpo", reason="quarterly freeze on new awards"
    )
    print(f"agent-sourcing status is now: {paused.status}")

    with psycopg.connect(registry._pg_url, row_factory=dict_row) as conn:  # noqa: SLF001
        log = conn.execute(
            """
            SELECT status, changed_by, reason, ts
              FROM registry.status_log
             WHERE name = 'agent-sourcing'
             ORDER BY ts DESC, id DESC
             LIMIT 1
            """
        ).fetchone()
    assert log is not None
    print(
        f"status_log: {log['status']} by {log['changed_by']} "
        f"-- {log['reason']!r} @ {log['ts'].isoformat()}"
    )

    print("\n--- reviving agent-sourcing (freeze lifted) ---")
    revived = registry.set_status(
        "agent-sourcing", "active", by="u-cpo", reason="freeze lifted"
    )
    print(f"agent-sourcing status is now: {revived.status}")
    _print_roster(registry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
