# Lane G: Diagnostic availability (APPROVAL-06, H02)

Date: 2026-10-25, Asia/Manila. Status: done-awaiting-confirmation for local implementation; coordinator integration and Fred's live acceptance remain outstanding.

Authority: [AGENTS.md](../../../../AGENTS.md), [task router](../../../README.md), APPROVAL-06 rev 2 section 4 supplied directly by Fred, and the coordinator-committed [DIAG-REQ-009–011](../../../features/diagnostic/README.md#diagnostic-availability-lane-g-approval-06). Related work: [WI-22](../work-items/WI-22-diagnostic-tutor-ui.md), WI-08. The coordinator alone edits the Diagnostic spec this round.

Implementation base: `1af50f1db1a9b142deb96bbeca1bdfc295c1eeeb`, after rebasing the initial `cab26de` investigation branch onto the released spec/integration commit. Evidence revision: that base plus the five paths listed in the audit below; the final commit SHA is returned in the lane's chat audit.

## Findings and resulting behavior

The original eligibility query checked only Diagnostic evidence. The status endpoint counted every such skill; question selection limited the first ten before checking availability, required five ready bank MCQs and classified missing material/exhausted pools as failures.

Both endpoints now use the same availability calculation. All learner evidence types and recorded item reviews exclude a skill, scoped by institution, course and learner. Actual Study reviews are read without changing their grading/mastery policy; claims or display alone are not treated as evidence.

Availability is evaluated across the eligible skills before the ten-question sitting cap. Bank selection retains approved/live/bank/practice/untested filters, deterministic oldest-item order and one MCQ per skill. One servable MCQ is sufficient. Query results are paged in ordered 500-row requests; skill-ID filters are batched in groups of 100. The Diagnostic-only picker is changed; Study/Test selection defaults are unchanged.

The response contract is:

- Status returns actionable `dueSkillCount`, `due = dueSkillCount > 0`, and `waitingForMaterialCount`. The counters remain optional for client compatibility.
- Question responses add optional `waitingForMaterialCount`; existing fields and the `ready/generating/failed` enum remain.
- Available questions win (`ready`), then pending preparation/replenishment (`generating`), then actual recorded failure (`failed`). Material-only waiting returns `ready` with an empty sitting and a positive material count; an empty/all-evidenced course returns zero.
- No-material skills enter neither pending nor failed lists. Exhaustion awaits replenishment. A recorded legacy `NoCourseContentError` is material waiting, rather than a generic generation failure.
- Status performs SELECTs only. Question loading retains the existing bank kick/legacy enqueue boundaries. A bank request kicks at most once. Legacy enqueue remains capped at ten new requests; already-recorded terminal jobs do not consume that allowance and block later unqueued skills. A post-enqueue item reread preserves the existing worker-completion race handling.
- Submission, grades, evidence writes, mastery calculations and migrations are unchanged. No evidence is written to dismiss a notice.

## Verification ledger

All automated records are synthetic. The shared pytest isolation disables dotenv loading and network access.

| Revision/environment | Command or method | Result |
| --- | --- | --- |
| Original `cab26de` investigation, local | `cd services/api && uv run pytest tests/test_diagnostic_idempotency.py tests/test_diagnostic_mastery_delta.py tests/test_bank_serving.py tests/test_async_item_generation_routes.py -q` | 19 passed; two existing dependency warnings |
| Initial implementation, local | Focused suite including the new Lane G tests | 43 passed, two failed: existing assertions expected partial readiness to remain generating and omitted the additive zero material counter |
| Initial implementation, local | `cd services/api && uv run pytest -q` | 572 passed, the same two contract-expectation failures; no other failure |
| Updated contract assertions, local | Full API suite | 574 passed; 30 dependency/deprecation warnings |
| Additional edge-case coverage, local | Full API suite | 578 passed; 30 dependency/deprecation warnings |
| Final five-path working tree, local | `cd services/api && uv run pytest -q` | **579 passed**, 30 dependency/deprecation warnings, 27.79 seconds; includes 31 Lane G cases |
| Final working tree, local | `cd services/api && uv run ruff check --ignore B008 app/routers/diagnostic.py app/bank/serving.py tests/test_lane_g_diagnostic_availability.py tests/test_diagnostic_idempotency.py` | Passed |
| Base and working tree, local | Ruff JSON comparison with `--select B008` | 23 findings on each revision, all the existing FastAPI dependency-default pattern; no increase |
| Final working tree, local | `git diff --check` | Passed |
| Final query projections, local Supabase Postgres + PostgREST | Disposable `/tmp/kala-g-local-availability.py` validation | **21 actual REST queries passed**; bank count 13, material count 12, sitting 10, proper pending/failure buckets, prior Study/Practice excluded; legacy projection/filter/order queries also executed successfully | (local only, not retained)

The new tests cover mixed no-material/ready/preparing/exhausted/failed skills, each evidence type, item-review-only history, one-MCQ readiness, more than ten actionable skills, deterministic refetch, empty/completed courses, a real submit followed by cleared eligibility, HTTP workspace/page parity, tenant/course/learner/module boundaries, retired/rejected/non-bank/non-MCQ exclusions, SELECT-only status for both serving modes, legacy saved items, recorded material failures, queue starvation and worker completion during enqueue. Separate cases place evidence, reviews, exposures, bank items and skills beyond the 500-row page boundary.

Only two existing test assertions changed, both in `test_diagnostic_idempotency.py`, to match DIAG-REQ-011. No deadline, grading or isolation test was weakened.

## Real local query validation and limits

Created two isolated disposable containers: `kala-diagnostic-lane-g-pg` using cached `public.ecr.aws/supabase/postgres:17.6.1.158`, and `kala-diagnostic-lane-g-rest` using cached `public.ecr.aws/supabase/postgrest:v14.15`. Existing migration files `0001` through `0036` were executed without editing them. The bare Postgres image required local auth/storage prerequisite bootstrap; initial bootstrap attempts failed on missing auth helpers, auth-schema permissions and missing Storage tables before those prerequisites were supplied. This was a query-validation fixture, not a clean migration-replay acceptance for Lane DB.

The local REST service used only synthetic institution/course/learner IDs and records. Its port was bound to loopback; Postgres had no published host port. The test asserted the actual endpoint helper results and executed the new bank and legacy projections, filters and ordering through PostgREST against the replayed schema. No hosted configuration, hosted data, credentials, model calls or student records were used. The image's local PostgreSQL 17 version does not establish the hosted major and does not satisfy FG-2.

Both containers were removed after validation. The disposable script is outside the repository and is not a durable test dependency; committed offline tests provide repeatable behavior coverage. This local check does not prove live latency, RLS under a real LMS session, concurrent-worker behavior or deployed frontend rendering. FG-5 remains Fred's gate.

Ordered paging follows the [Supabase range documentation](https://supabase.com/docs/reference/python/range). No new SQL, RPC, migration or database configuration is shipped.

## Integration notes and remaining risk

The coordinator retains ownership of `services/api/openapi.json`, generated frontend types and the Diagnostic feature spec. None is changed here. The existing Diagnostic endpoints have no response model describing these fields, so additive body fields are not automatically described by the existing OpenAPI response schema. Lane U owns optional Zod parsing, the workspace notice and question-page waiting presentation.

Read batching removes the old per-skill bank-state/picker round trips, but every request still scans the eligible bank pools and relevant learner histories. Cost grows with the remaining skill bank and history size; prompts/choices for candidate items are read before one item per skill is selected. There is no new whole-request deadline, cache or database aggregate. A large bank/history may still pressure the API request budget. Ordered offset paging also is not a transactional snapshot across concurrent writes; parity is asserted for unchanged source data, as specified. Configured REST page caps below the requested 500-row page size are not verified by these tests. No global database/timeout optimization or infrastructure change is included.

## AUDIT REPORT

```text
Task / brief ID: APPROVAL-06 rev 2, Lane G; H02 Diagnostic availability
Branch and worktree: codex/diagnostic-availability;
  .
Base revision: 1af50f1db1a9b142deb96bbeca1bdfc295c1eeeb
Files changed:
  services/api/app/routers/diagnostic.py
  services/api/app/bank/serving.py
  services/api/tests/test_lane_g_diagnostic_availability.py
  services/api/tests/test_diagnostic_idempotency.py
  docs/work/handover-2026/evidence/diagnostic-availability-lane-g.md
REQ / WI IDs touched: DIAG-REQ-009–011; WI-22 / WI-08
Commands run and results (tests, lint, typecheck, build):
  Final full API pytest: 579 passed, 30 existing warnings.
  Changed-path Ruff with existing B008 excluded: passed.
  Baseline/working B008: 23/23 findings, unchanged.
  git diff --check: passed.
  Real local PostgREST/Postgres: 21 query checks passed; containers removed.
  Web/worker checks not rerun: no frontend/worker path changed;
  combined integration checks belong to coordinator.
Spec changes made: none; implementation follows coordinator's 1af50f1 spec.
Evidence added: this report and 31 uniquely named Lane G test cases.
  The coordinator explicitly granted this unique evidence path on 2026-10-25
  under the standing disjoint-ownership rule, to preserve the audit durably.
Anything not done, and why: no merge, push, deploy, hosted write, migration,
  key rotation, identity repair, generated-file edit or live acceptance;
  coordinator integration and Fred's gates remain authoritative.
Risks or questions for the planner: per-request full eligible-pool/history
  scans, concurrent-write snapshot limits and unverified lower REST row caps
  described above; update spec status/evidence links after integration.
Secrets printed: none (confirmed)
```
