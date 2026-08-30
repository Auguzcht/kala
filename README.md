# Kala

AI learning companion and digital learning twin, delivered as an intelligence layer on top of the LMS (Blackboard, Canvas).

For project context and implementation details, see `docs/masterplan.md`, `docs/stack.md`, and the module-specific READMEs.

## Quick start

Prerequisites: [pnpm](https://pnpm.io) and [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`). The root workspace installs the Supabase CLI, AWS CLI, and Terraform locally through setup, so no separate global `supabase`, `aws`, or `terraform` install is needed. Docker is the one genuinely manual prerequisite — install Docker Desktop (Mac/Windows) or Docker Engine (Linux) from the official docs: <https://docs.docker.com/get-docker/>.

```bash
pnpm setup        # installs apps/web (pnpm) + services/api and services/worker (uv)
pnpm dev          # web app on :5173
pnpm api:dev      # backend on :8000
pnpm --filter web gen:api   # regenerate backend OpenAPI export + frontend types (one chain, via pregen:api)
pnpm exec supabase --help
pnpm aws --version
pnpm terraform -version
```

`pnpm setup` also appends small, idempotent PATH blocks to your shell rc file (`~/.zshrc` on macOS zsh, `~/.bashrc` on bash) so you can run `aws ...` and `terraform ...` directly after reloading your shell (`source ~/.zshrc`) or opening a new terminal. Docker is not vendored — see the Docker install link above — and `bash check_stack.sh` verifies it (section 5) plus the vendored Terraform (section 6) before you start dev.

Each module can also be installed independently. See the README in `apps/web`, `services/api`, and `services/worker`.

## Development workflow (integrated stack)

Kala's backend now runs on AWS (API Gateway + Lambda, see `infra/terraform`). The local frontend at `:5173` can talk to either the local backend or the deployed one, and the session is a bearer JWT either way — both environments sign with the same Supabase JWT secret, so a token minted by one backend works against the other.

There are two ways to get a session into the local frontend:

### Option A — Mock LTI launch (no LMS, no real data)

Exercises the real `/lti/login` → `/lti/launch` flow against a fake platform, in-process — no Blackboard, no uvicorn needed. Requires Supabase creds in `services/api/.env`:

```bash
pnpm api:dev              # local backend on :8000 (separate terminal)
pnpm dev                  # local frontend on :5173
cd services/api && uv run python scripts/mock_lti_launch.py   # prints "Session token: ..."
```

Copy the printed token into the local frontend:

```
http://localhost:5173/launch#token=<mock token>
```

With `apps/web/.env.local` set to `VITE_API_BASE_URL=http://localhost:8000`, this runs the full stack locally against mock data — the auth spine, the UI, and Supabase writes (a `Mock Course` row appears).

### Option B — Real Blackboard data (the integrated flow)

Point the local frontend at the deployed backend, then reuse a real session token from a live LTI launch:

1. `apps/web/.env.local`: set `VITE_API_BASE_URL` to the API Gateway URL (the `api_base_url` terraform output), e.g. `https://14vua0ys43.execute-api.ap-southeast-1.amazonaws.com`. Before the AWS integration this pointed at an ngrok tunnel to `localhost:8000`; ngrok is no longer needed — the deployed API is directly reachable and its CORS allows `localhost:5173`.
2. Restart `pnpm dev` so Vite picks up the new env.
3. In the real Blackboard instance, click the Kala LTI link. The launch redirects to the Vercel frontend with the token in the URL hash:
   `https://kala-web-lovat.vercel.app/launch#token=<real token>`.
4. Copy that token and open it in the local frontend:
   `http://localhost:5173/launch#token=<same real token>`.

The local app now runs with the real session: real course content, roster, and twin state served by the deployed backend — useful for UI work that needs real data without rebuilding the backend for every change.

### Deploying backend changes

After changing backend code, rebuild, push, and force Lambda to re-resolve the image digest in one command:

```bash
make deploy   # = ecr-login + build (amd64, no attestations) + push + lambda update-function-code
```

Infra changes (`.tf`) still go through `terraform apply` from `infra/terraform` (see that folder's README).


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