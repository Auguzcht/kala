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
| Configuration catalogue | `uv run --project services/api python scripts/config_inventory.py --check` | Source/config inventory check; no hosted secret inspection. |
| Full tooling setup | `pnpm setup` | Includes AWS/Terraform installs and shell PATH changes; do not run casually as a documentation check. |

Configuration names, stores and owners are catalogued in [secrets.md](secrets.md). This documentation lane has not opened environment files. The local throwaway database workflow is pending in [database.md](database.md); confirm the hosted major before implementation. Keep generated database types at `packages/schema/supabase.ts`, the existing imported path. Numeric migration filenames are retained unchanged.

## Automated test isolation contract

The committed test setup replaces the Study launcher and external Tutor launcher with one service-wide pytest conftest. Each service's pytest configuration sets `addopts = "--confcutdir=.."` so the shared parent conftest is discovered before collection. Run API and worker suites in separate processes from their service directories: each service has its own `app` package and uv environment. Configuration isolation and socket blocking start before test modules import application code. Unix socket pairs used by in-process ASGI/asyncio tests remain available; IPv4/IPv6 sockets and DNS lookups are blocked. These are mocked unit/integration suites, not live LMS, provider or database smoke tests. Test configuration and generated signing material must never be used for a running application or deployment.

The API tests' existing UUID constants stay in their local conftest. Existing test bodies remain unchanged. Frontend component tests retain their documented custom/external fixtures for this integration; [WI-20](../work/handover-2026/work-items/WI-20-frontend-test-runner.md) plans a standard runner without adding dependencies now.

## Component provenance

The main-only component install guide is a historical setup reference; its Next.js assumption is superseded by the React/Vite stack in [current architecture](architecture.md). shadcn primitives belong in `components/ui`, product motifs in `components/kala`, marketing-only flourishes in `components/marketing`; feature components remain feature-owned.

The ignored motion guide records manual copies of actual Motion Primitives registry sources after HTTP 429/rate limits, rather than approximate rewrites. It also records sliding-number provenance and its react-use-measure dependency. React 19 adaptations use `React.JSX.IntrinsicElements`; destructure-to-omit patterns depend on ESLint `ignoreRestSiblings`. TransitionPanel has caller-provided variants. Consumers, rather than those primitives, must respect reduced motion. These historical sourcing notes do not verify today's vendor CLI, package availability or version.

Sources: current manifests, fixture loaders, committed service conftest, [runtime/state ownership](architecture.md), and [DESIGN.md](../../apps/web/src/styles/DESIGN.md).

## Portable frontend checks

Run from repository root after locked dependencies are installed, using Node 22.18 or a compatible version with built-in TypeScript stripping. These commands describe existing loaders; DOCS-HYGIENE did not install fixtures or run application suites. There is no standard frontend test runner yet. Matching external renderer fixtures and a browser executable remain required; adopting a standard runner is planned. The versions below reproduce the existing verification fixture, not a claim about the latest upstream versions.

```sh
node --experimental-vm-modules --test apps/web/src/features/tutor/components/TutorChat.test.mjs apps/web/src/features/tutor/schema/tutor.schema.test.ts apps/web/src/lib/api-error.test.ts apps/web/src/features/tutor/tests/presentation.test.mjs
export KALA_STUDY_TEST_DEPS="$(mktemp -d)"
npm install --prefix "$KALA_STUDY_TEST_DEPS" --no-save --package-lock=false react@19.2.8 react-test-renderer@19.2.8
node --experimental-vm-modules --test apps/web/src/features/flashcards/tests/study-deck.test.mjs
```

The renderer loader resolves packages relative to `KALA_STUDY_TEST_DEPS/package.json`, keeping dependencies outside the checkout. Keep React and its renderer versions matched. For browser checks prepare a separate external fixture:

```sh
export KALA_BROWSER_TEST_DEPS="$(mktemp -d)"
npm install --prefix "$KALA_BROWSER_TEST_DEPS" --no-save --package-lock=false playwright@1.62.1
node "$KALA_BROWSER_TEST_DEPS/node_modules/playwright/cli.js" install chromium
export KALA_BROWSER_EXECUTABLE="$(node -e 'const {createRequire}=require("node:module"); const {resolve}=require("node:path"); const r=createRequire(resolve(process.env.KALA_BROWSER_TEST_DEPS,"package.json")); process.stdout.write(r("playwright").chromium.executablePath());')"
```

Coordinate one Vite server on port 5173 from the checkout under test, with strict port selection (`pnpm --filter web dev -- --host 127.0.0.1 --port 5173 --strictPort`). Do not disturb an existing server. In another terminal with those exported variables run each browser script:

```sh
node apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
node apps/web/src/features/twin/tests/presentation.browser.mjs
node apps/web/src/features/instructor/tests/review-feedback.browser.mjs
node apps/web/src/features/diagnostic/tests/frontend-closeout.browser.mjs
```

These scripts use synthetic intercepted API responses, not live Blackboard/provider acceptance. Keep their generated local outputs private; no request bodies or credentials enter docs. Shut down only the server/fixtures you created when finished. See [backend release](runbooks/deploy-backend.md#contract-generation-before-release-checks) for the isolated OpenAPI export before web checks.

## Documentation checks

```sh
python3 scripts/docs_check.py
python3 -m unittest discover -s scripts -p 'test_docs_check.py'
```

The checker covers published text documentation, record-link placement and portable paths. Ignored local notes and generated caches are not published inputs. Historical paths kept as evidence carry the literal marker `local only, not retained`. No external network/link request is made.

## Historical sources

These links preserve provenance only. Required rules, commands and limits are stated above; do not read the records unless the task explicitly names them.

- [guide extraction](../work/handover-2026/evidence/local-guide-knowledge.md)
