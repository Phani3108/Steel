"""Print the eval-gated autonomy maturity ladder.

Promotion is proven, not edited in: an agent earns its next autonomy level only when its
committed scorecard clears the manifest's targets, and never above L4 automatically (the
jump to L5 is a human decision). This is the governance artifact behind the catalog's
autonomy meters. Run: uv run python evals/run_maturity.py
"""

from __future__ import annotations

from steel_api.fleet import maturity_ladder

LEVELS = {1: "suggest", 2: "advise", 3: "gated", 4: "supervised", 5: "autonomous"}


def main() -> None:
    print("agent                     level                 scorecard   promotion")
    print("─" * 78)
    for e in maturity_ladder():
        lvl = f"L{e['current_level']} · {LEVELS.get(e['current_level'], '?')}"
        if not e["has_scorecard"]:
            verdict = "— no scorecard yet"
            sc = "—"
        else:
            sc = f"{e['pass_rate'] * 100:.0f}%"
            if e.get("promote"):
                verdict = f"✓ earns L{e['to_level']} · {LEVELS.get(e['to_level'], '?')}"
            else:
                verdict = "✓ holds (at promotion cap or below target)"
        print(f"{e['agent']:<25} {lvl:<20} {sc:<11} {verdict}")


if __name__ == "__main__":
    main()
