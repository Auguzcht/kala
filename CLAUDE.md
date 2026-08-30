# CLAUDE.md — Kala master orchestrator

## Standing constraint (do not remove)

Do not introduce, modify, or propose changes to deployment targets, infrastructure, or hosting architecture (Vercel config, Terraform, Docker, CI/CD, Lambda, EventBridge) without being explicitly asked in the current task. If a task seems to require an infra change, stop and name the proposed change and why, but do not commit it. Frontend and backend feature work only, unless the prompt says otherwise.

This file is loaded at the start of every session. It is a router, not an encyclopedia. It tells you what Kala is, the rules you must never break, and where to read deeper context on demand. Do not try to hold the whole system in your head. Read the local `CLAUDE.md` for the area you are about to touch.

## What Kala is

Kala is an AI learning companion and digital learning twin delivered as an intelligence layer on top of the LMS (Blackboard and Canvas), not a competitor to it. We do not host courses. We read the LMS as the source of truth and produce what the LMS cannot: a longitudinal, Bloom's-aligned model of each learner, plus early-warning analytics for teachers. Users enter through an LTI 1.3 link inside their LMS course, which opens Kala as a first-party page.

Pilot: Mapua Malayan Colleges Mindanao, College of Engineering and Architecture. Hard demo deadline: September 1.

## Sources of truth (read when relevant, not every time)

- `docs/masterplan.md` — product, architecture, digital twin model, phases, research plan. Read before any architectural or data-model decision.
- `docs/stack.md` — finalized frontend and dev-stack decisions. Read before touching build config, state, auth, or tenancy.
- `apps/web/src/styles/DESIGN.md` — visual system, tokens, component rules. Read before writing or restyling any UI.

## On-demand context system (the key mechanic)

Context is distributed. Almost every meaningful folder has its own `CLAUDE.md` scoped to that area. The rule:

> Before creating or editing files inside a folder, read that folder's `CLAUDE.md` first. Do not preload them all. Load the one for the area you are working in, plus the sources of truth above if the task is cross-cutting.

Folder guides live in: `apps/web/src/features/*`, `apps/web/src/features/_TEMPLATE`, `apps/web/src/hooks`, `apps/web/src/components`, `apps/web/src/lib`, `apps/web/src/stores`, `apps/web/src/app`, `services/api`, `services/worker`, `packages/db`, `packages/schema`, `infra`.

## Golden rules (non-negotiable)

1. **Multi-tenant, always.** Every persisted row carries `institution_id`. A tenant is an LMS deployment, resolved from the LTI launch (`iss` + `deployment_id`), never from a signup. Isolation is enforced by Postgres RLS. Never write a query or table that is not tenant-scoped.
2. **Auth comes from the LMS.** Identity flows LTI launch to FastAPI to a Supabase-compatible signed JWT. The frontend never runs its own password login for the LTI path. Never trust a client-supplied `institution_id` or `role`; they come from the validated token only.
3. **State has one owner.** Server data goes through TanStack Query. Auth/session belongs to Supabase. Ephemeral UI state goes in Zustand. Never mirror server data into Zustand.
4. **De-identify before any LLM call.** Send pseudonymous ids and stripped context to models, never student names or raw PII. Student learning data is sensitive under the Philippine Data Privacy Act.
5. **No secrets in the client.** Service-role keys, JWT secrets, and model keys live in the backend only. The web app holds only public anon keys and public config.
6. **Validate at the boundary.** Parse untrusted input and API responses with Zod. Frontend types are generated from the backend OpenAPI schema, not hand-written.
7. **Design tokens only.** Never hardcode colors or radii. Use the semantic and brand tokens from `DESIGN.md`.

## Architecture at a glance

Entry: LMS to LTI 1.3 launch to Kala frontend (first-party page). Frontend to API Gateway plus Lambda (FastAPI). The API fans out to an LMS connector (REST reads and grade passback), a tiered model router (Bedrock: Claude plus Titan embeddings), and Supabase (Postgres plus pgvector, the digital twin and RAG index). An EventBridge schedule drives an async worker that recomputes mastery and re-embeds content. See `docs/architecture.md` and `docs/masterplan.md` section 4.

## Repo map

```
apps/web            React + Vite SPA (the product UI)
  src/app           router, providers, root layout
  src/styles        globals.css (tokens) + DESIGN.md
  src/lib           api client, auth/session, supabase, utils  (cross-cutting)
  src/hooks         GLOBAL hooks only (app-wide, feature-agnostic)
  src/components     GLOBAL reusable UI: ui/ (shadcn), shared/, brand/
  src/stores         Zustand (ephemeral UI state only)
  src/features       feature-first modules; each owns its components/hooks/schema/api
services/api        FastAPI backend (Lambda): LTI, connectors, AI, twin
services/worker     async twin recompute + re-embed
packages/db         SQL migrations + RLS policies (tenancy lives here)
packages/schema     shared contracts / generated types
infra               IaC for AWS
docs                masterplan.md, stack.md, architecture.md
```

## Commands

```
pnpm setup                  # install everything: web (pnpm) + api and worker (uv) + aws/terraform tooling
pnpm install                # install workspace deps (web only)
pnpm exec supabase --help    # run the locally installed Supabase CLI from the root workspace
pnpm aws --version           # run the workspace-local AWS CLI from the root workspace
pnpm terraform -version      # run the workspace-local Terraform from the root workspace
pnpm setup:aws:path          # add workspace AWS CLI to your shell PATH (idempotent)
pnpm setup:terraform:path    # add workspace Terraform to your shell PATH (idempotent)
pnpm --filter web dev       # run the web app (Vite)
pnpm --filter web build     # production build
pnpm --filter web lint      # eslint
pnpm --filter web typecheck # tsc --noEmit
pnpm dlx shadcn@latest add <component>   # add a shadcn primitive into components/ui
pnpm --filter web gen:api   # regenerate frontend types from backend OpenAPI

pnpm api:dev                 # run services/api locally (uv run uvicorn ...)
cd services/api && uv sync   # install/update just the backend's deps
cd services/worker && uv sync # install/update just the worker's deps
```

`services/api` and `services/worker` are managed with [uv](https://docs.astral.sh/uv/), each has its own `pyproject.toml` and `uv.lock`. `requirements.txt` in both is a generated export (`uv export --no-hashes --no-dev -o requirements.txt`) kept only so the Lambda Dockerfiles can stay on plain `pip`, never hand-edit it.

## Conventions

- **Feature-first.** A feature owns everything it needs: `components/`, `hooks/`, `schema/`, `api/`, an `index.ts` public surface, and a `CLAUDE.md`. See `apps/web/src/features/CLAUDE.md` and copy `_TEMPLATE` for new features.
- **Hook scope is explicit.** App-wide hooks live in `src/hooks`. Feature-specific hooks live in that feature's `hooks/`. Do not put feature logic in global hooks, and do not import one feature's internals from another; go through its `index.ts`.
- **Imports** use the `@/` alias (for example `@/components/ui/button`, `@/features/diagnostic`).
- **Keep files small.** If a component passes a few hundred lines, split it.
- **Sentence case** in UI copy. Buttons name the action (`Start diagnostic`, not `Submit`).

## Design in one line

Cintana palette (navy ink, gold accent, teal secondary) on a shadcn new-york foundation, with a chevron signature and confident large headings. Buttons are pill-shaped, cards use the `xl` radius. Full rules and tokens in `apps/web/src/styles/DESIGN.md`. Read it before any UI work.

## Definition of done

Type-checks, lints, tenant-scoped, validated at the boundary, uses design tokens, keyboard-focusable with visible focus, responsive to mobile, and reduced-motion respected. If it touches data, it has an RLS policy. If it calls a model, it de-identifies first.

## Adding a new feature

1. Copy `apps/web/src/features/_TEMPLATE` to `apps/web/src/features/<name>`.
2. Fill in its `CLAUDE.md` (purpose, key files, contracts, gotchas, related masterplan section).
3. Expose the public surface in `index.ts`. Keep internals private.
4. Register routes in `src/app/router.tsx`.
