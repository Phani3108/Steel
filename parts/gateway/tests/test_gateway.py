"""GatewayClient unit tests — zero network: the openai client object is replaced by a
tiny fake whose with_raw_response endpoints record kwargs and return canned stubs."""

from types import SimpleNamespace
from typing import Any

import pytest
from steel_gateway import BudgetExceededError, GatewayClient
from steel_gateway.client import MOCK_EMBED_DIM
from steel_gateway.pricing import modeled_cost
from steel_manifest import RunContext


def make_ctx(budget: float | None = None) -> RunContext:
    return RunContext(
        tenant_id="t1",
        actor={"id": "u1", "role": "requester"},
        agent="agent-test",
        budget_usd_remaining=budget,
    )


class FakeRaw:
    """Stub for the openai raw-response wrapper: .headers plus .parse()."""

    def __init__(self, parsed: Any, headers: dict[str, str] | None = None) -> None:
        self.headers = headers or {}
        self._parsed = parsed

    def parse(self) -> Any:
        return self._parsed


class FakeEndpoint:
    """Stands in for chat.completions.with_raw_response / embeddings.with_raw_response."""

    def __init__(self, raw: FakeRaw) -> None:
        self.raw = raw
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> FakeRaw:
        self.calls.append(kwargs)
        return self.raw


def chat_parsed(content: str = "stub answer", model: str = "provider/model-x") -> Any:
    return SimpleNamespace(
        model=model,
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=7),
    )


def make_client(
    *,
    mock: bool,
    chat: FakeEndpoint | None = None,
    embeddings: FakeEndpoint | None = None,
) -> tuple[GatewayClient, FakeEndpoint, FakeEndpoint]:
    chat = chat or FakeEndpoint(FakeRaw(chat_parsed()))
    embeddings = embeddings or FakeEndpoint(FakeRaw(SimpleNamespace(data=[])))
    client = GatewayClient(base_url="http://fake:4000", api_key="sk-fake", mock=mock)
    client._client = SimpleNamespace(  # type: ignore[assignment]
        chat=SimpleNamespace(completions=SimpleNamespace(with_raw_response=chat)),
        embeddings=SimpleNamespace(with_raw_response=embeddings),
    )
    return client, chat, embeddings


MESSAGES = [{"role": "user", "content": "hi"}]


def test_exhausted_budget_raises_before_any_dispatch() -> None:
    client, chat, _ = make_client(mock=True)
    with pytest.raises(BudgetExceededError):
        client.complete(make_ctx(budget=0.0), group="fast", messages=MESSAGES)
    assert chat.calls == []


def test_no_budget_set_means_no_gate() -> None:
    client, chat, _ = make_client(mock=True)
    client.complete(make_ctx(budget=None), group="fast", messages=MESSAGES)
    assert len(chat.calls) == 1


def test_metadata_tags_attached_via_extra_body() -> None:
    client, chat, _ = make_client(mock=True)
    ctx = make_ctx(budget=1.0)
    client.complete(ctx, group="reasoning", messages=MESSAGES)
    tags = chat.calls[0]["extra_body"]["metadata"]["tags"]
    expected = {f"{k}:{v}" for k, v in ctx.metadata_tags().items()}
    assert expected <= set(tags)
    assert "agent:agent-test" in tags


def test_mock_path_sends_mock_response_and_models_cost_from_tokens() -> None:
    chat = FakeEndpoint(FakeRaw(chat_parsed(), headers={"x-litellm-response-cost": "0.42"}))
    client, chat, _ = make_client(mock=True, chat=chat)
    resp = client.complete(
        make_ctx(budget=1.0), group="fast", messages=MESSAGES, mock_response="hello"
    )
    assert chat.calls[0]["extra_body"]["mock_response"] == "hello"
    # Mock mode ignores any billed-cost header and MODELS cost from real token usage.
    assert resp.cost_usd == modeled_cost("fast", 12, 7) > 0.0
    assert resp.text == "stub answer"
    assert resp.group == "fast"
    assert resp.model == "provider/model-x"
    assert (resp.input_tokens, resp.output_tokens) == (12, 7)


def test_explicit_mock_response_forces_mock_even_when_client_is_live() -> None:
    chat = FakeEndpoint(FakeRaw(chat_parsed(), headers={"x-litellm-response-cost": "0.42"}))
    client, chat, _ = make_client(mock=False, chat=chat)
    resp = client.complete(make_ctx(), group="fast", messages=MESSAGES, mock_response="canned")
    assert chat.calls[0]["extra_body"]["mock_response"] == "canned"
    assert resp.cost_usd == modeled_cost("fast", 12, 7)  # modeled, not the header


def test_live_path_reads_cost_header_and_sends_no_mock_response() -> None:
    chat = FakeEndpoint(FakeRaw(chat_parsed(), headers={"x-litellm-response-cost": "0.0123"}))
    client, chat, _ = make_client(mock=False, chat=chat)
    resp = client.complete(make_ctx(), group="reasoning", messages=MESSAGES)
    assert resp.cost_usd == pytest.approx(0.0123)
    assert "mock_response" not in chat.calls[0]["extra_body"]


def test_missing_or_garbled_cost_header_falls_back_to_zero() -> None:
    for headers in ({}, {"x-litellm-response-cost": "not-a-float"}):
        chat = FakeEndpoint(FakeRaw(chat_parsed(), headers=headers))
        client, chat, _ = make_client(mock=False, chat=chat)
        resp = client.complete(make_ctx(), group="fast", messages=MESSAGES)
        assert resp.cost_usd == 0.0


def test_embed_mock_is_deterministic_dim8_and_never_calls_the_server() -> None:
    client, _, embeddings = make_client(mock=True)
    first = client.embed(make_ctx(), texts=["alpha", "beta"])
    second = client.embed(make_ctx(), texts=["alpha", "beta"])
    assert first == second
    assert all(len(vec) == MOCK_EMBED_DIM for vec in first)
    assert first[0] != first[1]  # distinct texts, distinct vectors
    assert embeddings.calls == []


def test_embed_respects_the_budget_gate() -> None:
    client, _, _ = make_client(mock=True)
    with pytest.raises(BudgetExceededError):
        client.embed(make_ctx(budget=0.0), texts=["alpha"])
