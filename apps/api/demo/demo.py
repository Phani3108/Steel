"""Standalone demo: drive the control plane in-process and read every surface.

No server, no ports — an httpx TestClient runs the exact ASGI app. With the
compose Postgres up (docker compose up -d postgres) you see real rollups; with
it down you see the graceful degraded responses instead of stack traces.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from steel_api.main import create_app


def main() -> None:
    client = TestClient(create_app())
    for path in ("/health", "/costs?by=tenant_id", "/runs?limit=5", "/audit/verify"):
        resp = client.get(path)
        print(f"GET {path}  ->  {resp.status_code}")
        print(json.dumps(resp.json(), indent=2, default=str))
        print()
    print("Serve it for real:   uv run steel-api          (PORT env, default 8400)")
    print("Then for example:    curl http://localhost:8400/health")


if __name__ == "__main__":
    main()
