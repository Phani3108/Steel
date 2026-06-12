"""Chain integrity, tamper detection, and multi-instance appends."""

from __future__ import annotations

import uuid

import psycopg
from jai_blackbox import GENESIS_HASH, BlackBox
from jai_manifest import AuditEvent, canonical_json, sha256_hex


def _event(i: int, run_id: str, tenant_id: str) -> AuditEvent:
    return AuditEvent(
        tenant_id=tenant_id,
        actor_id="u_test",
        actor_role="system",
        agent="agent-test",
        run_id=run_id,
        trace_id="trace_test",
        action=f"test.step_{i}",
        outcome="ok",
        detail={"i": i},
    )


def _ids() -> tuple[str, str]:
    token = uuid.uuid4().hex[:8]
    return f"run_{token}", f"tenant_{token}"


def test_chain_integrity_over_five_appends(box: BlackBox) -> None:
    run_id, tenant_id = _ids()
    events = [_event(i, run_id, tenant_id) for i in range(5)]
    returned_hashes = [box.append(e) for e in events]

    # Recompute the whole chain locally from the contract's canonical form.
    prev = GENESIS_HASH
    for event, stored in zip(events, returned_hashes, strict=True):
        expected = sha256_hex(prev + canonical_json(event))
        assert stored == expected
        prev = stored

    rows = box.tail(n=10)
    assert [r["prev_hash"] for r in rows] == [GENESIS_HASH, *returned_hashes[:-1]]
    assert [r["hash"] for r in rows] == returned_hashes

    result = box.verify()
    assert result.ok is True
    assert result.checked == 5
    assert result.broken_at_seq is None


def test_verify_catches_tampered_row(box: BlackBox) -> None:
    run_id, tenant_id = _ids()
    for i in range(3):
        box.append(_event(i, run_id, tenant_id))
    assert box.verify().ok is True

    with psycopg.connect(box.pg_url) as conn:
        conn.execute(
            """UPDATE blackbox.audit_events SET detail = '{"i": 999}'::jsonb WHERE seq = 2"""
        )

    result = box.verify()
    assert result.ok is False
    assert result.broken_at_seq == 2
    assert result.checked == 2  # walk stops at the broken row

    # run_id only filters reporting; the global break is still detected.
    scoped = box.verify(run_id="run_that_does_not_exist")
    assert scoped.ok is False
    assert scoped.broken_at_seq == 2


def test_append_from_two_instances_sequentially(box: BlackBox) -> None:
    run_id, tenant_id = _ids()
    first_hash = box.append(_event(0, run_id, tenant_id))

    other = BlackBox(box.pg_url)
    second_hash = other.append(_event(1, run_id, tenant_id))

    rows = box.tail(n=2, run_id=run_id)
    assert rows[0]["prev_hash"] == GENESIS_HASH
    assert rows[1]["prev_hash"] == first_hash
    assert rows[1]["hash"] == second_hash

    result = other.verify(run_id=run_id)
    assert result.ok is True
    assert result.checked == 2
