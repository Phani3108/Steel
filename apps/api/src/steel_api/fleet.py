"""The fleet assembler — the one place every NETWORK part is wired together.

This is assembler-tier glue (like the demos): it is allowed to import cortex, mcp,
governor, brakes, mesh, registry, engine and compose them. The engine, mesh, and
specialists stay pure; here is where the orchestrator gets its specialists' handlers,
the sourcing agent, and the mesh that carries the shared trace between them.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from steel_blackbox import BlackBox
from steel_brakes import Brakes
from steel_cortex import Cortex
from steel_engine.negotiate import Negotiator, compile_negotiator
from steel_engine.orchestrate import Orchestrator, compile_orchestrator
from steel_engine.sourcing import SourcingAgent, compile_sourcing
from steel_gateway import GatewayClient, estimate_tokens, modeled_cost
from steel_governor import Governor
from steel_manifest import AgentManifest, AuditEvent, RunContext, load_manifest
from steel_mcp.registry import in_process_tools
from steel_mesh import AgentCard, Hop, Mesh, Skill
from steel_meter import Meter
from steel_registry import Registry

ROOT = Path(__file__).resolve().parents[4]
AGENTS = ROOT / "parts" / "agents"
SEED = ROOT / "data" / "seed"
RESULTS = ROOT / "evals" / "results"

# Which system each agent belongs to, for the roster.
AGENT_SYSTEMS = {
    "agent-echo": "POWERTRAIN",
    "agent-supplier-intel": "CHASSIS",
    "agent-sourcing": "DRIVETRAIN",
    "agent-orchestrator": "NETWORK",
    "agent-intake-triage": "NETWORK",
    "agent-risk-sentinel": "NETWORK",
    "agent-spend-analyst": "NETWORK",
    "agent-negotiator": "NETWORK",
}

SOURCING_THRESHOLD_USD = 10_000.0


def _card(manifest: AgentManifest) -> AgentCard:
    return AgentCard(
        name=manifest.name,
        description=manifest.description.strip(),
        version="0.1.0",
        skills=[Skill(id=s, name=s) for s in manifest.skills],
    )


@dataclass
class Fleet:
    mesh: Mesh
    orchestrator: Orchestrator
    sourcing: SourcingAgent
    negotiator: Negotiator
    sellers: list[dict[str, Any]]  # [{skill_id, name}] — the negotiation counterparties
    brakes: Brakes
    blackbox: BlackBox
    registry: Registry
    hops: list[Hop]

    def close(self) -> None:
        self.sourcing.close()


def build_fleet() -> Fleet:
    """Compose the whole NETWORK: specialists on the mesh + the sourcing agent +
    the orchestrator. Returns a Fleet whose .orchestrator runs a full operation."""
    GatewayClient()  # validate gateway config is loadable; specialists are mock-deterministic
    blackbox = BlackBox()
    blackbox.ensure_schema()
    meter = Meter()
    meter.ensure_schema()
    cortex = Cortex()
    cortex.ensure_schema()
    if not cortex.is_ingested():
        cortex.ingest_seed(SEED)
    brakes = Brakes()
    brakes.ensure_schema()
    governor = Governor()
    sm = in_process_tools("supplier-master")
    spend = in_process_tools("spend-analytics")

    hops: list[Hop] = []
    mesh = Mesh(on_hop=hops.append)

    # ── specialist handlers ──
    # Each writes one audit event under its OWN child agent and meters its work with a
    # MODELED cost (real per-model rates × estimated tokens — honest, no API spend), so a
    # single run_id carries the whole fleet's footprint in one chain and one cost rollup.
    def _record(ctx: RunContext, action: str, detail: dict, *, group: str,
                in_text: str, out_text: str) -> float:
        in_tok, out_tok = estimate_tokens(in_text), estimate_tokens(out_text)
        cost = modeled_cost(group, in_tok, out_tok)
        blackbox.append(AuditEvent(
            tenant_id=ctx.tenant_id, actor_id=ctx.actor.id, actor_role=ctx.actor.role,
            agent=ctx.agent, run_id=ctx.run_id, trace_id=ctx.trace_id,
            action=action, outcome="ok", detail=detail,
        ))
        meter.record(ctx, action=action, model=group, model_group=group,
                     input_tokens=in_tok, output_tokens=out_tok, cost_usd=cost, detail=detail)
        return cost

    def triage_handler(ctx: RunContext, inp: dict[str, Any]) -> dict[str, Any]:
        est = float(inp.get("est_value_usd") or 0)
        decision = governor.check(ctx, "intake.approve", {"est_value_usd": est})
        route = "sourcing_required" if est >= SOURCING_THRESHOLD_USD else "auto_approved"
        cmp = "≥" if route == "sourcing_required" else "<"
        thr = f"${SOURCING_THRESHOLD_USD:,.0f}"
        reason = f"est ${est:,.0f} {cmp} {thr} competition threshold"
        in_text = f"{inp.get('title', '')} {inp.get('category', '')} {est}"
        cost = _record(ctx, "skill.triage", {"route": route}, group="fast",
                       in_text=in_text, out_text=reason)
        return {"route": route, "reason": reason,
                "policy_version": decision.policy_version, "_cost_usd": cost}

    def risk_handler(ctx: RunContext, inp: dict[str, Any]) -> dict[str, Any]:
        category = inp.get("category") or ""
        suppliers = sm["search_suppliers"](ctx.tenant_id, ctx.actor.role, category=category)
        if not suppliers:
            suppliers = sm["search_suppliers"](ctx.tenant_id, ctx.actor.role)
        if not suppliers:
            return {"summary": "no suppliers found for category", "_cost_usd": 0.0}
        supplier = next((s for s in suppliers if s.get("red_flag")), suppliers[0])
        result = cortex.retrieve(ctx, f"news and risk signals about {supplier['name']}")
        if getattr(result, "refused", False):
            summary = f"risk read not permitted for role {ctx.actor.role!r}"
            cost = _record(ctx, "skill.risk", {"supplier": supplier["name"], "refused": True},
                           group="reasoning", in_text=supplier["name"], out_text=summary)
            return {"summary": summary, "refused": True, "_cost_usd": cost}
        signals = [f for f in result.facts if f.get("signal")]
        adverse = [s for s in signals if s.get("signal") != "positive"]
        head = (adverse or signals or [{}])[0].get("headline", "no adverse signals")
        cites = [{"source_type": c.source_type, "source_id": c.source_id}
                 for c in result.citations[:4]]
        summary = f"{supplier['name']}: {len(adverse)} adverse / {len(signals)} signals — {head}"
        cost = _record(ctx, "skill.risk", {"supplier": supplier["name"]}, group="reasoning",
                       in_text=str(result.facts)[:600], out_text=summary)
        return {"summary": summary, "supplier": supplier["name"], "adverse": len(adverse),
                "signals": len(signals), "citations": cites, "_cost_usd": cost}

    def spend_handler(ctx: RunContext, inp: dict[str, Any]) -> dict[str, Any]:
        cube = spend["spend_cube"](ctx.tenant_id, ctx.actor.role, by="category")
        if isinstance(cube, dict) and cube.get("error"):
            summary = f"spend read unavailable: {cube['error']}"
            cost = _record(ctx, "skill.spend", {"error": True}, group="fast",
                           in_text="spend cube by category", out_text=summary)
            return {"summary": summary, "_cost_usd": cost}
        top = cube[:3] if isinstance(cube, list) else []
        parts = ", ".join(f"{r['key']}=${float(r['total_usd']):,.0f}" for r in top)
        summary = f"top categories by spend: {parts}"
        cost = _record(ctx, "skill.spend", {"by": "category"}, group="fast",
                       in_text=str(top)[:600], out_text=summary)
        return {"summary": summary, "top": top, "_cost_usd": cost}

    specialists = {
        "agent-intake-triage": ("intake.triage", triage_handler),
        "agent-risk-sentinel": ("risk.assess", risk_handler),
        "agent-spend-analyst": ("spend.summary", spend_handler),
    }
    for name, (skill_id, handler) in specialists.items():
        manifest = load_manifest(AGENTS / _dir(name) / "manifest.yaml")
        mesh.register(_card(manifest), {skill_id: handler})

    sourcing = compile_sourcing(
        load_manifest(AGENTS / "sourcing" / "manifest.yaml"),
        blackbox=blackbox, governor=governor, brakes=brakes,
        tools={n: in_process_tools(n) for n in ("sourcing-events", "supplier-master")},
        personas=[json.loads(line)
                  for line in (SEED / "seller_personas.jsonl").read_text().splitlines()],
    )
    orchestrator = compile_orchestrator(
        load_manifest(AGENTS / "orchestrator" / "manifest.yaml"),
        mesh=mesh, blackbox=blackbox, sourcing=sourcing,
        sourcing_threshold_usd=SOURCING_THRESHOLD_USD,
    )

    # ── negotiation counterparties: three seller personas on the mesh ──
    personas = [json.loads(line)
                for line in (SEED / "seller_personas.jsonl").read_text().splitlines()]
    sellers: list[dict[str, Any]] = []
    for persona in personas[:3]:
        slug = persona["name"].lower().replace("the ", "").replace(" ", "-")
        skill_id = f"negotiate.{slug}"
        card = AgentCard(name=f"seller · {persona['name']}",
                         description=persona.get("style", ""),
                         skills=[Skill(id=skill_id, name=persona["name"])])
        mesh.register(card, {skill_id: _make_seller(persona)})
        sellers.append({"skill_id": skill_id, "name": persona["name"]})

    negotiator = compile_negotiator(
        load_manifest(AGENTS / "negotiator" / "manifest.yaml"),
        mesh=mesh, blackbox=blackbox, governor=governor,
    )

    registry = Registry()
    registry.ensure_schema()
    registry.sync_agents(AGENTS, AGENT_SYSTEMS)
    if RESULTS.exists():
        registry.load_scorecards(RESULTS)

    return Fleet(mesh=mesh, orchestrator=orchestrator, sourcing=sourcing,
                 negotiator=negotiator, sellers=sellers, brakes=brakes, blackbox=blackbox,
                 registry=registry, hops=hops)


def _make_seller(persona: dict[str, Any]) -> Handler:
    """A persona-driven seller: concedes from list toward a hidden floor by its step,
    accepts once the buyer's offer reaches that floor. Deterministic given the round."""
    floor_pct = float(persona["price_floor_pct"]) / 100.0   # seed stores percentages
    step_pct = float(persona["concession_step_pct"]) / 100.0

    def handler(ctx: RunContext, inp: dict[str, Any]) -> dict[str, Any]:
        list_price = float(inp["list_price"])
        offer = float(inp["offer"])
        rnd = int(inp["round"])
        floor = list_price * floor_pct
        counter = max(floor, list_price * (1.0 - step_pct * rnd))
        return {
            "counter_price": round(counter, 2),
            "accept": offer >= floor,
            "payment_terms": int(inp.get("payment_terms_ask") or 30),
            "persona": persona["name"],
            # Modeled cost of the negotiator's per-round reasoning (no API spend).
            "_cost_usd": modeled_cost("reasoning", 120, 40),
        }

    return handler


def run_negotiation(fleet: Fleet, ctx: RunContext, deal: dict[str, Any]) -> dict[str, Any]:
    """Run one negotiation against a named seller and return a console-shaped payload."""
    result = fleet.negotiator.run(ctx, deal)
    return {
        "status": result.status, "seller": result.seller,
        "list_price": result.list_price, "final_price": result.final_price,
        "savings_pct": result.savings_pct, "payment_terms_days": result.payment_terms_days,
        "rounds": result.rounds, "mandate_cap": result.mandate_cap,
        "breached": result.breached, "closed": result.closed,
        "transcript": result.transcript, "run_id": ctx.run_id,
    }


_DIRS = {
    "agent-intake-triage": "intake_triage",
    "agent-risk-sentinel": "risk_sentinel",
    "agent-spend-analyst": "spend_analyst",
}


def _dir(agent_name: str) -> str:
    return _DIRS.get(agent_name, agent_name.removeprefix("agent-"))


def run_orchestration(
    fleet: Fleet, ctx: RunContext, intake: dict[str, Any], *, auto_approve: bool = True
) -> dict[str, Any]:
    """Run one orchestration and (optionally) clear its gates, returning a console-shaped
    payload: the fan-out hops, specialist memos, final status, and the award if it landed."""
    result = fleet.orchestrator.run(ctx, intake)
    award: dict[str, Any] | None = None
    paused_gate: str | None = result.hops[-1]["summary"].split("'")[1] \
        if result.status == "paused" and "'" in result.hops[-1]["summary"] else None
    final_status = result.status

    if auto_approve and result.status == "paused":
        while True:
            pending = [p for p in fleet.brakes.pending(ctx.tenant_id)
                       if p["thread_id"] == result.thread_id]
            if not pending:
                break
            fleet.brakes.decide(pending[0]["id"], approver="console.auto", approve=True,
                                note="auto-approved by mission control")
            sr = fleet.sourcing.resume(ctx, thread_id=result.thread_id)
            final_status = sr.status
            if sr.status == "complete" and sr.text.startswith("AWARDED:"):
                head = sr.text.split()[0]  # AWARDED:SUP-0064
                supplier_id = head.split(":", 1)[1]
                total = next((tok for tok in sr.text.split() if tok.startswith("total=$")), "")
                award = {"supplier_id": supplier_id,
                         "total_usd": float(total.removeprefix("total=$") or 0)}
            if sr.status != "paused":
                paused_gate = None
                break

    return {
        "run_id": result.run_id,
        "trace_id": result.trace_id,
        "status": final_status,
        "hops": result.hops,
        "memos": result.memos,
        "event_id": result.event_id,
        "paused_gate": paused_gate,
        "award": award,
        "total_cost_usd": result.total_cost_usd,
    }


def maturity_ladder() -> list[dict[str, Any]]:
    """Each agent's autonomy promotion decision: did its committed scorecard earn it a
    level? The eval-gated maturity ladder — promotion is proven, never edited in."""
    from steel_dyno.scorecard import Scorecard, promotion_gate

    # Collect the best committed scorecard per agent across all result files.
    best: dict[str, dict[str, Any]] = {}
    for path in sorted(RESULTS.glob("*.json")):
        raw = json.loads(path.read_text())
        for card in raw if isinstance(raw, list) else [raw]:
            agent = card.get("agent")
            if agent and card.get("pass_rate", 0) >= best.get(agent, {}).get("pass_rate", -1):
                best[agent] = card

    ladder: list[dict[str, Any]] = []
    for adir in sorted(AGENTS.iterdir()):
        manifest_path = adir / "manifest.yaml"
        if not manifest_path.is_dir() and manifest_path.exists():
            manifest = load_manifest(manifest_path)
            card_dict = best.get(manifest.name)
            entry = {"agent": manifest.name, "current_level": int(manifest.autonomy_level),
                     "has_scorecard": card_dict is not None}
            if card_dict:
                card = Scorecard.model_validate({
                    "agent": manifest.name, "suite": card_dict.get("suite", "?"),
                    "n_cases": card_dict.get("n_cases", 0),
                    "n_passed": card_dict.get("n_passed", 0),
                    "pass_rate": card_dict.get("pass_rate", 0.0),
                    "policy_violations": card_dict.get("policy_violations", 0),
                })
                decision = promotion_gate(manifest, card)
                entry.update(pass_rate=card.pass_rate, promote=decision.promote,
                             to_level=int(decision.to_level) if decision.to_level else None,
                             reasons=decision.reasons)
            ladder.append(entry)
    return ladder


def _reference_topology() -> dict[str, Any]:
    """The canonical designed wiring (nodes + skill edges) — the structure of the fleet."""
    nodes = [
        {"id": "human", "label": "Human (CPO)", "system": "COCKPIT", "role": "operator"},
        {"id": "agent-orchestrator", "label": "Orchestrator", "system": "NETWORK",
         "role": "coordinator"},
        {"id": "agent-intake-triage", "label": "Intake Triage", "system": "NETWORK",
         "role": "specialist"},
        {"id": "agent-risk-sentinel", "label": "Risk Sentinel", "system": "NETWORK",
         "role": "specialist"},
        {"id": "agent-spend-analyst", "label": "Spend Analyst", "system": "NETWORK",
         "role": "specialist"},
        {"id": "agent-sourcing", "label": "Sourcing", "system": "DRIVETRAIN",
         "role": "worker"},
        {"id": "agent-supplier-intel", "label": "Supplier Intel", "system": "CHASSIS",
         "role": "worker"},
        {"id": "agent-negotiator", "label": "Negotiator", "system": "NETWORK",
         "role": "specialist"},
        {"id": "mcp-sourcing-events", "label": "sourcing-events", "system": "DRIVETRAIN",
         "role": "tool"},
        {"id": "steel-cortex", "label": "cortex", "system": "CHASSIS", "role": "knowledge"},
        {"id": "seller-personas", "label": "seller personas", "system": "DRIVETRAIN",
         "role": "counterparty"},
    ]
    edges = [
        {"source": "human", "target": "agent-orchestrator", "label": "procure.orchestrate"},
        {"source": "agent-orchestrator", "target": "agent-intake-triage", "label": "intake.triage"},
        {"source": "agent-orchestrator", "target": "agent-risk-sentinel", "label": "risk.assess"},
        {"source": "agent-orchestrator", "target": "agent-spend-analyst", "label": "spend.summary"},
        {"source": "agent-orchestrator", "target": "agent-sourcing", "label": "sourcing.run"},
        {"source": "agent-sourcing", "target": "mcp-sourcing-events", "label": "rfx.*"},
        {"source": "agent-supplier-intel", "target": "steel-cortex", "label": "retrieve"},
        {"source": "human", "target": "agent-supplier-intel", "label": "chat"},
        {"source": "human", "target": "agent-negotiator", "label": "negotiate.run"},
        {"source": "agent-negotiator", "target": "seller-personas", "label": "negotiate.*"},
    ]
    return {"nodes": nodes, "edges": edges}


def network_topology(fleet: Fleet | None = None) -> dict[str, Any]:
    """The fleet graph the console renders. The wiring is the design (canonical), but the
    LIVE truth is overlaid from the running mesh: which agents are actually registered,
    each agent's registry status, and real A2A traffic (hop counts on edges + a recent
    activity feed). Pass a Fleet for live data; omit it for the reference structure."""
    base = _reference_topology()
    if fleet is None:
        return {**base, "live": False}

    registered = {card.name for card in fleet.mesh.cards()}
    status_by = {rec.name: rec.status for rec in fleet.registry.list()}
    for node in base["nodes"]:
        node["live"] = node["id"] in registered or node["id"] in status_by
        node["status"] = status_by.get(node["id"])

    counts: dict[tuple[str, str], int] = {}
    for hop in fleet.hops:
        key = (hop.from_agent, hop.to_agent)
        counts[key] = counts.get(key, 0) + 1
    for edge in base["edges"]:
        c = counts.get((edge["source"], edge["target"]), 0)
        edge["hops"] = c
        edge["active"] = c > 0

    recent = [{"from_agent": h.from_agent, "to_agent": h.to_agent,
               "skill_id": h.skill_id, "ok": h.ok} for h in fleet.hops[-12:]]
    return {**base, "live": True, "agents_registered": len(registered),
            "total_hops": len(fleet.hops), "recent_hops": recent}


Handler = Callable[[RunContext, dict[str, Any]], dict[str, Any]]
