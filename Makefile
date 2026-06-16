.DEFAULT_GOAL := help
SHELL := /bin/bash

# Load .env if present
ifneq (,$(wildcard .env))
include .env
export
endif

help: ## List targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

up: ## Start the platform (postgres + pgvector, LiteLLM gateway)
	docker compose up -d --wait

down: ## Stop the platform
	docker compose down

sync: ## Install/refresh all Python workspace packages
	uv sync --all-packages --dev

seed: ## Generate + load the Borealis Manufacturing dataset
	uv run steel-foundry generate --out data/seed
	uv run steel-foundry load --from data/seed

smoke: ## Demo 0: echo agent runs from manifest through gateway; audit + ledger written
	uv run python parts/engine/demo/demo_0.py

demo-p0: smoke ## Alias for the P0 demo

demo-p1: ## Demo 1: supplier intelligence — one agent, four personas, permission-aware
	uv run python parts/engine/demo/demo_1.py

demo-p2: ## Demo 2: autonomous sourcing — gates, kill -9 resume, governor, kill switch
	uv run python parts/engine/demo/demo_2.py

demo-p3: ## Demo 3: the orchestrated fleet — one intake, one trace, one chain
	uv run python parts/engine/demo/demo_3.py

demo-p4: ## Demo 4: autonomous negotiation under a bounded mandate
	uv run python parts/engine/demo/demo_4.py

evals: ## Run all eval suites (keyless: deterministic policy + retrieval correctness)
	uv run python evals/run_suite1.py
	uv run python evals/run_suite2.py
	uv run python evals/run_suite3.py
	uv run python evals/run_suite4.py

portability: ## Prove the manifest is the contract: suite 1 on the miniloop runtime
	uv run python evals/run_miniloop.py

maturity: ## Print the eval-gated autonomy promotion ladder
	uv run python evals/run_maturity.py

schemas: ## Export JSON Schemas from steel-manifest pydantic models
	uv run steel-manifest export-schemas --out schemas/

demo-part-%: ## Run a part's standalone demo, e.g. make demo-part-blackbox
	uv run python parts/$*/demo/demo.py

api: ## Run the control plane on :8400
	uv run uvicorn --factory steel_api.main:create_app --port 8400

console: ## Run the console on :3000 (needs `make api` in another shell)
	pnpm --dir apps/console dev

console-build: ## Production-build the console
	pnpm --dir apps/console install && pnpm --dir apps/console build

lint: ## Ruff + import-boundary contracts
	uv run ruff check .
	uv run lint-imports

fmt: ## Auto-format
	uv run ruff format .
	uv run ruff check --fix .

test: ## Unit tests
	uv run pytest

ci: lint test ## What CI runs

.PHONY: help up down sync seed smoke demo-p0 evals schemas lint fmt test ci
