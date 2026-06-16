"""steel-gateway — the fuel system: typed client over the LiteLLM proxy that gives every
model call routing by group, pre-dispatch budgets, metering tags, and a keyless mock mode.
"""

from steel_gateway.client import (
    DEFAULT_MOCK_RESPONSE,
    BudgetExceededError,
    GatewayClient,
    GatewayError,
)
from steel_gateway.keys import GatewayKeyError, provision_virtual_key
from steel_gateway.models import GatewayResponse
from steel_gateway.pricing import estimate_tokens, modeled_cost

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_MOCK_RESPONSE",
    "BudgetExceededError",
    "GatewayClient",
    "GatewayError",
    "GatewayKeyError",
    "GatewayResponse",
    "estimate_tokens",
    "modeled_cost",
    "provision_virtual_key",
]
