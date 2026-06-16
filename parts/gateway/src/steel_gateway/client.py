"""GatewayClient — typed client over the LiteLLM proxy.

Callers name a model GROUP ("reasoning", "reasoning-max", "fast", "embed"), never a
provider model id; the proxy owns routing and fallbacks. This client owns the
pre-dispatch budget gate, the metering tags, the cost extraction, and the keyless mock
path (LiteLLM's mock_response — the proxy answers with no provider keys configured).
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from typing import Any

from steel_manifest import RunContext
from openai import OpenAI

from steel_gateway.models import GatewayResponse
from steel_gateway.pricing import modeled_cost

DEFAULT_MOCK_RESPONSE = "steel-gateway mock response — served keyless by the LiteLLM proxy."

COST_HEADER = "x-litellm-response-cost"

MOCK_EMBED_DIM = 8


class GatewayError(Exception):
    """Base class for gateway failures."""


class BudgetExceededError(GatewayError):
    """Raised pre-dispatch when the RunContext budget pool is exhausted."""


def _cost_from_headers(headers: Mapping[str, str]) -> float:
    value = headers.get(COST_HEADER)
    if value is None:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _mock_embedding(text: str) -> list[float]:
    """Deterministic pseudo-vector: first MOCK_EMBED_DIM bytes of sha256, scaled to [0, 1]."""
    digest = hashlib.sha256(text.encode()).digest()
    return [round(b / 255.0, 6) for b in digest[:MOCK_EMBED_DIM]]


class GatewayClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        mock: bool | None = None,
    ) -> None:
        self.base_url = base_url or os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
        self.api_key = api_key or os.environ.get("LITELLM_MASTER_KEY", "sk-steel-master-dev")
        self.mock = mock if mock is not None else os.environ.get("STEEL_MOCK", "1") == "1"
        self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def complete(
        self,
        ctx: RunContext,
        *,
        group: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 1024,
        mock_response: str | None = None,
    ) -> GatewayResponse:
        self._enforce_budget(ctx)
        mocked = self.mock or mock_response is not None
        extra_body: dict[str, Any] = {"metadata": self._metering_metadata(ctx)}
        if mocked:
            extra_body["mock_response"] = mock_response or DEFAULT_MOCK_RESPONSE
        raw = self._client.chat.completions.with_raw_response.create(
            model=group,
            messages=messages,  # type: ignore[arg-type]  # gateway speaks plain dicts
            max_tokens=max_tokens,
            extra_body=extra_body,
        )
        parsed = raw.parse()
        usage = parsed.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        # Mock mode bills nothing, so model the cost from real token usage at list rates
        # (honest, no API spend); a real proxy reports its own billed cost via the header.
        cost = (modeled_cost(group, input_tokens, output_tokens)
                if mocked else _cost_from_headers(raw.headers))
        return GatewayResponse(
            text=parsed.choices[0].message.content or "",
            model=parsed.model,
            group=group,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )

    def embed(
        self,
        ctx: RunContext,
        *,
        texts: list[str],
        group: str = "embed",
    ) -> list[list[float]]:
        self._enforce_budget(ctx)
        if self.mock:
            # Keyless AND serverless: deterministic vectors, no proxy round-trip.
            return [_mock_embedding(text) for text in texts]
        raw = self._client.embeddings.with_raw_response.create(
            model=group,
            input=texts,
            extra_body={"metadata": self._metering_metadata(ctx)},
        )
        parsed = raw.parse()
        return [item.embedding for item in sorted(parsed.data, key=lambda d: d.index)]

    def _enforce_budget(self, ctx: RunContext) -> None:
        if ctx.budget_usd_remaining is not None and ctx.budget_usd_remaining <= 0:
            raise BudgetExceededError(
                f"budget exhausted for run {ctx.run_id} "
                f"(tenant={ctx.tenant_id}, agent={ctx.agent or '-'})"
            )

    @staticmethod
    def _metering_metadata(ctx: RunContext) -> dict[str, list[str]]:
        return {"tags": [f"{k}:{v}" for k, v in ctx.metadata_tags().items()]}
