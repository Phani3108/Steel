"""In-memory fakes for the engine's three ports — just the methods compile.py calls."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from steel_gateway import BudgetExceededError, GatewayResponse
from steel_manifest import AuditEvent, RunContext


class FakeGateway:
    """Mirrors GatewayClient.complete's surface, including the pre-dispatch budget gate."""

    def __init__(self, reply: str = "ECHO: Hello, STEEL.", cost_usd: float = 0.001) -> None:
        self.reply = reply
        self.cost_usd = cost_usd
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        ctx: RunContext,
        *,
        group: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 1024,
    ) -> GatewayResponse:
        if ctx.budget_usd_remaining is not None and ctx.budget_usd_remaining <= 0:
            raise BudgetExceededError(f"budget exhausted for run {ctx.run_id}")
        self.calls.append(
            {"ctx": ctx, "group": group, "messages": messages, "max_tokens": max_tokens}
        )
        return GatewayResponse(
            text=self.reply,
            model="mock-model",
            group=group,
            input_tokens=12,
            output_tokens=8,
            cost_usd=self.cost_usd,
        )


class FakeBlackBox:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> str:
        self.events.append(event)
        return "f" * 64

    def actions(self) -> list[str]:
        return [event.action for event in self.events]


class FakeMeter:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def record(
        self,
        ctx: RunContext,
        *,
        action: str,
        model: str | None,
        model_group: str | None,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        detail: dict[str, Any] | None = None,
    ) -> int:
        self.rows.append(
            {
                "tenant_id": ctx.tenant_id,
                "agent": ctx.agent,
                "run_id": ctx.run_id,
                "action": action,
                "model": model,
                "model_group": model_group,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
                "detail": detail or {},
            }
        )
        return len(self.rows)

    def run_total(self, run_id: str) -> Decimal:
        return sum(
            (Decimal(str(r["cost_usd"])) for r in self.rows if r["run_id"] == run_id),
            Decimal("0"),
        )
