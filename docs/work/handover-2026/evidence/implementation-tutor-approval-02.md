<!-- Historical lane submission, preserved verbatim below. Delivery state is tracked in approval-02-coordinator.md. Local scratch paths are historical evidence locations, not fresh-clone dependencies. -->

# AUDIT REPORT — Lane T complete; stopped before merge

Task: APPROVAL-01, Lane T including A1, and APPROVAL-02 verification refresh; AI-REQ-001 and TUTOR-REQ-001.
Branch: `codex/tutor-boundary`
Worktree: `/Users/fred/.codex/worktrees/8491/kala`
Base: `e9de105d7f3074ec39f54e32b1f2b5e2bda669ed` (`origin/main` at dispatch).
Final local commit: `b605a3b852c6eb4573ca6ae8460eec9eff486207`.
Prior completed UI/implementation commit: `4b0436d4462a4b43dd93707c7b96cc8703ab3434`.
Prior scoped backend/contract commit: `98e542a25d5225c8e1c067c19fec9c872be3baa9`.
Disposition: approved Lane T implementation complete, verified and committed locally; awaiting Fred's explicit approval of this refreshed AUDIT REPORT before any merge. APPROVAL-02 requested this final spec-only change and full API plus web rerun; it did not authorize merging. TUTOR-REQ-001 is implemented. AI-REQ-001 remains partial by approval because sanitizer coverage is intentionally limited.
No push, merge, rebase, deployment, hosted migration, or hosted API/model/LMS/database call.

## Changed files
```
apps/web/src/features/tutor/components/TutorChat.test.mjs
apps/web/src/features/tutor/components/TutorChat.tsx
apps/web/src/features/tutor/schema/tutor.schema.test.ts
apps/web/src/features/tutor/schema/tutor.schema.ts
apps/web/src/lib/api-error.test.ts
apps/web/src/lib/api-error.ts
docs/features/ai-platform/README.md
docs/features/tutor/README.md
services/api/app/ai/bedrock.py
services/api/app/ai/deidentify.py
services/api/app/ai/rag.py
services/api/app/ai/request_budget.py
services/api/app/ai/router.py
services/api/app/db/supabase.py
services/api/app/main.py
services/api/app/routers/tutor.py
services/api/tests/test_request_budget.py
services/api/tests/test_tutor.py
```

## Implemented behavior and evidence
- One 26s monotonic budget begins at `/tutor/ask` handler entry. Each synchronous outbound stage runs off the async event loop with AnyIO `fail_after` and `abandon_on_cancel=True`. Waiting for worker capacity is included. Operations get `min(current timeout, remaining minus 3s reserve)`. HTTPX inactivity timeout values are NOT treated as wall-clock bounds.
- Opt-in budget parameters propagate through tutor ownership/history/attachments, RAG embedding/RPC, chat/fallback, and both persistence writes. Default calls omit the new keywords and retain payloads, roles, fallback behavior, and 60s DB / 25s OpenRouter / 20s OpenAI timeouts.
- Tutor Bedrock clients clamp connect/read settings and disable SDK retries for this opt-in call only. Default boto3 construction remains identical; global timeout/retry policy remains deferred.
- Fallback is skipped below 6s remaining, and backoff is skipped if it would cross that threshold. The elapsed guard also bounds an attempted fallback. Per-request role/fallback metadata is recorded.
- Deadline exhaustion before an answer maps to HTTP 503 `{detail: "The tutor took too long to respond. Please try again.", code: "tutor_timeout"}`.
- Persistence failure, no remaining persistence budget, or a slow persistence write returns the answer with HTTP 200 and a privacy-safe stage/conversation-prefix warning. A late message insert cannot start the subsequent conversation update.
- Exactly one `tutor_timing` line per handler records stage milliseconds, handler time, mode, provider role, fallback use, outcome, and user ID prefix. Provider role is `none` until chat starts; primary uses `chat`, fallback uses `chat_fallback`. New provider/persistence logs omit raw exception strings and provider response bodies.
- Tutor embedding query, prior history, system text, current question, RAG context, filenames and attachment text use sanitized model-bound copies. Stored question/title/message content remains original. Sanitizer regex patterns are unchanged.
- `apiErrorReason` parses JSON structurally, accepting both flat detail and detail plus code; non-JSON uses caller fallback. Tutor error schema uses `code: z.string().nullish()`.
- TutorChat displays the parsed error detail inline and in its toast, with a safe fallback for non-JSON bodies. When the conversation refetch fails or lacks the returned turn, its question/answer stays in local UI state with a save-uncertainty note. It sends no automatic new ask/save request. A later refetch confirming both new message IDs removes the duplicate local display. Message matching tolerates equal timestamps/changed relative row order and rejects historical identical pairs. Normal saved-response handoff remains unchanged.

## Specs
Created minimal `docs/features/tutor/README.md` and `docs/features/ai-platform/README.md` from the supplied feature-spec template BEFORE implementation. Both cite APPROVAL-01 dated 2026-10-24. Only TUTOR-REQ-001 and AI-REQ-001 are specified.
AI-REQ-001 remains `partial`: emails and explicit `name:` / `姓名:` patterns only; arbitrary names and other personal information are not removed. Non-tutor behavior remains unchanged.
TUTOR-REQ-001 is `implemented`; its spec includes the granted UI behavior, UI regression paths, ephemeral-copy limitations, and change-log entries citing APPROVAL-01, the coordinating planner grant, and APPROVAL-02. The APPROVAL-02 commit changes only `docs/features/tutor/README.md`, explicitly recording that on Lambda an abandoned synchronous call can resume when the warm execution environment serves the next request. Returning the response does not terminate that call or guarantee cancellation of its remote side effects.

## Exact verification commands and results
Full API, frontend regressions, web lint, web typecheck, and web build were rerun under APPROVAL-02 after the spec update. Fresh logs and JUnit evidence are under `approval-02/`. All commands below ran from the worktree root unless otherwise stated. Dependency installation and Python Ruff results are carried forward from the prior implementation round; no dependency, Python code, or shared test harness was changed in this round.
- `uv sync --locked --project services/api` — PASS; created a local .venv using uv.lock; no manifest or lockfile edit.
- `pnpm install --frozen-lockfile` — PASS; local node_modules, no manifest or lockfile edit.
- `env -i PATH=/opt/homebrew/bin:/usr/bin:/bin SUPABASE_JWT_SECRET=isolated-fake-test-secret-never-used-live /Users/fred/.codex/worktrees/8491/kala/services/api/.venv/bin/python /Users/fred/.codex/visualizations/2026/10/24/01a16e82-b88c-7ee1-b65d-bebfc6f5e8c6/kala-tutor-boundary/run_api_tests.py -q --junitxml=/Users/fred/.codex/visualizations/2026/10/24/01a16e82-b88c-7ee1-b65d-bebfc6f5e8c6/kala-tutor-boundary/approval-02/api-tests.xml` — PASS, 400 tests, 31 deprecation/record_property warnings, 27.440s. Includes real 26s request-budget test: HTTP 503 returned in **23.003187624999555s**. Fresh log and JUnit XML: `approval-02/api-tests.log` and `approval-02/api-tests.xml`.
- `node --test apps/web/src/features/tutor/components/TutorChat.test.mjs apps/web/src/lib/api-error.test.ts apps/web/src/features/tutor/schema/tutor.schema.test.ts` — PASS, 14 tests. Covers flat detail, detail/code, non-JSON, JSON escapes/key order, optional/null code, timeout detail inline/toast, normal saved response, failed/missing refetch, late-save deduplication, historical identical pairs, timestamp ties, local-answer retention and conversation isolation. Fresh log: `approval-02/web-tests.log`.
- `pnpm --filter web lint` — PASS, 0 errors / 18 pre-existing react-refresh warnings. Fresh log: `approval-02/web-lint.log`.
- `pnpm --filter web typecheck` — PASS; router CLI circular-dependency warning. Fresh log: `approval-02/web-typecheck.log`. Prior implementation-round follow-up checks `pnpm --filter web exec eslint src/features/tutor/components/TutorChat.tsx` and `pnpm --filter web exec tsc -b` also PASS after timestamp-tie handling.
- `pnpm --filter web build` — PASS; existing large-chunk and router CLI circular-dependency warnings. APPROVAL-02 build completed in 6.30s; `approval-02/web-build.log` saved. Build did not start a server. Environment-file existence checks confirmed no `.env` or `.env.local` at root, web, or API locations.
- `services/api/.venv/bin/ruff check --select I,F services/api/app/ai/request_budget.py services/api/app/ai/bedrock.py services/api/app/ai/deidentify.py services/api/app/ai/rag.py services/api/app/ai/router.py services/api/app/db/supabase.py services/api/app/main.py services/api/app/routers/tutor.py services/api/tests/test_tutor.py services/api/tests/test_request_budget.py` — PASS.
- Full configured Ruff across those same files reports 11 pre-existing B008/BLE001 diagnostics. Compared current diagnostic code/message counters to `git show e9de105:<path>` through Ruff stdin: **no added diagnostics**. Existing DB and non-ask tutor routes were not refactored.
- `git diff --check` and `git diff --cached --check` — PASS before commit.
- `git status --short` after commit — empty; worktree clean.

Test isolation: saved `run_api_tests.py` clears inherited environment via env -i, switches to an empty temporary working directory, disables Settings env_file before collection/importing app.main, and blocks AF_INET/AF_INET6 socket connections. All providers/LMS/DB calls are mocked. The existing external runner and isolation were reused unchanged for APPROVAL-02. Shared conftest/harness integration remains coordinator-owned after S/F/T integration; no shared harness was edited. No `.env`, `.env.local`, or secret.json read. Initial focused run had 3 fixture errors (missing ModelUnavailableError.model_id); fixtures corrected and full suite passed. First UI test run had 2 harness failures from an omitted Button stub; stub corrected before all 14 tests passed. One invocation of the temporary runner initially discovered no tests; fixed argument selection before full-suite runs.

## Extra-path grants used
1. Initial dispatch pre-granted `services/api/app/ai/request_budget.py` and dedicated `services/api/tests/test_request_budget.py`: needed for an elapsed waiting guard independent of HTTPX phase/inactivity settings and shared opt-in deadline calculation.
2. Follow-up coordinating planner grant under APPROVAL-01 standing rule permitted `apps/web/src/features/tutor/components/TutorChat.tsx` and dedicated tutor UI regression files. Rationale: complete timeout detail display and preserve an answer when persistence refetch lacks it or fails, conditional on tutor responses/errors. Used only that component and `apps/web/src/features/tutor/components/TutorChat.test.mjs`. No redesign or non-tutor caller change. Grant recorded in the tutor spec change log.
No other extra path was edited. No remaining ownership grant is needed.

## Limits and risks
- On Lambda, an abandoned synchronous call can resume when the warm execution environment serves the next request. This APPROVAL-02 known limit is now explicit in TUTOR-REQ-001. Returning a response does not terminate the call or guarantee cancellation of its remote side effects.
- The handler stops waiting within the request budget; synchronous HTTPX/Boto operations are not forcibly killed. Threads and an in-flight remote request can continue afterward. Clients close when their workers exit; subsequent tutor stages check the closed/expired budget. Repeated slow calls can occupy worker resources beyond the response deadline.
- An in-flight persistence write may commit after the handler returns. Message insertion and conversation metadata update are not transactional; success after a metadata failure can be partial. No migration or persistence schema change is proposed here.
- The 26s budget starts at handler entry, excluding authentication and cold initialization. It is an application waiting deadline, subject to event-loop scheduling; no live Lambda/platform latency guarantee or recovery claim.
- Sanitization remains partial by explicit approval. Other model callers retain their current behavior.
- Unconfirmed answers are ephemeral UI state: refresh/navigation can lose an unsaved copy; the interface labels save uncertainty and does not automatically retry persistence. A slow conversation refetch can still delay the existing handoff. The UI regression harness executes the actual component callbacks and React JSX/server rendering with isolated hooks/query/router/visual shells; it is not a real-browser/TanStack integration smoke test. Fred retains that click-through after integration.
- Fred still owns live stateless/persistent tutor smoke and Blackboard testing after integration. No hosted verification was performed or claimed.

## Sources consulted
- Accepted BRIEF-01 audit report and supplied feature-spec template; root CLAUDE.md read. No AGENTS.md or scoped CLAUDE.md existed in this base checkout. `apps/web/src/styles/DESIGN.md` read before the granted UI edit.
- Supabase skill: `/Users/fred/.agents/skills/supabase/SKILL.md`. Changelog fetched via curl after web markdown fetch failed; no relevant Data API/HTTP client breaking change found. No schema/auth/RLS capability changed.
- [HTTPX timeout semantics](https://www.python-httpx.org/advanced/timeouts/)
- [AnyIO worker cancellation](https://anyio.readthedocs.io/en/stable/threads.html)
- [Botocore Config](https://docs.aws.amazon.com/botocore/latest/reference/config.html)
- [Supabase Data REST API](https://supabase.com/docs/guides/api)

## Final state
Clean tracked/untracked git status at the final local commit. Work stayed in the assigned worktree/branch. Main checkout, other audit worktrees, and localhost:5173 untouched. No server, container, or temporary port created. Test workers were released/completion-observed in tests; no running test/build/install command remains. Only local ignored dependencies/build outputs and scratch evidence remain. No push, merge, deployment, key rotation, hosted migration, or production write. Fred must explicitly approve this refreshed report before any merge.

Secrets printed: none.
