"""jai-gateway — the fuel system: typed client over the LiteLLM proxy that gives every
model call routing by group, pre-dispatch budgets, metering tags, and a keyless mock mode.
"""

from jai_gateway.client import (
    DEFAULT_MOCK_RESPONSE,
    BudgetExceededError,
    GatewayClient,
    GatewayError,
)
from jai_gateway.keys import GatewayKeyError, provision_virtual_key
from jai_gateway.models import GatewayResponse

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_MOCK_RESPONSE",
    "BudgetExceededError",
    "GatewayClient",
    "GatewayError",
    "GatewayKeyError",
    "GatewayResponse",
    "provision_virtual_key",
]
