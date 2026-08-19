# Kala

AI learning companion and digital learning twin, delivered as an intelligence layer on top of the LMS (Blackboard, Canvas).

For project context and implementation details, see `docs/masterplan.md`, `docs/stack.md`, and the module-specific READMEs.

## Quick start

Prerequisites: [pnpm](https://pnpm.io) and [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`). The root workspace installs both Supabase CLI and AWS CLI locally through setup, so no separate global `supabase` or `aws` install is needed.

```bash
pnpm setup        # installs apps/web (pnpm) + services/api and services/worker (uv)
pnpm dev          # web app on :5173
pnpm api:dev      # backend on :8000
pnpm exec supabase --help
pnpm aws --version
```

`pnpm setup` also appends a small, idempotent PATH block to your shell rc file (`~/.zshrc` on macOS zsh, `~/.bashrc` on bash) so you can run `aws ...` directly after reloading your shell (`source ~/.zshrc`) or opening a new terminal.

Each module can also be installed independently. See the README in `apps/web`, `services/api`, and `services/worker`.

## Layout

* `apps/web` — React + Vite SPA (product UI)
* `services/api` — FastAPI backend (LTI, connectors, AI, twin)
* `services/worker` — asynchronous twin recompute
* `packages/db` — SQL migrations and RLS (tenancy)
* `packages/schema` — shared contracts
* `infra` — AWS infrastructure as code
* `docs` — masterplan, stack, and architecture documentation

## CI

Three path-scoped GitHub Actions workflows live in `.github/workflows`, one per installable module: `web-ci.yml`, `api-ci.yml`, and `worker-ci.yml`.

Each workflow runs only when its corresponding module or shared `packages/` code changes. It installs dependencies using the module's actual package manager, pnpm or uv, against the committed lockfile, then runs the relevant linting, type checking or import validation, and build steps.

Docker is intentionally excluded from CI and remains a deploy-time concern. See `services/api/Dockerfile`, `services/worker/Dockerfile`, and `infra/terraform`.