"""Mesh — the CAN bus: in-process A2A-shaped dispatch with run context propagation.

The mesh lets agents call each other by skill id over A2A-conformant agent cards, with
the :class:`RunContext` (tenant, actor, budget, trace) carried across every hop so one
orchestration shares one trace. Dispatch is in-process today; the contracts and the
agent-card JSON are A2A-conformant, so the same cards can be served cross-host tomorrow.

``a2a-sdk`` is the drop-in for real cross-host A2A serving/calling; ``httpx`` is already a
dependency for that future HTTP transport (see the TODO :class:`HttpTransport` stub).
"""

from __future__ import annotations

from collections.abc import Callable

from steel_manifest import RunContext

from steel_mesh.cards import AgentCard, Hop, TaskResult, to_a2a_json

Handler = Callable[[RunContext, dict], dict]


class Mesh:
    """In-process A2A registry + context-propagating dispatch.

    Register agent cards with their skill handlers, then ``dispatch`` by skill id. Each
    dispatch hands the handler a child :class:`RunContext` (same tenant/actor/trace/budget,
    agent name swapped to the callee) and emits a :class:`Hop` for the network view.
    """

    def __init__(self, on_hop: Callable[[Hop], None] | None = None) -> None:
        self._on_hop = on_hop
        self._cards: dict[str, AgentCard] = {}
        self._handlers: dict[str, Handler] = {}
        self._skill_owner: dict[str, str] = {}

    def register(self, card: AgentCard, handlers: dict[str, Handler]) -> None:
        """Register a card and its per-skill handlers.

        Every skill on the card must have a handler keyed by its skill id, or this raises
        — a card cannot advertise a skill it cannot serve.
        """
        missing = [s.id for s in card.skills if s.id not in handlers]
        if missing:
            raise ValueError(
                f"card {card.name!r} advertises skills with no handler: {missing}"
            )

        self._cards[card.name] = card
        for skill in card.skills:
            self._handlers[skill.id] = handlers[skill.id]
            self._skill_owner[skill.id] = card.name

    def cards(self) -> list[AgentCard]:
        """All registered cards, in registration order."""
        return list(self._cards.values())

    def card_for_skill(self, skill_id: str) -> AgentCard | None:
        """The card that serves ``skill_id``, or ``None`` if no agent advertises it."""
        owner = self._skill_owner.get(skill_id)
        return self._cards.get(owner) if owner is not None else None

    def dispatch(self, ctx: RunContext, skill_id: str, input: dict) -> TaskResult:
        """Route ``skill_id`` to its handler with a context-propagating child run.

        Builds ``child = ctx.child(agent=<card.name>)`` so the callee shares the parent's
        tenant, actor, trace, and budget pool. Wraps the handler return as a successful
        :class:`TaskResult` (cost read from ``output["_cost_usd"]``); a handler exception
        becomes ``ok=False`` with the error text. Either way exactly one :class:`Hop` is
        emitted (``from_agent`` = the caller's agent or ``"human"``, ``to_agent`` = callee).
        Dispatching an unknown skill returns ``ok=False`` and emits no hop (no callee).
        """
        from_agent = ctx.agent or "human"
        card = self.card_for_skill(skill_id)
        if card is None:
            return TaskResult(
                skill_id=skill_id,
                agent=from_agent,
                ok=False,
                error=f"no agent serves skill {skill_id!r}",
            )

        handler = self._handlers[skill_id]
        child = ctx.child(agent=card.name)

        try:
            output = handler(child, input)
            cost = float(output.get("_cost_usd", 0.0))
            result = TaskResult(
                skill_id=skill_id,
                agent=card.name,
                ok=True,
                output=output,
                cost_usd=cost,
            )
        except Exception as exc:  # noqa: BLE001 — any handler failure becomes a clean result
            result = TaskResult(
                skill_id=skill_id,
                agent=card.name,
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )

        self._emit(
            Hop(
                from_agent=from_agent,
                to_agent=card.name,
                skill_id=skill_id,
                ok=result.ok,
                cost_usd=result.cost_usd,
            )
        )
        return result

    def to_a2a_json(self, card: AgentCard) -> dict:
        """The real A2A agent-card JSON (the ``.well-known/agent.json`` shape)."""
        return to_a2a_json(card)

    def topology(self) -> dict:
        """The network graph the console renders: nodes (agents + their skills) and the
        skill-id -> agent routing map."""
        return {
            "nodes": [
                {"id": card.name, "skills": [s.id for s in card.skills]}
                for card in self._cards.values()
            ],
            "skills": dict(self._skill_owner),
        }

    def _emit(self, hop: Hop) -> None:
        if self._on_hop is not None:
            self._on_hop(hop)


class HttpTransport:  # pragma: no cover - future cross-host transport
    """TODO: real cross-host A2A transport over httpx.

    The in-process :class:`Mesh` and the A2A-conformant cards are the seam: swapping this
    transport in (backed by ``a2a-sdk`` for serving and ``httpx`` for calling) makes the
    same dispatch work across hosts with no change to callers. Not implemented yet.
    """

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def dispatch(self, ctx: RunContext, skill_id: str, input: dict) -> TaskResult:
        raise NotImplementedError(
            "cross-host A2A transport is not implemented; use the in-process Mesh"
        )
