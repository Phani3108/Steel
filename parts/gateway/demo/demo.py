"""jai-gateway standalone demo — a model call through the LiteLLM proxy with NO provider
keys: routing by group, metering tags, cost extraction, and the pre-dispatch budget gate.

Requires the platform proxy:   docker compose up -d --wait   (LiteLLM on :4000)
Run:                           python parts/gateway/demo/demo.py
"""

from jai_gateway import BudgetExceededError, GatewayClient
from jai_manifest import RunContext


def main() -> None:
    ctx = RunContext(
        tenant_id="borealis",
        actor={"id": "u-dana", "name": "Dana", "role": "category_manager"},
        budget_usd_remaining=0.50,
    ).child(agent="agent-demo")

    client = GatewayClient()  # LITELLM_BASE_URL / LITELLM_MASTER_KEY / JAI_MOCK from env

    print("── metering tags sent with every call ──")
    for key, value in ctx.metadata_tags().items():
        print(f"  {key}: {value}")

    print("\n── complete(group='fast') served keyless via mock_response ──")
    response = client.complete(
        ctx,
        group="fast",
        messages=[{"role": "user", "content": "Say hello to the JAI demo."}],
        mock_response="Hello from jai-gateway — routed, tagged, metered, zero keys used.",
    )
    print(response.model_dump_json(indent=2))

    print("\n── embed(): deterministic mock vectors (dim 8) ──")
    vectors = client.embed(ctx, texts=["supplier risk", "contract renewal"])
    for text, vec in zip(["supplier risk", "contract renewal"], vectors, strict=True):
        print(f"  {text!r} -> {vec}")

    print("\n── budget gate: an exhausted context is refused PRE-dispatch ──")
    broke = ctx.model_copy(update={"budget_usd_remaining": 0.0})
    try:
        client.complete(broke, group="fast", messages=[{"role": "user", "content": "hi"}])
    except BudgetExceededError as exc:
        print(f"  BudgetExceededError (as designed): {exc}")


if __name__ == "__main__":
    main()
