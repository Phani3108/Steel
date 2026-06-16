"""registry: both faces of every server — plain functions and FastMCP tools — agree."""

from __future__ import annotations

import asyncio

import pytest
from steel_mcp import SERVERS, in_process_tools

EXPECTED = {
    "supplier-master": {"search_suppliers", "get_supplier"},
    "sourcing-events": {
        "create_event", "invite_suppliers", "open_bidding", "submit_bid",
        "list_bids", "score_bids", "award", "get_event",
    },
    "contracts": {"search_contracts"},
    "spend-analytics": {"spend_cube", "price_benchmark"},
    "intake": {"submit_request", "list_requests", "get_request"},
}


def test_five_servers_registered() -> None:
    assert set(SERVERS) == set(EXPECTED)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_in_process_tools_match_expected(name: str) -> None:
    tools = in_process_tools(name)
    assert set(tools) == EXPECTED[name]
    assert all(callable(fn) for fn in tools.values())


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_fastmcp_server_lists_the_same_tools(name: str) -> None:
    listed = asyncio.run(SERVERS[name].list_tools())
    assert {t.name for t in listed} == EXPECTED[name]
    assert all(t.description for t in listed), "every tool needs a docstring/description"


def test_unknown_server_raises() -> None:
    with pytest.raises(KeyError):
        in_process_tools("invoices")
