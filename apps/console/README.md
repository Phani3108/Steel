# steel-console

**SYSTEM: COCKPIT** — the human interface of the STEEL platform.

One-line purpose: the cockpit shell — a Next.js app showing platform state: the parts
catalog, costs, and run audit trails, read live from the control-plane API.

## Standalone use case

steel-console is a generic **agent-operations dashboard**. Any system that exposes three
plain HTTP endpoints can use it as-is, with zero STEEL code:

- `GET /costs?by=<dimension>` → `[{key, calls, input_tokens, output_tokens, cost_usd}]`
- `GET /runs` → `[{run_id, ...}]`
- `GET /runs/{id}/events` → `[{event_id, ts, action, outcome, actor_id, actor_role, agent, detail, ...}]`

Point `NEXT_PUBLIC_STEEL_API_URL` at your API and you get a live cost dashboard and a
clickable audit timeline for every run — useful for any agent platform that records
spend and audit events, not just STEEL.

## Pages

| Route | What it shows |
|---|---|
| `/` | Parts catalog — the six systems and their parts as a static tree with status pills |
| `/costs` | Cost table from `GET /costs`, toggle between `by=agent` and `by=tenant_id` |
| `/runs` | Run list from `GET /runs`; click a run to render its audit timeline (`GET /runs/{id}/events`) with action/outcome chips |

All data pages poll every 2 seconds with plain `fetch` in client components. If the
control plane is unreachable, a "control plane offline" banner appears and the last
known state stays on screen.

## Run it

```bash
cd apps/console
pnpm install
pnpm dev        # http://localhost:3000
```

Production build:

```bash
pnpm build && pnpm start
```

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `NEXT_PUBLIC_STEEL_API_URL` | `http://localhost:8400` | Base URL of the control-plane API |

The console fetches from the **browser**, so the control plane must allow CORS from the
console's origin (e.g. `http://localhost:3000`).

## Demo

1. Start the platform services and the control plane (`docker compose up -d` and the
   `steel-api` app on port 8400) from the repo root.
2. `pnpm dev` here, then open `http://localhost:3000`.
3. With the API down, the pages still render — banner up, catalog intact. Start the API
   and the costs/runs pages go live within 2 seconds.

## Structure

```
src/
  app/            # App Router pages: / (catalog), /costs, /runs
  components/     # Nav, OfflineBanner
  lib/api.ts      # typed fetch helpers + API base resolution
  lib/usePoll.ts  # 2s polling hook, offline-tolerant
```

Stack: Next.js (App Router) · TypeScript · Tailwind CSS. Deliberately minimal this
phase: no component library, no data-fetching library.
