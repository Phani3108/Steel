"""FastAPI app factory for the JAI control plane (COCKPIT backend).

Every endpoint degrades gracefully: when Postgres is unreachable, data routes
answer 503 with a JSON error envelope and /health answers 200 with
``postgres: false`` — the console never sees a raw stack trace.
"""

from __future__ import annotations

import os
from typing import Annotated, Any, Literal

import psycopg
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from jai_api import chat, queries
from jai_api.db import ping


class DecideRequest(BaseModel):
    approver: str
    approve: bool
    note: str = ""

Dimension = Literal["tenant_id", "agent", "run_id", "model_group"]


def _pg_unavailable(exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"error": "postgres_unavailable", "detail": str(exc).strip()},
    )


def create_app() -> FastAPI:
    """Build the read-only control-plane app the console talks to."""
    app = FastAPI(
        title="jai-api",
        version="0.1.0",
        description="JAI control plane — read-only: costs, runs, audit verification, health.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "postgres": ping()}

    @app.get("/costs")
    def costs(by: Annotated[Dimension, Query()] = "tenant_id") -> Any:
        try:
            return queries.costs_by(by)
        except (psycopg.Error, OSError) as exc:
            return _pg_unavailable(exc)

    @app.get("/runs")
    def runs(limit: Annotated[int, Query(ge=1, le=500)] = 20) -> Any:
        try:
            return queries.list_runs(limit)
        except (psycopg.Error, OSError) as exc:
            return _pg_unavailable(exc)

    @app.get("/runs/{run_id}/events")
    def events_for_run(run_id: str) -> Any:
        try:
            return queries.run_events(run_id)
        except (psycopg.Error, OSError) as exc:
            return _pg_unavailable(exc)

    @app.get("/audit/verify")
    def audit_verify() -> Any:
        try:
            return queries.verify_chain()
        except (psycopg.Error, OSError) as exc:
            return _pg_unavailable(exc)

    @app.get("/meta")
    def meta() -> Any:
        try:
            tenants = queries.tenants()
        except (psycopg.Error, OSError):
            tenants = []  # cortex not ingested yet — the console renders a hint
        return {"tenants": tenants, "roles": ["requester", "category_manager", "cpo"]}

    @app.post("/chat")
    def post_chat(req: chat.ChatRequest) -> Any:
        try:
            return chat.run_chat(req)
        except FileNotFoundError as exc:
            return JSONResponse(status_code=503, content={"error": "agent_unavailable",
                                                          "detail": str(exc)})
        except (psycopg.Error, OSError) as exc:
            return _pg_unavailable(exc)

    @app.get("/approvals")
    def approvals(tenant_id: str | None = None) -> Any:
        try:
            from jai_brakes import Brakes

            brakes = Brakes()
            brakes.ensure_schema()
            return brakes.pending(tenant_id)
        except (psycopg.Error, OSError) as exc:
            return _pg_unavailable(exc)

    @app.post("/approvals/{approval_id}/decide")
    def decide_approval(approval_id: int, req: DecideRequest) -> Any:
        try:
            from jai_brakes import Brakes

            row = Brakes().decide(approval_id, approver=req.approver,
                                  approve=req.approve, note=req.note)
            return row
        except ValueError as exc:  # already decided / unknown id
            return JSONResponse(status_code=409, content={"error": "undecidable",
                                                          "detail": str(exc)})
        except (psycopg.Error, OSError) as exc:
            return _pg_unavailable(exc)

    return app


def serve() -> None:
    """Console-script entrypoint: uvicorn on PORT (default 8400)."""
    uvicorn.run(
        create_app(),
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8400")),
    )
