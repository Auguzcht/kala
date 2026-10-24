# AUDIT REPORT — APPROVAL-03 local integration

Date: 2026-10-25 (Asia/Manila). Coordinator on `main` at `/Users/fred/Documents/Repository/kala`.
Authorization: [APPROVAL-03](../approval-03.md), implementing APPROVAL-02 section 5.

## Revision and delivery

Starting main: `65a9cad7396cac7d5da3af8d6655c8e50ddcc382`.
Approved T revision: `b605a3b852c6eb4573ca6ae8460eec9eff486207`.
T merged cleanly after F as `9c2e667cbcf7820d4f55c6837adbcf8201eb9892`.

Verification below ran on that merged local main plus the integration changes to `services/conftest.py` and removal of `services/api/tests/run_study_checks.py`. The only subsequent conftest edit before commit removed an unused Ruff suppression comment; executable content did not change. Approval, work-item and evidence documentation is included in the integration commit. The final main SHA is reported by the coordinator after commit; this file cannot embed its own containing commit SHA.

Nothing was pushed or deployed. Fred deploys the backend first, then pushes. No hosted operations, migrations, key rotation or live Blackboard/model/database smoke tests were performed. Lane DB remains gated on the hosted Postgres major.

## Integration changes

- One shared `services/conftest.py` is automatically loaded for both service suites before test modules import application code. It removes inherited application/AWS/proxy settings by name, supplies fake test-only settings and a generated JWT signing key, clears the hosted secret bootstrap ARN, disables Settings dotenv loading, disables metadata lookup, and blocks IPv4/IPv6 sockets and DNS. Unix socket pairs remain available for in-process asyncio/ASGI tests. Process patches are released at pytest shutdown.
- Existing API UUID constants remain in `services/api/tests/conftest.py`. No existing API or worker test bodies or imports were changed; an AST comparison against `9c2e667` passed for every retained test file.
- Removed the Study-specific launcher. The historical Tutor scratch runner is retained as old evidence only and is not used by the integrated commands.
- Added [WI-20](../work-items/WI-20-frontend-test-runner.md) as planned: adopt a standard frontend runner (for example, Vitest) so component tests no longer need external fixtures. No dependency, lockfile or runtime setting changed in this integration.
- Updated the development test contract, approval router and initiative delivery state. Feature requirements remain those accepted in the lane reports: INGEST-REQ-001, AI-REQ-001, TUTOR-REQ-001 and STUDY-REQ-001–005.

## Initial main verification — superseded for service isolation

All listed commands exited 0. Each service ran in its own process from its own directory. Subsequent fresh-clone verification found that the parent conftest was not discovered by default. These initial API/worker passes therefore do not establish dotenv or network isolation and are not the accepted final service-suite evidence. Frontend, build and configuration results remain applicable because their source is unchanged by the discovery correction.

| Command | Result |
| --- | --- |
| `cd services/api && uv run pytest -q --tb=short` | **431 passed**, 30 existing deprecation warnings, 40.85s |
| `cd services/worker && uv run pytest -q --tb=short` | **117 passed**, 0.47s |
| `node --test apps/web/src/features/tutor/components/TutorChat.test.mjs apps/web/src/lib/api-error.test.ts apps/web/src/features/tutor/schema/tutor.schema.test.ts` | **14 passed**, no failures/skips |
| `KALA_STUDY_TEST_DEPS=/private/tmp/kala-lane-f-renderer node --experimental-vm-modules --test apps/web/src/features/flashcards/tests/study-deck.test.mjs` | **4 passed**, no failures/skips |
| `pnpm --filter web lint` | Pass; 0 errors, 18 existing Fast Refresh warnings |
| `pnpm --filter web typecheck` | Pass; existing route-generator circular-dependency warning |
| `pnpm --filter web build` | Pass; 5,534 modules; Vite phase 6.21s; existing route-generator and large-chunk advisories |
| `python3 -B scripts/config_inventory.py --format json --check` | Pass; 67 names, 21 matching duplicate API/worker fields |
| `python3 -B -m unittest discover -s scripts -p test_config_inventory.py -v` | **11 passed** |
| `services/api/.venv/bin/ruff check services/conftest.py` | Pass after removing an unused E402 suppression; no behavior change |
| `git diff --check` | Pass |

A separate isolation probe forbade all dotenv/credential-file opens before importing the shared conftest. Settings construction passed, the synthetic inherited bootstrap ARN was removed and its synthetic JWT key was replaced by a generated key. TCP and UDP sockets for IPv4 and IPv6, plus DNS, were rejected. An asyncio-compatible Unix socket pair remained available. No signing values were displayed. This probe did not change test bodies or invoke a live service.

## Scope check against e9de105

Migration files: **zero changes**, including both `packages/db/migrations/` and `supabase/migrations/`.
Terraform source (`.tf` and `.tf.json`): **zero changes**.

The literal no-infra/terraform-path condition has **one existing documentation exception**: D's previously approved archive move removes `infra/terraform/lambda.tf.NOTE.md` and preserves it as `docs/archive/engineering/async-ingest-lambda-note.md`. A scoped `git diff --stat e9de105..main -- infra/terraform packages/db/migrations supabase/migrations` shows only that note's 55-line deletion; rename-aware summary identifies the 85%-similar archive move. No Terraform configuration is changed. Rename-aware name-only output can omit the old path, so the coordinator also checked with `--no-renames` and does not claim the literal zero-path condition passed. The approved archive move was preserved.

## Fresh-clone proof and remaining limits

Fresh-clone verification is the final follow-up after the integration commit; its result is appended below when completed. No claim of that check passing is made by this initial entry.

The Study component suite still needs the retained external renderer fixture, Node's experimental VM modules and deprecated react-test-renderer; WI-20 remains planned. Tutor component tests use their existing custom hook/module harness. Automated checks are mocked/in-process and do not establish live LTI, platform latency, database/RLS behavior or tutor recovery. The warm-Lambda abandoned-call and partial sanitizer limits remain explicit in the Tutor/AI specs. Existing lane Ruff findings were not globally refactored.

No deployment, hosted smoke, server, Docker or existing Vite operation was executed. Main's ignored dependency/build outputs were used or refreshed by the requested checks. The initial service runs did not establish dotenv/network isolation; no credential values were printed. Later runs must use verified discovery and blocking. The previously disclosed Lane S exposure remains in the names-only exposure log with rotation at cutover.

## Fresh-clone failure and discovery correction — 2026-10-25

At committed revision cf396410686a96c3cdc1210decc540b6a7f9e2ff, a fresh local clone with no dotenv files or existing virtual environment ran the exact `cd services/api && uv run pytest` command: **409 passed, 22 failed**. Twenty-one mocked LTI tests failed because no generated signing key was present; one existing tight abandoned-thread timing assertion also failed. This result exposed that pytest's service-root discovery cutoff excluded services/conftest.py. The first local-main API/worker results cannot be used as proof of the new isolation. No test body is changed to hide these failures.

The correction adds only `addopts = "--confcutdir=.."` under the pytest section of both service pyproject.toml files, without dependency or lock changes. A trace-config collection check verified that the shared services/conftest.py loads before the API tests' local UUID conftest, with 431 cases collected. Both full service suites and fresh-clone proof are rerun after this correction; passing results are appended below.

## Verified-discovery rerun and test-body gate — 2026-10-25

After the pytest discovery correction, the full API suite on local main returned **430 passed, one failed**, with 30 warnings in 27.71s. The worker suite returned **117 passed** in 0.38s. Trace-config confirms services/conftest.py is loaded in both service runs. The signing failures are resolved. No existing test body or import was edited.

The remaining failure is `tests/test_request_budget.py::test_TUTOR_REQ_001_elapsed_guard_abandons_trickling_sync_operation`, specifically its final `assert finished` after a fixed 100ms cleanup sleep. A focused rerun also fails. An independent three-attempt instrumented probe measured the timeout response at 62.082–62.171ms (below the test's 110ms response bound), the cleanup assertion at 164.184–164.280ms, and worker completion at 172.342–176.535ms. Twelve nominal 10ms sleeps do not guarantee completion by the fixed assertion time on this host. This does not establish a request-deadline violation; the already-documented abandoned worker continues after the response.

A proposed patch is prepared outside the repo: replace the fixed cleanup sleep with polling until completion inside `anyio.fail_after(1)`. It preserves the strict response-time assertion, the assertion that work is unfinished when the deadline returns, and the eventual-completion assertion. The test file is untouched because APPROVAL-03 prohibits test-body edits. The coordinator cannot truthfully declare all checks green until Fred authorizes this test-only correction or provides a different resolution. The initial failing and subsequent probe evidence is retained; tests are not skipped or retried until green.

The initial shared-isolation commit was cf39641. The correction changes only pytest discovery options, a non-value test-report header, and explanatory documentation. No dependencies, lockfiles, application behavior, migrations or Terraform configuration were changed. A committed fresh-clone rerun follows this entry; the original failed attempt is retained separately.
