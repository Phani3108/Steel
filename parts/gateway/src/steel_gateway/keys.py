"""Virtual key provisioning — one LiteLLM key per (tenant, agent) with its own budget.

The multi-tenant cost-control surface: a provisioned key carries its tenant/agent tags
and a hard max_budget enforced by the proxy itself. Requires LiteLLM running with a
DATABASE_URL (the compose file provides one). Demo-only — tests never hit this path.
"""

from __future__ import annotations

import os

import httpx


class GatewayKeyError(Exception):
    """Raised when the proxy cannot provision a virtual key (no DB, bad master key, down)."""


def provision_virtual_key(
    tenant_id: str,
    agent: str,
    max_budget_usd: float,
    *,
    base_url: str | None = None,
    master_key: str | None = None,
) -> str:
    base = (base_url or os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")).rstrip("/")
    key = master_key or os.environ.get("LITELLM_MASTER_KEY", "sk-steel-master-dev")
    payload = {
        "max_budget": max_budget_usd,
        "metadata": {"tags": [f"tenant_id:{tenant_id}", f"agent:{agent}"]},
    }
    try:
        response = httpx.post(
            f"{base}/key/generate",
            json=payload,
            headers={"Authorization": f"Bearer {key}"},
            timeout=10.0,
        )
        response.raise_for_status()
        body = response.json()
    except httpx.HTTPStatusError as exc:
        raise GatewayKeyError(
            f"key/generate returned {exc.response.status_code} — LiteLLM must run with a "
            f"DATABASE_URL and a valid master key: {exc.response.text[:200]}"
        ) from exc
    except httpx.HTTPError as exc:
        raise GatewayKeyError(f"cannot reach LiteLLM at {base}: {exc}") from exc
    try:
        return str(body["key"])
    except (KeyError, TypeError) as exc:
        raise GatewayKeyError(f"unexpected key/generate response shape: {body!r}") from exc
