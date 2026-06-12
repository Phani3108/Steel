"""jai-blackbox standalone demo: append, verify, tamper, catch, restore.

Requires the Postgres from docker compose (`docker compose up -d postgres`):
    python parts/blackbox/demo/demo.py
"""

from __future__ import annotations

import sys

import psycopg
from jai_blackbox import BlackBox
from jai_manifest import AuditEvent


def main() -> int:
    box = BlackBox()
    try:
        box.ensure_schema()
    except psycopg.OperationalError as exc:
        print(f"postgres unavailable ({exc}); run: docker compose up -d postgres")
        return 1

    print(f"flight recorder at {box.pg_url}\n")

    print("1) appending 3 audit events …")
    run_id = "run_blackbox_demo"
    seqs: list[int] = []
    for action, outcome in [
        ("model.call", "ok"),
        ("tool.call", "ok"),
        ("approval.decision", "denied"),
    ]:
        event = AuditEvent(
            tenant_id="demo",
            actor_id="u_demo",
            actor_role="category_manager",
            agent="agent-demo",
            run_id=run_id,
            trace_id="trace_demo",
            action=action,
            outcome=outcome,  # type: ignore[arg-type]
            detail={"demo": True, "action": action},
        )
        chain_hash = box.append(event)
        print(f"   {action:<20} -> {outcome:<8} hash={chain_hash[:16]}…")

    result = box.verify(run_id=run_id)
    print(f"\n2) verify(): ok={result.ok}, checked={result.checked} — chain intact\n")

    print("3) tampering: UPDATE one row's detail directly in SQL …")
    with psycopg.connect(box.pg_url) as conn:
        row = conn.execute(
            "SELECT seq, detail FROM blackbox.audit_events WHERE run_id = %s "
            "ORDER BY seq LIMIT 1",
            (run_id,),
        ).fetchone()
        assert row is not None
        seq, original_detail = row[0], row[1]
        seqs.append(seq)
        conn.execute(
            "UPDATE blackbox.audit_events "
            """SET detail = '{"demo": true, "amount_usd": 9999999}'::jsonb WHERE seq = %s""",
            (seq,),
        )
    print(f"   row seq={seq} now claims amount_usd=9999999")

    result = box.verify(run_id=run_id)
    print(f"\n4) verify(): ok={result.ok}, broken_at_seq={result.broken_at_seq} — TAMPER FOUND\n")

    print("5) restoring the original row …")
    with psycopg.connect(box.pg_url) as conn:
        conn.execute(
            "UPDATE blackbox.audit_events SET detail = %s::jsonb WHERE seq = %s",
            (psycopg.types.json.Json(original_detail), seq),
        )
    result = box.verify(run_id=run_id)
    print(f"   verify(): ok={result.ok} — chain intact again")
    return 0


if __name__ == "__main__":
    sys.exit(main())
