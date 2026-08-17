# Kala

AI learning companion and digital learning twin, delivered as an intelligence layer on top of the LMS (Blackboard, Canvas).

Start here: read `CLAUDE.md` at the repo root. It routes you to `docs/masterplan.md`, `docs/stack.md`, and the per-folder guides.

## Quick start

Prerequisites: [pnpm](https://pnpm.io) and [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`).

```
pnpm setup        # installs apps/web (pnpm) + services/api and services/worker (uv)
pnpm dev          # web app on :5173
pnpm api:dev      # backend on :8000
```

Each module is also installable on its own, see the README in `apps/web`, `services/api`, and `services/worker`.

## Layout

- `apps/web` — React + Vite SPA (the product UI)
- `services/api` — FastAPI backend (LTI, connectors, AI, twin)
- `services/worker` — async twin recompute
- `packages/db` — SQL migrations and RLS (tenancy)
- `packages/schema` — shared contracts
- `infra` — AWS IaC
- `docs` — masterplan, stack, architecture

## CI

Three path-scoped GitHub Actions workflows in `.github/workflows`, one per installable module (`web-ci.yml`, `api-ci.yml`, `worker-ci.yml`). Each only runs when its own module (or `packages/`) changes, installs with the module's real package manager (pnpm or uv) against the committed lockfile, then lints, typechecks/imports, and builds. No Docker in CI, that stays a deploy-time concern (see `services/api/Dockerfile`, `services/worker/Dockerfile`, and `infra/terraform`).
