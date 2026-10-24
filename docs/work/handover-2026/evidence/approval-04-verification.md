# AUDIT REPORT — APPROVAL-04 repeated verification

Date: 2026-10-25 (Asia/Manila).
Task / brief ID: [APPROVAL-04](../approval-04.md), resolving the recorded APPROVAL-03 test-body gate.
Branch/worktree: `main`, `/Users/fred/Documents/Repository/kala`.
Base revision: `c41fbe0d0563753751ba6c99850dee34b9008b01`.
Tested revision: `a5002366e0d364e29797855a0c035f2b0f4bd181`.
Disposition: all requested checks passed; stop without pushing or deploying.

## Change and scope

Applied exactly the approved patch to `services/api/tests/test_request_budget.py`: the fixed 100ms cleanup sleep is replaced with polling inside `anyio.fail_after(1)`. This bounds waiting for the already-abandoned worker to finish and does not extend the request budget.

All assertions are preserved byte for byte / AST-equivalent, including:

- Response returns within the existing 110ms test bound.
- Worker is unfinished when the deadline returns.
- Remaining budget is zero.
- Worker eventually completes.

The test file equals its base text with only that approved replacement. Every other test body and import is unchanged. No production code, shared conftest implementation, dependency, lockfile, migration or infrastructure file changed in this approval. The only additional edits are approval, routing, initiative and evidence documentation.

REQ / WI IDs: TUTOR-REQ-001 verification only; no intended feature behavior changed and no new requirement was created. WI-20 remains planned and no frontend runner/dependencies were added. Spec changes: none; the existing deadline behavior and known limits remain authoritative.

## After-the-fact discovery acceptance

APPROVAL-04 section 2 explicitly accepts `addopts = "--confcutdir=.."` in both `services/api/pyproject.toml` and `services/worker/pyproject.toml`. These options were introduced in ef487ed and are unchanged by this approval. The shared parent conftest loads before collection, disables dotenv, sets fake test-only configuration including a generated JWT signing key, and blocks IPv4/IPv6 sockets and DNS. Full-suite logs confirm the isolation header. This acceptance is also appended to [the integration evidence](approval-03-integration.md); prior failed attempts remain historical evidence.

## Exact requested verification

All runs below executed once in the requested order/count; none failed, were skipped or were retried to obtain a pass.

| Check | Command | Result |
| --- | --- | --- |
| Focused shell loop on main | `for kala_run in {1..20}; do uv run pytest tests/test_request_budget.py::test_TUTOR_REQ_001_elapsed_guard_abandons_trickling_sync_operation -q --tb=short; done` from services/api, with individual exit-code/log capture | **20/20 passed**, zero failures |
| Full API on main, run 1 | `cd services/api && uv run pytest` | **431 passed**, 30 existing warnings, 27.54s |
| Full API on main, run 2 | `cd services/api && uv run pytest` | **431 passed**, 30 existing warnings, 27.59s |
| Full API in a fresh clone | `cd services/api && uv run pytest` | **431 passed**, 30 existing warnings, 28.39s |
| Full worker suite on main | `cd services/worker && uv run pytest` | **117 passed**, 0.36s |

The shell loop retained all twenty individual logs and a 20-row exit-code CSV; all twenty outputs contain one passing case. The two full main API runs ran sequentially after the focused loop. The independent worker run followed the focused loop. The fresh clone ran after both main API runs.

Fresh-clone method: local `git clone --quiet --no-local --no-hardlinks` of the tested revision into a temporary directory; verify clean status, zero non-example dotenv files and no existing API virtual environment; run the exact API command with a minimal ordinary process environment. uv installed 47 locked packages. The shared-isolation header appeared; clone Git status remained clean and the temporary clone was removed. No lane-specific or scratch test runner was used.

Supplemental checks: Ruff on the edited test file passed; exact-patch/all-assertions/other-tests scope checks and whitespace checks passed. Frontend, build and inventory sources are unchanged; their APPROVAL-03 results remain historical evidence and were not unnecessarily rerun for this test-only amendment.

## Evidence and delivery

All raw logs and value-free result records are retained at:
`/Users/fred/.codex/visualizations/2026/10/24/01a16e30-fcb8-7b50-91d8-4f38c908acd5/kala-approval04-integration/`.

Files: `focused-1.log` through `focused-20.log`, `focused-results.csv`, `main-api-1.log`, `main-api-2.log`, `main-api-results.json`, `fresh-clone-api.log`, `fresh-clone-result.json`, `worker.log` and `worker-result.json`.

The completion commit changes documentation only, preserving the tested revision's code, tests, configuration and locks. The final local main SHA is reported by the coordinator after that commit. The earlier integration failures are superseded by these passing results, not removed from history.

Push: not performed. Deployment: not performed. Fred deploys the backend first, then pushes. Live Blackboard/LTI/CloudWatch observation and hosted behavior remain unverified by these mocked/in-process suites. The existing partial sanitizer and warm-Lambda abandoned-call limits remain unchanged. Lane DB stays gated on the hosted Postgres major.

Resources: temporary fresh clone removed; all test commands exited; no server, Docker resource or hosted data operation was started. Existing development sessions and other worktrees were preserved. Ignored test dependencies/caches remain local. Secrets printed by this approval round: none; no credential values are included in evidence.
