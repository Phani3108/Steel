"""Demo 4 — autonomous negotiation under a bounded mandate.

The negotiator works three seller personas over the mesh, closing inside its ZOPA on
price and payment terms. Then a deal whose only prices exceed the hard cap: the negotiator
walks rather than breach it — a constraint violation is impossible by construction, and
the governor is the backstop. Imports jai_api.fleet (assembler-tier). Needs docker
compose (postgres + mock gateway); no API keys.
"""

from jai_api.fleet import build_fleet, run_negotiation
from jai_manifest import Actor, RunContext


def show(payload: dict) -> None:
    if payload["closed"]:
        saved = payload["savings_pct"] * 100
        terms = payload["payment_terms_days"]
        print(f"  ✅ {payload['seller']:<22} closed ${payload['final_price']:>10,.0f} "
              f"({saved:4.1f}% saved, {terms}d terms, {payload['rounds']} rounds)")
    else:
        print(f"  ⛔ {payload['seller']:<22} {payload['status']:<8} "
              f"(cap ${payload['mandate_cap']:,.0f} held; breached={payload['breached']})")
    for t in payload["transcript"]:
        print(f"       r{t['round']}: offer ${t['offer']:>9,.0f}  "
              f"counter ${t['counter']:>9,.0f}  → {t['action']}")


def main() -> None:
    fleet = build_fleet()
    ctx = RunContext(tenant_id="TEN-0001", actor=Actor(id="maria", role="cpo"))

    print("═══ Negotiating $100k against three seller personas ═══")
    for seller in fleet.sellers:
        payload = run_negotiation(fleet, ctx, {
            "list_price": 100_000, "seller_skill": seller["skill_id"],
        })
        show(payload)

    print("\n═══ A deal the mandate forbids — list $200k, hard cap $150k ═══")
    payload = run_negotiation(fleet, ctx, {
        "list_price": 200_000, "seller_skill": fleet.sellers[0]["skill_id"],
    })
    show(payload)
    print(f"\n  constraint violations: {1 if payload['breached'] else 0} "
          f"(the negotiator walked rather than exceed ${payload['mandate_cap']:,.0f})")
    fleet.close()
    print("\nDemo 4 complete.")


if __name__ == "__main__":
    main()
