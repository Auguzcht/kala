# Kala

AI learning companion and digital learning twin, delivered as an intelligence layer on top of the LMS (Blackboard, Canvas).

For project context and implementation details, see `docs/masterplan.md`, `docs/stack.md`, and the module-specific READMEs.

## Quick start

Prerequisites: [pnpm](https://pnpm.io) and [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`). The root workspace installs both Supabase CLI and AWS CLI locally through setup, so no separate global `supabase` or `aws` install is needed.

```bash
pnpm setup        # installs apps/web (pnpm) + services/api and services/worker (uv)
pnpm dev          # web app on :5173
pnpm api:dev      # backend on :8000
pnpm --filter web gen:api   # regenerate backend OpenAPI export + frontend types (one chain, via pregen:api)
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

## Deploying to Vercel (services model)

One Vercel project, three services, wired in root `vercel.json`:

- `web` (Vite SPA) serves everything at `/`; the catch-all rewrite sends SPA routes to it.
- `api` (FastAPI) is mounted at `/api/api/*`; a `request.path` transform strips the prefix so the app sees its real routes (`/health`, `/lti/login`, `/courses/...`).
- `worker` (async jobs) is mounted at `/api/worker` via a minimal ASGI entry (`services/worker/app/http.py`) — usable as a Vercel cron target in place of EventBridge.

Python services install from the generated `requirements.txt` (uv export) — no build step. The Vite service uses its own `build` script (`tsr generate && tsc -b && vite build`).

Required env vars, set per-service in the Vercel dashboard:

| Service | Vars |
|---|---|
| `web` | `VITE_API_BASE_URL=/api/api` (client already defaults to this), `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` |
| `api` | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`, `FRONTEND_URL` (must be the deployed origin — the LTI launch redirects there), `AI_PROVIDER`/`EMBED_PROVIDER` plus provider keys, all `LTI_*` and `LMS_REST_*` values from `services/api/.env.example` |
| `worker` | same Supabase values as `api` (for the future real jobs) |

Gotchas:

- If `FRONTEND_URL` is wrong, the LTI launch redirects to localhost. Set it to the Vercel deployment/production URL.
- Long model runs (skill proposal, ingest) may exceed the plan's default `maxDuration`; raise it for the api service in the dashboard if those endpoints time out.
- Vercel cold starts replace the Lambda warm-start concern; if the launch handshake feels flaky on stage, add a scheduled ping to `/api/api/lti/login`.
