"""jai-mcp CLI: serve one drivetrain server over streamable HTTP, or list its tools."""

from __future__ import annotations

import argparse

from jai_mcp.db import ensure_schemas
from jai_mcp.registry import SERVERS, in_process_tools


def main() -> None:
    parser = argparse.ArgumentParser(prog="jai-mcp")
    sub = parser.add_subparsers(dest="cmd", required=True)
    names = sorted(SERVERS)

    p_serve = sub.add_parser("serve", help="run one MCP server (streamable-http)")
    p_serve.add_argument("server", choices=names)
    p_serve.add_argument("--port", type=int, default=8100)

    p_tools = sub.add_parser("tools", help="print a server's tool names")
    p_tools.add_argument("server", choices=names)

    args = parser.parse_args()
    if args.cmd == "tools":
        for name in in_process_tools(args.server):
            print(name)
        return

    ensure_schemas()
    server = SERVERS[args.server]
    server.settings.port = args.port
    # TODO(P3): HTTP deployments add auth middleware that resolves tenant_id/role
    # from the bearer token instead of trusting them as tool parameters.
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
