"""Demo 0 — the echo agent: manifest -> compile -> run -> audit + ledger.

The smallest proof that the powertrain and safety systems turn over together: a YAML
manifest compiles into a LangGraph agent, one keyless mock model call flows through the
LiteLLM proxy, the meter writes a ledger row, and the blackbox chain verifies.

Requires: docker compose up -d (postgres + litellm). No provider API keys needed.
Run: python parts/engine/demo/demo_0.py   (or: make smoke)
"""

from __future__ import annotations

from pathlib import Path

from steel_blackbox import BlackBox
from steel_engine import compile_manifest
from steel_gateway import GatewayClient
from steel_manifest import Actor, RunContext, load_manifest
from steel_meter import Meter

REPO_ROOT = Path(__file__).resolve().parents[3]
ECHO_DIR = REPO_ROOT / "parts" / "agents" / "echo"


def main() -> None:
    ctx = RunContext(
        tenant_id="borealis-na",
        actor=Actor(id="demo-0", name="Demo 0 smoke", role="system"),
    )
    manifest = load_manifest(ECHO_DIR / "manifest.yaml")

    blackbox = BlackBox()
    meter = Meter()
    blackbox.ensure_schema()
    meter.ensure_schema()

    # STEEL_MOCK=1 (the default) -> the proxy answers keyless via mock_response.
    gateway = GatewayClient()
    agent = compile_manifest(
        manifest, gateway=gateway, blackbox=blackbox, meter=meter, prompt_base=ECHO_DIR
    )

    print(f"agent      : {manifest.name} (autonomy L{int(manifest.autonomy_level)})")
    print(f"mock mode  : {gateway.mock}")
    print(f"checkpoint : {'postgres' if agent.checkpointer else 'none'}")

    result = agent.run(ctx, "Hello, STEEL.")
    print(f"\noutput     : {result.text}")
    print(f"run id     : {result.run_id}")
    print(f"run cost   : ${meter.run_total(result.run_id)} (ledger)")

    verdict = blackbox.verify(run_id=result.run_id)
    print(
        f"\nblackbox   : ok={verdict.ok} checked={verdict.checked} "
        f"broken_at_seq={verdict.broken_at_seq}"
    )
    print("audit tail :")
    for row in blackbox.tail(n=10, run_id=result.run_id):
        print(
            f"  seq={row['seq']:>4}  {row['action']:<12} {row['outcome']:<7} "
            f"hash={row['hash'][:12]}…"
        )

    agent.close()


if __name__ == "__main__":
    main()
