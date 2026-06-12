"""Typed response surface of the gateway — what every model call returns to its caller."""

from __future__ import annotations

from pydantic import BaseModel


class GatewayResponse(BaseModel):
    """One completed model call: text plus the routing and metering facts about it."""

    text: str
    model: str          # provider model the proxy actually routed to
    group: str          # gateway model group the caller asked for
    input_tokens: int
    output_tokens: int
    cost_usd: float     # 0.0 in mock mode, by definition
