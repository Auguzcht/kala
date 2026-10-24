# Local development entry point

This is a source-checked command index, extracted for WI-03 on 2026-10-24 at base `e9de105`. It is not a verified zero-to-running runbook. [Runbook authoring remains planned](runbooks/README.md). Do not use historical README claims as proof that local and hosted environments share credentials.

| Task | Existing command / owner | Limits |
| --- | --- | --- |
| Locked web dependencies | `pnpm install --frozen-lockfile` | pnpm version comes from root `packageManager`; do not mutate shared checkout dependencies. |
| API / worker dependencies | `uv sync --frozen` from the corresponding service directory | Each service owns its `uv.lock`; Lambda requirements are generated exports, never handwritten. |
| Web checks | `pnpm --filter web lint`, `pnpm --filter web typecheck`, `pnpm --filter web build` | Application changes need their own lane evidence. |
| API / worker tests | `uv run pytest` in the service | Shared isolation in `services/conftest.py` disables dotenv, replaces inherited app/AWS configuration with fake test settings, generates a JWT signing key and blocks network sockets before test collection. No lane-specific runner or .env is needed. |
| Existing dev servers | `pnpm dev`, `pnpm api:dev` | Vite uses 5173, API uses 8000. Do not start another Vite or alter an existing user's server. |
| OpenAPI types | `pnpm --filter web gen:api` | Runs API export first via pregen hook. Review generated changes in the owning code lane. |
| Full tooling setup | `pnpm setup` | Includes AWS/Terraform installs and shell PATH changes; do not run casually as a documentation check. |

Configuration names and placeholders are owned by Lane C in [secrets.md](secrets.md). This documentation lane has not opened environment files. The local throwaway database workflow is owned by Lane DB in [database.md](database.md), gated on Fred's hosted Postgres major and a post-D rebase; it is not installed by this lane. Keep generated database types at `packages/schema/supabase.ts`, the existing imported path. Numeric migration filenames are retained unchanged.

## Automated test isolation contract

[APPROVAL-03](../work/handover-2026/approval-03.md), implementing APPROVAL-02 section 5, replaces the Study launcher and external Tutor launcher with one service-wide pytest conftest. Each service's pytest configuration sets `addopts = "--confcutdir=.."` so the shared parent conftest is discovered before collection. Run API and worker suites in separate processes from their service directories: each service has its own `app` package and uv environment. Configuration isolation and socket blocking start before test modules import application code. Unix socket pairs used by in-process ASGI/asyncio tests remain available; IPv4/IPv6 sockets and DNS lookups are blocked. These are mocked unit/integration suites, not live LMS, provider or database smoke tests. Test configuration and generated signing material must never be used for a running application or deployment.

The API tests' existing UUID constants stay in their local conftest. Existing test bodies remain unchanged. Frontend component tests retain their documented custom/external fixtures for this integration; [WI-20](../work/handover-2026/work-items/WI-20-frontend-test-runner.md) plans a standard runner without adding dependencies now.

## Component provenance

The main-only component install guide is a historical setup reference; its Next.js assumption is superseded by the React/Vite stack in [stack.md](../stack.md). shadcn primitives belong in `components/ui`, product motifs in `components/kala`, marketing-only flourishes in `components/marketing`; feature components remain feature-owned.

The ignored motion guide records manual copies of actual Motion Primitives registry sources after HTTP 429/rate limits, rather than approximate rewrites. It also records sliding-number provenance and its react-use-measure dependency. React 19 adaptations use `React.JSX.IntrinsicElements`; destructure-to-omit patterns depend on ESLint `ignoreRestSiblings`. TransitionPanel has caller-provided variants. Consumers, rather than those primitives, must respect reduced motion. These historical sourcing notes do not verify today's vendor CLI, package availability or version.

Sources: root/service/frontend READMEs retained at their original paths, [guide extraction](../work/handover-2026/evidence/local-guide-knowledge.md), [stack rationale](../stack.md), and [DESIGN.md](../../apps/web/src/styles/DESIGN.md).
