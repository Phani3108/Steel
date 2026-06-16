"""Demo 3 — the orchestrated fleet: one intake, the whole network, one trace.

A CPO submits one purchase intake. The orchestrator triages it, fans out to the risk
and spend specialists over the mesh, then runs a governed sourcing event — and every
agent's work lands under ONE run_id, ONE audit chain, ONE cost rollup. The human then
clears both gates and the event awards.

Imports steel_api.fleet — assembler-tier glue, like the other demos. Requires docker
compose (postgres + mock gateway); no API keys.
"""

from steel_api.fleet import build_fleet
from steel_blackbox import BlackBox
from steel_manifest import Actor, RunContext
from steel_meter import Meter


def main() -> None:
    fleet = build_fleet()
    ctx = RunContext(tenant_id="TEN-0001", actor=Actor(id="maria", role="cpo"))
    intake = {
        "title": "Line-2 conveyor PPE + guarding refresh",
        "category": "Safety Equipment & PPE",
        "line_items": [{"sku": "PPE-CONV", "qty": 400}],
        "est_value_usd": 120_000,
        "requested_by": "maria.cpo",
        "simulate_bids": 3,
    }

    print("═══ One intake → the whole fleet ═══")
    print(f"  intake: {intake['title']}  (${intake['est_value_usd']:,})")
    result = fleet.orchestrator.run(ctx, intake)
    print(f"\n  trace {result.trace_id[:12]}…  status={result.status}  "
          f"hops={len(result.hops)}  cost=${result.total_cost_usd:.4f}")
    print("\n  fan-out:")
    for h in result.hops:
        flag = "ok " if h["ok"] else "ERR"
        print(f"    [{flag}] {h['from_agent']} → {h['to_agent']:<22} "
              f"{h['skill_id']:<18} {h['summary'][:60]}")

    print("\n  specialist memos:")
    for key, memo in result.memos.items():
        print(f"    {key:<6} {memo.get('summary', memo)}")

    # The human clears the gates; the durable sourcing run resumes to award.
    print("\n═══ Human clears the gates ═══")
    sourcing_result = None
    while True:
        pending = [p for p in fleet.brakes.pending("TEN-0001")
                   if p["thread_id"] == result.thread_id]
        if not pending:
            break
        gate = pending[0]["gate"]
        fleet.brakes.decide(pending[0]["id"], approver="maria.cpo", approve=True,
                            note=f"{gate} approved")
        sourcing_result = fleet.sourcing.resume(ctx, thread_id=result.thread_id)
        print(f"  approved {gate} → {sourcing_result.status}: {sourcing_result.text[:80]}")
        if sourcing_result.status != "paused":
            break

    # One run, one chain, one rollup.
    run_id = result.run_id
    print("\n═══ One run_id, one audit chain, one cost rollup ═══")
    blackbox = BlackBox()
    events = blackbox.tail(n=40, run_id=run_id)
    agents_seen = sorted({e["agent"] for e in events if e["agent"]})
    print(f"  run {run_id}")
    print(f"  agents in this run: {', '.join(agents_seen)}")
    print(f"  audit events: {len(events)}")
    verdict = blackbox.verify()
    print(f"  chain verified: ok={verdict.ok} checked={verdict.checked}")
    total = Meter().run_total(run_id)
    print(f"  run cost: ${float(total):.4f}")
    fleet.close()
    print("\nDemo 3 complete.")


if __name__ == "__main__":
    main()
