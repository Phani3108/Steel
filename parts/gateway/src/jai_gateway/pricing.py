"""Modeled cost — real per-model token rates applied to real token counts.

In mock mode the proxy never bills, so a naive cost is $0 and the cost dashboards are
meaningless. Instead of faking numbers, we MODEL the cost: take the actual token usage the
mock proxy returns and price it at representative mid-2026 list rates per model group. The
result is a true function of real usage (longer prompts cost more) with zero API spend —
labelled "modeled cost" everywhere it surfaces. Flip JAI_MOCK=0 and the proxy's own
billed cost header takes over.
"""

from __future__ import annotations

# USD per 1M tokens (input, output), by gateway model group. Representative list prices.
RATES_PER_MTOK: dict[str, tuple[float, float]] = {
    "reasoning": (3.00, 15.00),       # Sonnet-class
    "reasoning-max": (5.00, 25.00),   # Opus-class
    "fast": (1.00, 5.00),             # Haiku / Flash-class
    "embed": (0.02, 0.0),
}
_DEFAULT = (3.00, 15.00)


def modeled_cost(group: str, input_tokens: int, output_tokens: int) -> float:
    """Price token usage for a model group. Returns USD, rounded to 6 dp."""
    in_rate, out_rate = RATES_PER_MTOK.get(group, _DEFAULT)
    cost = (input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate
    return round(cost, 6)


def estimate_tokens(text: str) -> int:
    """A cheap, deterministic token estimate (~4 chars/token) for non-LLM skills that
    still do real work (retrieval, tool calls) and should carry a proportional cost."""
    return max(1, len(text) // 4)
