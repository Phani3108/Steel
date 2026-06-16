"""steel-registry CLI: sync the fleet from disk, then show the roster.

    steel-registry sync   # load parts/agents/*/manifest.yaml + evals/results/*.json
    steel-registry list   # pretty table of the current roster

`sync` is idempotent: it upserts every agent from its manifest (preserving live status)
and attaches each agent's latest scorecard headline.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from steel_registry.store import AgentRecord, Registry

# The fleet's home systems. Agents not listed here default to NETWORK — they are
# agents, so they belong to the fleet — but the specialists that live "inside" a car
# system are catalogued there (echo = the powertrain reference agent, supplier-intel =
# the chassis knowledge agent, sourcing = the drivetrain workflow agent).
SYSTEMS: dict[str, str] = {
    "agent-echo": "POWERTRAIN",
    "agent-supplier-intel": "CHASSIS",
    "agent-sourcing": "DRIVETRAIN",
    "agent-orchestrator": "NETWORK",
    "agent-intake-triage": "NETWORK",
    "agent-risk-sentinel": "NETWORK",
    "agent-spend-analyst": "NETWORK",
}

# Repo-root-relative defaults, resolved from this file's location:
# parts/registry/src/steel_registry/cli.py -> repo root is four parents up.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_AGENTS_DIR = _REPO_ROOT / "parts" / "agents"
_DEFAULT_RESULTS_DIR = _REPO_ROOT / "evals" / "results"


def _print_table(records: list[AgentRecord]) -> None:
    if not records:
        print("(roster is empty — run `steel-registry sync`)")
        return
    header = f"{'NAME':<24} {'SYSTEM':<11} {'L':<2} {'PIPELINE':<11} {'STATUS':<8} {'SCORECARD'}"
    print(header)
    print("-" * len(header))
    for r in records:
        if r.scorecard and "pass_rate" in r.scorecard:
            sc = f"{r.scorecard.get('suite', '?')} {r.scorecard['pass_rate'] * 100:.0f}%"
        else:
            sc = "-"
        print(
            f"{r.name:<24} {r.system:<11} {r.autonomy_level:<2} "
            f"{r.pipeline:<11} {r.status:<8} {sc}"
        )


def _cmd_sync(args: argparse.Namespace) -> int:
    registry = Registry()
    try:
        registry.ensure_schema()
    except Exception as exc:  # noqa: BLE001 - surface a friendly hint, not a traceback
        print(f"Cannot reach Postgres ({exc}).")
        print("Start it with: docker compose up -d postgres")
        return 1
    n_agents = registry.sync_agents(args.agents_dir, SYSTEMS)
    n_cards = registry.load_scorecards(args.results_dir)
    print(f"synced {n_agents} agent(s); attached {n_cards} scorecard(s)")
    _print_table(registry.list())
    return 0


def _cmd_list(_args: argparse.Namespace) -> int:
    registry = Registry()
    try:
        registry.ensure_schema()
    except Exception as exc:  # noqa: BLE001
        print(f"Cannot reach Postgres ({exc}).")
        print("Start it with: docker compose up -d postgres")
        return 1
    _print_table(registry.list())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="steel-registry", description="the fleet roster")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sync = sub.add_parser("sync", help="sync agents + scorecards from disk")
    p_sync.add_argument("--agents-dir", type=Path, default=_DEFAULT_AGENTS_DIR)
    p_sync.add_argument("--results-dir", type=Path, default=_DEFAULT_RESULTS_DIR)
    p_sync.set_defaults(func=_cmd_sync)

    p_list = sub.add_parser("list", help="show the current roster")
    p_list.set_defaults(func=_cmd_list)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    import sys

    sys.exit(main())
