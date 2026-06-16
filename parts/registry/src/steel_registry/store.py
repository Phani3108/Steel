"""Registry — the fleet roster, backed by the `registry` Postgres schema.

The live catalog of every agent: its card (system, description, autonomy, pipeline,
skills), its status (active | paused | killed | planned), and its latest scorecard.
The console reads this to render the fleet; the orchestrator reads it to know who it
may dispatch and at what autonomy. Agents are upserted from their manifests, never
hand-typed here; status changes are logged so the roster carries its own history.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg
from steel_manifest import AgentManifest, load_manifest
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from steel_registry.schema import SCHEMA_SQL

_DEFAULT_PG_URL = "postgresql://steel:steel@localhost:5433/steel"

# The fields a scorecard contributes to the roster — the registry keeps the headline,
# not the full failure list (that lives in evals/results and the dyno).
_SCORECARD_KEYS = ("suite", "pass_rate", "n_cases", "n_passed", "ts")


class AgentRecord(BaseModel):
    """One row of the fleet roster — an agent's published card plus live status."""

    name: str
    system: str
    description: str
    autonomy_level: int
    pipeline: str
    skills: list[str]
    status: str
    mandate_usd: float | None = None
    scorecard: dict | None = None
    updated_at: str | None = None


def _row_to_record(row: dict[str, Any]) -> AgentRecord:
    updated = row.get("updated_at")
    mandate = row.get("mandate_usd")
    return AgentRecord(
        name=row["name"],
        system=row["system"],
        description=row["description"],
        autonomy_level=int(row["autonomy_level"]),
        pipeline=row["pipeline"],
        skills=list(row["skills"] or []),
        status=row["status"],
        mandate_usd=float(mandate) if mandate is not None else None,
        scorecard=row["scorecard"],
        updated_at=updated.isoformat() if updated is not None else None,
    )


def _trim_scorecard(scorecard: dict) -> dict:
    """Keep only the headline fields the roster surfaces."""
    return {k: scorecard[k] for k in _SCORECARD_KEYS if k in scorecard}


class Registry:
    """The fleet roster: register agents from manifests, track status, attach scorecards."""

    def __init__(self, pg_url: str | None = None) -> None:
        self._pg_url = pg_url or os.environ.get("POSTGRES_URL", _DEFAULT_PG_URL)

    def _connect(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._pg_url, row_factory=dict_row)

    def ensure_schema(self) -> None:
        """Idempotently create the registry schema, agents table, and status_log."""
        with self._connect() as conn:
            conn.execute(SCHEMA_SQL)

    def register_manifest(
        self, manifest: AgentManifest, *, system: str, status: str = "active"
    ) -> AgentRecord:
        """Upsert one agent into the roster from its manifest, keyed by name.

        On insert the row takes `status`. On update the existing status is preserved
        unless `status` is explicitly different from the default — promotion of an
        agent's autonomy/skills should never silently revive a paused or killed agent,
        so the live status is owned by set_status, not by re-registration.
        """
        skills = list(manifest.skills)
        mandate_usd = manifest.mandate.max_spend_usd
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO registry.agents
                    (name, system, description, autonomy_level, pipeline, skills,
                     status, mandate_usd, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (name) DO UPDATE SET
                    system         = EXCLUDED.system,
                    description    = EXCLUDED.description,
                    autonomy_level = EXCLUDED.autonomy_level,
                    pipeline       = EXCLUDED.pipeline,
                    skills         = EXCLUDED.skills,
                    mandate_usd    = EXCLUDED.mandate_usd,
                    updated_at     = now()
                RETURNING *
                """,
                (
                    manifest.name,
                    system,
                    manifest.description,
                    int(manifest.autonomy_level),
                    manifest.pipeline,
                    Jsonb(skills),
                    status,
                    mandate_usd,
                ),
            ).fetchone()
            if row is None:  # pragma: no cover - RETURNING always yields a row
                raise RuntimeError("upsert returned no row")
            return _row_to_record(row)

    def list(self) -> list[AgentRecord]:
        """The whole roster, ordered by system then name."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM registry.agents ORDER BY system, name"
            ).fetchall()
        return [_row_to_record(r) for r in rows]

    def get(self, name: str) -> AgentRecord | None:
        """One agent's record by name, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM registry.agents WHERE name = %s", (name,)
            ).fetchone()
        return _row_to_record(row) if row is not None else None

    def set_status(
        self, name: str, status: str, *, by: str, reason: str = ""
    ) -> AgentRecord:
        """Change an agent's live status and append a row to registry.status_log.

        Raises ValueError if the agent is not in the roster.
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE registry.agents
                   SET status = %s, updated_at = now()
                 WHERE name = %s
                RETURNING *
                """,
                (status, name),
            ).fetchone()
            if row is None:
                raise ValueError(f"agent {name!r} is not in the registry")
            conn.execute(
                """
                INSERT INTO registry.status_log (name, status, changed_by, reason)
                VALUES (%s, %s, %s, %s)
                """,
                (name, status, by, reason),
            )
            return _row_to_record(row)

    def attach_scorecard(self, name: str, scorecard: dict) -> None:
        """Store an agent's latest scorecard headline (no-op if the agent is unknown)."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE registry.agents
                   SET scorecard = %s, updated_at = now()
                 WHERE name = %s
                """,
                (Jsonb(_trim_scorecard(scorecard)), name),
            )

    def sync_agents(self, agents_dir: Path, systems: dict[str, str]) -> int:
        """Register every parts/agents/*/manifest.yaml, mapping name -> system.

        Agents not in `systems` default to the NETWORK system (they are agents — they
        belong to the fleet). Returns the number of manifests registered.
        """
        count = 0
        for manifest_path in sorted(Path(agents_dir).glob("*/manifest.yaml")):
            manifest = load_manifest(manifest_path)
            system = systems.get(manifest.name, "NETWORK")
            self.register_manifest(manifest, system=system)
            count += 1
        return count

    def load_scorecards(self, results_dir: Path) -> int:
        """Ingest evals/results/*.json and attach each scorecard to its agent.

        A results file may hold a single scorecard (dict) or a list of them. Each
        scorecard names its agent in the "agent" field. Returns the number attached.
        """
        import json

        attached = 0
        for results_path in sorted(Path(results_dir).glob("*.json")):
            data = json.loads(results_path.read_text())
            scorecards = data if isinstance(data, list) else [data]
            for scorecard in scorecards:
                agent = scorecard.get("agent")
                if not agent:
                    continue
                self.attach_scorecard(agent, scorecard)
                attached += 1
        return attached
