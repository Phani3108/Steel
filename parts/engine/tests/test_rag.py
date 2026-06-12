"""RAG pipeline tests — fake retriever, no services needed."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from engine_fakes import FakeBlackBox, FakeGateway, FakeMeter
from jai_engine.compile import compile_manifest
from jai_manifest import Actor, RunContext, load_manifest

AGENT_DIR = Path(__file__).resolve().parents[2] / "agents" / "supplier_intel"


def _ctx(role: str = "category_manager") -> RunContext:
    return RunContext(tenant_id="TEN-0001", actor=Actor(id="t", role=role))


def _fake_retrieval(*, refused: bool = False):
    if refused:
        return SimpleNamespace(
            facts=[], chunks=[], citations=[], refused=True,
            refusal_reason="role 'requester' is not permitted to access contract",
        )
    return SimpleNamespace(
        facts=[{"id": "SUP-0001", "name": "Rampart Engineering Inc.", "country": "United States"}],
        chunks=[
            SimpleNamespace(
                model_dump=lambda: {
                    "chunk_id": "DOC-X#0", "doc_type": "policy", "doc_id": "DOC-X",
                    "source_id": "POL-001", "text": "Three competitive bids are required.",
                    "score": 0.5,
                }
            )
        ],
        citations=[
            SimpleNamespace(
                model_dump=lambda: {
                    "source_type": "supplier", "source_id": "SUP-0001",
                    "snippet": "Rampart Engineering Inc.",
                }
            )
        ],
        refused=False,
        refusal_reason=None,
    )


def _compile(retriever, monkeypatch):
    monkeypatch.setenv("JAI_MOCK", "1")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://nobody:n@127.0.0.1:1/none")  # no checkpointer
    blackbox = FakeBlackBox()
    agent = compile_manifest(
        load_manifest(AGENT_DIR / "manifest.yaml"),
        gateway=FakeGateway(),
        blackbox=blackbox,
        meter=FakeMeter(),
        prompt_base=AGENT_DIR,
        retriever=retriever,
    )
    return agent, blackbox


def test_rag_happy_path_renders_facts_verbatim(monkeypatch):
    agent, blackbox = _compile(lambda ctx, q: _fake_retrieval(), monkeypatch)
    result = agent.run(_ctx(), "Tell me about supplier Rampart Engineering Inc.")
    assert "United States" in result.text
    assert "[policy:POL-001]" in result.text
    assert result.citations and result.citations[0]["source_id"] == "SUP-0001"
    assert not result.refused
    assert blackbox.actions() == ["run.start", "retrieve", "run.end"]


def test_rag_refusal_path(monkeypatch):
    agent, blackbox = _compile(lambda ctx, q: _fake_retrieval(refused=True), monkeypatch)
    result = agent.run(_ctx("requester"), "What are the terms of the contract 'X'?")
    assert result.refused
    assert result.text.startswith("REFUSED:")
    assert "contract" in result.text
    assert ("retrieve", "denied") in [(e.action, e.outcome) for e in blackbox.events]


def test_rag_requires_retriever(monkeypatch):
    monkeypatch.setenv("JAI_MOCK", "1")
    with pytest.raises(ValueError, match="retriever"):
        compile_manifest(
            load_manifest(AGENT_DIR / "manifest.yaml"),
            gateway=FakeGateway(),
            blackbox=FakeBlackBox(),
            meter=FakeMeter(),
            prompt_base=AGENT_DIR,
        )
