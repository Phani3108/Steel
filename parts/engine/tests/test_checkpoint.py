"""Checkpointer path: a run with a thread_id persists state in Postgres and a second
invoke on the same thread resumes from it. Skips when no Postgres is reachable."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from engine_fakes import FakeBlackBox, FakeGateway, FakeMeter
from steel_engine import compile_manifest
from steel_manifest import AgentManifest, RunContext


def test_run_with_thread_id_resumes(
    postgres_url: str,
    echo_manifest: AgentManifest,
    echo_dir: Path,
    ctx: RunContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POSTGRES_URL", postgres_url)
    agent = compile_manifest(
        echo_manifest,
        gateway=FakeGateway(),
        blackbox=FakeBlackBox(),
        meter=FakeMeter(),
        prompt_base=echo_dir,
    )
    assert agent.checkpointer is not None
    thread_id = f"t-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    try:
        first = agent.run(ctx, "Hello, STEEL.", thread_id=thread_id)
        snapshot = agent.graph.get_state(config)
        assert snapshot.values["output"] == first.text  # checkpoint survived the run

        second = agent.run(ctx, "Hello again, STEEL.", thread_id=thread_id)
        assert second.text == first.text  # fake gateway is constant; the run completed
        resumed = agent.graph.get_state(config)
        assert resumed.values["input"] == "Hello again, STEEL."
    finally:
        agent.close()
