"""Demo 2 — autonomous sourcing with hard rails, including the kill -9 proof.

Acts: (1) a full gated RFx lifecycle: draft → publish gate → bids → score → award gate
→ award; (2) the same workflow killed dead (SIGKILL) while parked at a gate, then
resumed from its Postgres checkpoint in a fresh process; (3) the governor denying a
mandate breach; (4) the kill switch stopping the agent cold.

Requires docker compose (postgres + mock gateway); no API keys.
"""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from steel_blackbox import BlackBox
from steel_brakes import Brakes
from steel_engine.sourcing import compile_sourcing
from steel_governor import Governor
from steel_manifest import Actor, RunContext, load_manifest
from steel_mcp.registry import in_process_tools

ROOT = Path(__file__).resolve().parents[3]
AGENT_DIR = ROOT / "parts" / "agents" / "sourcing"
SERVERS = ("sourcing-events", "supplier-master")


def build_agent(brakes: Brakes):
    blackbox = BlackBox()
    blackbox.ensure_schema()
    personas = [json.loads(line) for line in
                (ROOT / "data" / "seed" / "seller_personas.jsonl").read_text().splitlines()]
    return compile_sourcing(
        load_manifest(AGENT_DIR / "manifest.yaml"),
        blackbox=blackbox,
        governor=Governor(),
        brakes=brakes,
        tools={name: in_process_tools(name) for name in SERVERS},
        personas=personas,
    ), blackbox


def intake(title: str, est: float) -> str:
    return json.dumps({
        "title": title, "category": "Safety Equipment & PPE",
        "line_items": [{"sku": "DEMO-SKU", "qty": 100}],
        "est_value_usd": est, "requested_by": "maria.cpo",
    })


def ctx() -> RunContext:
    return RunContext(tenant_id="TEN-0001", actor=Actor(id="maria", role="category_manager"))


def act1_full_lifecycle() -> None:
    print("\n═══ Act 1: gated lifecycle, end to end ($120k → award gate) ═══")
    brakes = Brakes()
    brakes.ensure_schema()
    agent, blackbox = build_agent(brakes)
    c = ctx()
    result = agent.run(c, intake("Plant PPE refresh", 120_000))
    print(f"  {result.status}: {result.text}  (gate={result.gate})")

    for gate in ("rfx_publish", "award_approval"):
        pending = [p for p in brakes.pending("TEN-0001") if p["gate"] == gate]
        if not pending:
            continue
        decided = brakes.decide(pending[0]["id"], approver="dana.cpo", approve=True,
                                note=f"{gate}: looks right")
        print(f"  human approved {gate} (approval #{decided['id']})")
        result = agent.resume(c, thread_id=result.thread_id)
        print(f"  {result.status}: {result.text[:110]}")

    print("\n  audit tail:")
    for row in blackbox.tail(n=8, run_id=result.run_id):
        print(f"    {row['action']:<18} {row['outcome']}")
    agent.close()


def act2_kill_minus_nine() -> None:
    print("\n═══ Act 2: kill -9 mid-workflow, resume in a fresh process ═══")
    worker = subprocess.Popen(
        [sys.executable, __file__, "--worker"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    thread_id = ""
    assert worker.stdout is not None
    for line in worker.stdout:
        if line.startswith("THREAD:"):
            thread_id = line.split(":", 1)[1].strip()
            break
    os.kill(worker.pid, signal.SIGKILL)
    worker.wait()
    print(f"  worker SIGKILLed while parked at the publish gate (thread {thread_id})")

    brakes = Brakes()
    agent, _ = build_agent(brakes)
    result = None
    while True:  # decide whatever gate is pending, resume, repeat until terminal
        pending = [p for p in brakes.pending("TEN-0001") if p["thread_id"] == thread_id]
        if not pending:
            break
        brakes.decide(pending[0]["id"], approver="dana.cpo", approve=True, note="post-crash")
        result = agent.resume(ctx(), thread_id=thread_id)
        print(f"  resumed from checkpoint → {result.status}: {result.text[:100]}")
        if result.status != "paused":
            break
    agent.close()


def act3_governor_denials() -> None:
    print("\n═══ Act 3: the governor says no ═══")
    brakes = Brakes()
    agent, _ = build_agent(brakes)
    c = ctx()
    over_mandate = agent.run(c, intake("Line-3 robotics retrofit", 400_000))
    if over_mandate.status == "paused":  # mandate is an award-time check: pass the gate
        pend = [p for p in brakes.pending("TEN-0001")
                if p["thread_id"] == over_mandate.thread_id]
        brakes.decide(pend[0]["id"], approver="dana.cpo", approve=True, note="publish ok")
        over_mandate = agent.resume(c, thread_id=over_mandate.thread_id)
    print(f"  mandate breach   → {over_mandate.status}: {over_mandate.text[:90]}")
    requester = RunContext(tenant_id="TEN-0001", actor=Actor(id="rob", role="requester"))
    no_role = agent.run(requester, intake("Desk chairs", 8_000))
    print(f"  requester create → {no_role.status}: {no_role.text[:90]}")
    agent.close()


def act4_kill_switch() -> None:
    print("\n═══ Act 4: the kill switch ═══")
    brakes = Brakes()
    agent, _ = build_agent(brakes)
    brakes.kill("agent-sourcing", by="dana.cpo", reason="incident drill")
    result = agent.run(ctx(), intake("Anything at all", 9_000))
    print(f"  killed agent → {result.status}: {result.text[:90]}")
    brakes.revive("agent-sourcing", by="dana.cpo")
    print("  revived.")
    agent.close()


def worker_mode() -> None:
    """Child process for Act 2: start a run, print the thread id, park at the gate."""
    brakes = Brakes()
    brakes.ensure_schema()
    agent, _ = build_agent(brakes)
    result = agent.run(ctx(), intake("Crash-test gloves", 60_000))
    print(f"THREAD:{result.thread_id}", flush=True)
    # parked at rfx_publish; hang around so the parent can SIGKILL us mid-flight
    import time

    time.sleep(60)


if __name__ == "__main__":
    if "--worker" in sys.argv:
        worker_mode()
    else:
        act1_full_lifecycle()
        act2_kill_minus_nine()
        act3_governor_denials()
        act4_kill_switch()
        print("\nDemo 2 complete.")
