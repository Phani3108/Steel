"""The negotiate pipeline: bounded-mandate, multi-round supplier negotiation over A2A.

The negotiator opens below its target, concedes in small steps, and closes only inside its
ZOPA — never above the walkaway, and NEVER above its hard spend cap. The cap is enforced
twice: the round logic clamps every offer to it, and the governor is asked to bless the
close (reusing the award policy's mandate hard-deny). If the only available deals exceed
the cap, the negotiator walks. A constraint violation is, by construction, impossible.

Like the other pipelines, the engine imports no other part: the seller is reached through
the injected mesh, and the cap is checked through the injected governor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from jai_manifest import AgentManifest, RunContext, sha256_hex

from jai_engine.compile import BlackboxPort, _audit
from jai_engine.orchestrate import MeshPort


class GovernorPort(Protocol):
    def check(self, ctx: RunContext, action: str, params: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class NegotiationResult:
    status: str  # deal | no_deal | walked
    list_price: float
    final_price: float | None
    savings_pct: float
    payment_terms_days: int | None
    rounds: int
    mandate_cap: float | None
    breached: bool  # did it ever close above the cap? must always be False
    seller: str = ""
    transcript: list[dict[str, Any]] = field(default_factory=list)

    @property
    def closed(self) -> bool:
        return self.status == "deal"


def _money(x: float) -> float:
    return round(x, 2)


@dataclass
class Negotiator:
    manifest: AgentManifest
    mesh: MeshPort
    blackbox: BlackboxPort
    governor: GovernorPort

    def run(self, ctx: RunContext, deal: dict[str, Any]) -> NegotiationResult:
        ctx = ctx.child(agent=self.manifest.name)
        m = self.manifest.mandate
        list_price = float(deal["list_price"])
        seller_skill = deal["seller_skill"]
        max_rounds = m.max_rounds or 6
        target = list_price * (m.target_price_pct or 0.86)
        walkaway = list_price * (m.walkaway_price_pct or 0.95)
        hard_cap = m.max_spend_usd
        # Never offer or accept above this — the mandate clamp.
        ceiling = min(walkaway, hard_cap) if hard_cap else walkaway

        _audit(self.blackbox, ctx, action="run.start", outcome="ok",
               input_sha256=sha256_hex(str(deal)),
               detail={"list_price": list_price, "ceiling": _money(ceiling),
                       "hard_cap": hard_cap, "seller": seller_skill})

        # Open just below target — but never table an offer above the mandate ceiling.
        buyer_offer = _money(min(target * 0.97, ceiling))
        terms = m.payment_terms_target_days
        transcript: list[dict[str, Any]] = []
        status, final_price, seller_name = "no_deal", None, ""
        rounds = 0

        for rnd in range(1, max_rounds + 1):
            rounds = rnd
            resp = self.mesh.dispatch(ctx, seller_skill, {
                "list_price": list_price, "offer": buyer_offer, "round": rnd,
                "payment_terms_ask": terms,
            })
            if not resp.ok:
                _audit(self.blackbox, ctx, action="negotiate.round", outcome="error",
                       detail={"round": rnd, "error": resp.error})
                break
            out = resp.output
            seller_name = out.get("persona", resp.agent)
            counter = float(out["counter_price"])
            seller_accepts = bool(out.get("accept"))
            _audit(self.blackbox, ctx, action="negotiate.round", outcome="ok",
                   detail={"round": rnd, "offer": buyer_offer, "counter": _money(counter),
                           "seller_accepts": seller_accepts})

            if seller_accepts:  # seller took our offer (offer is already <= ceiling)
                final_price, status = buyer_offer, "deal"
                transcript.append({"round": rnd, "offer": buyer_offer,
                                   "counter": _money(counter), "action": "seller_accepts"})
                break
            if counter <= ceiling:  # their counter is within our mandate — take it
                final_price, status = _money(counter), "deal"
                transcript.append({"round": rnd, "offer": buyer_offer,
                                   "counter": _money(counter), "action": "accept_counter"})
                break
            # Their counter is above our ceiling. Step toward the ceiling, never past it.
            next_offer = min(ceiling, _money(buyer_offer + (counter - buyer_offer) * 0.4))
            transcript.append({"round": rnd, "offer": buyer_offer,
                               "counter": _money(counter), "action": "counter_up"})
            if next_offer <= buyer_offer + 1.0:  # pinned at the ceiling; they won't meet us
                status = "walked"
                break
            buyer_offer = next_offer

        # Governor backstop: a close must clear the mandate cap. Defense in depth — the
        # clamp above already guarantees it, but the governor is the auditable authority.
        breached = False
        if status == "deal" and final_price is not None:
            decision = self.governor.check(ctx, "rfx.award", {
                "total_usd": final_price, "n_bids": 3, "mandate_max_spend_usd": hard_cap,
            })
            if not decision.allowed:
                _audit(self.blackbox, ctx, action="negotiate.blocked", outcome="denied",
                       policy_version=decision.policy_version,
                       detail={"final_price": final_price, "reasons": decision.reasons})
                status, final_price = "walked", None  # the governor stops the breach

        savings = (list_price - final_price) / list_price if final_price else 0.0
        _audit(self.blackbox, ctx, action="run.end",
               outcome="ok" if status == "deal" else "denied",
               detail={"status": status, "final_price": final_price,
                       "savings_pct": round(savings, 4), "rounds": rounds})

        return NegotiationResult(
            status=status, list_price=list_price, final_price=final_price,
            savings_pct=round(savings, 4), payment_terms_days=terms, rounds=rounds,
            mandate_cap=hard_cap, breached=breached, seller=seller_name, transcript=transcript,
        )


def compile_negotiator(
    manifest: AgentManifest,
    *,
    mesh: MeshPort,
    blackbox: BlackboxPort,
    governor: GovernorPort,
) -> Negotiator:
    if manifest.pipeline != "negotiate":
        raise ValueError(f"manifest {manifest.name!r} is pipeline {manifest.pipeline!r}")
    return Negotiator(manifest=manifest, mesh=mesh, blackbox=blackbox, governor=governor)
