# WI-25: complete evidence history

Date: 2026-10-25. Environment: local synthetic only. Branch: `codex/wi25-evidence-history`.
Base: `9c24a85b4bd21ca9995073dd078e2b3f66ea8325` plus the working-tree paths recorded below. Requirements: TWIN-REQ-010 / INSTR-REQ-010, coordinator-owned specs committed before implementation. Authority: APPROVAL-07 section 2 and Amendments 1–3.

## Query and cursor verification

`cd services/api && uv run pytest tests/test_evidence_history.py -q`: **24 passed**. Uses committed `services/conftest.py`; dotenv disabled, inherited application settings replaced and IPv4/IPv6/DNS blocked. No hosted calls or credentials.

Scenarios: first/next/final/empty/exact-limit pages; equal timestamp ID ties; limit bounds; malformed/noncanonical/tampered/wrong-version cursors; timestamp/UUID validation; caller/target/course/institution binding; secret rotation; concurrent newer arrival; valid cutoff after anchor removal/re-attribution; scoped approved skill names. These query tests do not assert route admission.

The new helper reads only evidence and approved skill names, explicitly filtering tenant/user/course and ordering `(created_at DESC, id DESC)`. Existing bounded responses are untouched. Cursor HMAC is domain-separated from the existing JWT secret; no new setting, TTL, anchor query, evidence/XP write or model call is added.

## Local database proof

Dedicated container: `kala-wi25-history-pg`, network disabled, no host port mapping. Image: `public.ecr.aws/supabase/postgres:17.6.1.158`; PostgreSQL reports 17.6. This container was created for H and no other lane's database was reset/reused.

Historical 0001–0037 replay completed byte-for-byte. The database image lacks the service-managed auth/storage bootstrap: initial replay stopped at missing `auth.jwt()`, then at `storage.buckets`. Minimal synthetic `auth.jwt()`, storage buckets/objects and foldername shims were installed only in this throwaway database. Replay resumed at the failed files; no migration source was changed. This is a database replay with bootstrap shims, not a full running Supabase service stack.

0039 applied twice successfully. The runbook's actual pre-check and guarded apply/post-check SQL ran successfully. A transactionally created conflicting index was rejected with the expected mismatch; connection abort rolled the probe back. The correct index definition survived.

`services/api/tests/fixtures/evidence_history_local.sql` passed on the replay. Its 61 synthetic events include timestamp ties. The PostgREST-equivalent OR predicate matches native tuple ordering with 26-row lookahead. `EXPLAIN` selects `evidence_events_history_idx` for user/course ordering, with institution as an explicit row filter; no leading institution column is needed. `enable_seqscan=off` demonstrates index eligibility only, not measured production latency. All fixture rows rolled back.

All **37** historical migration files compare byte-identically with the base. Only new 0039 is added by H. Hosted FG-6 is pending Fred.

## Frontend verification

Frozen-lockfile install completed without changing dependency manifests/lockfile. Web lint passes with 18 pre-existing Fast Refresh warnings; typecheck and production build pass. Build retains existing large-chunk warnings.

The independent history hook scopes cached pages by institution/caller/target/course and stores cursor identity in TanStack pageParams. It does not retain previous-scope data. Loaded pages deduplicate by ID in server order. Shared ledger ten-row pages and reduced-motion behavior remain intact. The new wrapper keeps bounded fallback labels until history succeeds, labels loaded counts, retries failures while retaining rows, and resets the whole cursor chain on Reload activity. Readiness charts/statistics keep their original bounded arrays.

Dedicated `evidence-history.browser.mjs` is written for student Twin and instructor record, at 375/1440 and reduced/normal motion: older loading through the earliest event, keyboard activation, 40px controls, failure/retry, invalid-cursor reload, final-page behavior, overflow, and no mutations. **Execution pending coordinator handover of port 5173.** Retained UI/tour fixtures were not edited.

## Remaining integration

New own/staff routes, authorization integration tests and generated OpenAPI/types are pending SEC merge and explicit router-phase release. H has not edited twin/dashboard routers or generated files. Coordinator owns generation after integration. Full API suite on this pre-route working tree: `cd services/api && uv run pytest -q` — **634 passed**, 30 dependency deprecation warnings, 28.66s. This does not verify the pending routes.

Retained fixture proposal: add a synthetic `/evidence` handler only where those suites intend active full history, and change their `Last 20/25 events` assertions to the loaded-activity wording with the synthetic feed's count. Fixtures that intentionally omit/fail history may retain legacy expectations. H does not change retained fixtures without coordinator direction.

No hosted read/write, deployment, push, migration application, real-user fixture or 5173 server action occurred.

## Amendment 2: existing staff 404 presentation audit

Static source findings at H commit `02e5b90`; these are not browser observations. API 404 denial semantics remain unchanged. The shared client throws `Error` with prefix `API 404:`; feature-local recognition needs no shared-client change.

| Source | Observed failure presentation | Scope/disposition |
| --- | --- | --- |
| `apps/web/src/features/instructor/components/RosterTable.tsx:96,103,152,209` | Reads only data/loading, defaults missing students to an empty array and count zero; failure can show “No students enrolled yet” | Outside H manifest; recorded for coordinator/U |
| `apps/web/src/features/instructor/components/AtRiskList.tsx:50,63` | Reads only data/loading and defaults missing flags to an empty array; failure can show reassuring no-support-needed copy | Outside H manifest; recorded for coordinator/U |
| `apps/web/src/features/instructor/components/CohortStats.tsx:71,73` | Missing data always returns skeletons, including after a failed request | Outside H manifest; recorded for coordinator/U |
| `apps/web/src/features/instructor/components/LearnerRecord.tsx:67–77` | Error branch prevents a missing-data crash, but 404 gets connection/retry wording | H caller; exact unavailable-copy/navigation proposal submitted, awaiting coordinator spec release |
| `apps/web/src/features/instructor/components/StudentDrillDown.tsx:23–29` | Same generic error/retry behavior on 404 | H caller; same pending proposal |
| `apps/web/src/features/instructor/components/Heatmap.tsx:27–31` | Error branch prevents a missing-data crash, but 404 gets connection/retry wording | Outside H manifest; recorded for coordinator/U |

Proposed INSTR-REQ-009 clarification: learner record and Twin drill-down render HTTP 404 as “Learner unavailable”, with “This learner or course is unavailable. Return to your class to choose an available learner.” Provide a “Back to class” action to `/class`; preserve generic retry for other failures. Do not disclose whether the requested resource exists. Dedicated synthetic 404 checks must assert truthful copy and zero mutating requests. This proposal is not implemented or an amendment to the coordinator-owned spec.

## Amendment 6 implementation update

Coordinator released INSTR-REQ-011 and the validated-role history amendment in `0a2be1250dabd216bdaa28c0b3d6b5e0c23e7037`; H rebased before editing. This update supersedes the pending-UI-proposal disposition in the earlier static audit, while retaining its findings as historical evidence.

H's granted path manifest now also includes `RosterTable.tsx`, `AtRiskList.tsx`, `CohortStats.tsx`, `CohortCharts.tsx`, `Heatmap.tsx`, feature-local `InstructorReadFailure.tsx` and dedicated `read-states.browser.mjs`, alongside the already-owned learner record/drill-down callers. No class routes, shared client/primitives, API semantics or specs were edited.

Roster, at-risk, stats/charts and heatmap now check settled errors before rendering empty or numerical data, including a failed refetch after cached success. Skeletons apply only while loading. Feature-local status-prefix classification renders class 403/404 as unavailable, and other failures as retryable load failure. Learner record/drill-down use Learner unavailable plus Back to class for 403/404 and a transient Retry state for other failures. Error bodies are never displayed. Successful empty responses retain their existing presentation.

History cache identity now includes validated session role. A staff target enables only for instructor/admin; own history enables only for student. Disabled scopes and 403/404 hide protected rows and loaded-count labels. Transient failures retain loaded rows, and invalid cursor uses Reload activity as before.

Validation after these changes: web lint passes (18 existing warnings), typecheck passes, production build passes (existing warnings), new browser scripts pass Node syntax checks, and diff whitespace checks pass. Browser execution is still pending coordinator handover of port 5173; the suites are ready. The dedicated new matrix covers 375/1440, class and learner 403/404/500/network/slow/empty responses, Retry recovery, cached-success refetch failure, heatmap denial and no mutations. The history scope suite covers role/account/course/learner changes, staff-only enablement, page reset and cached-row hiding on 403/404. These are written scenarios, not passing browser evidence yet.

Coordinator follow-up `872c464f6f7bde08eb089794e8c1db27c46b0da6` was incorporated by clean rebase. Its updated TWIN-REQ-010 preserves rows on transient own-history errors only; staff history hides rows and loaded-count labels on any failed history request, with retry/reload controls. Both modes hide loaded/fallback rows after 403/404. Browser expectations distinguish these cases. Router files remain byte-identical to the integration base.

## Legacy bounded cache limitation (coordinator follow-up)

Static review after Amendment 6 confirms `apps/web/src/features/instructor/hooks/use-instructor.ts` keys heatmap at line 27, at-risk at 34, student Twin at 41, roster at 104, cohort stats at 112 and learner record at 120 by course and, where applicable, target only. They omit caller, institution and role. `apps/web/src/lib/auth/AuthProvider.tsx:18–20,28–31` replaces session state without clearing QueryClient; `apps/web/src/app/providers.tsx:8–10,20–21` retains the shared in-memory client with 30-second stale time. An in-place session replacement can therefore reuse old bounded staff data until a new request settles. A fresh document load reconstructs that in-memory client; that normal launch behavior is not evidence that in-place replacement is isolated.

H's new history key explicitly includes caller/institution/role/target/course and cursor page identity; its scope suite is written to verify that independent feed only. This does **not** fix or verify actor isolation in the legacy bounded Twin/record fallback arrays or every instructor query. Hook-wide cache changes and shared session/client invalidation remain outside the current component-only Amendment 6 grant. No such files were edited. The new component error branches hide cached data once their request fails; they cannot force an unscoped cached query to reauthorize on session replacement.

The final follow-up production build completed successfully with the existing large-chunk warning. Browser execution and router-phase gates remain pending; no server action was taken.

## LearnerTriage scope clarification

Coordinator clarified that the roster sheet's `LearnerTriage.tsx` is included in Amendment 6's learner-record callers. It now reuses the same feature-local unavailable/transient failure primitive as the full record; decision rendering and mutation semantics are untouched. This supersedes the earlier report's statement that Triage remained unchanged.

The dedicated instructor read-state suite now includes the actual roster → keyboard-open LearnerSheet → LearnerTriage path with synthetic 403 and 404 at 375/1440. Written assertions cover unavailable copy, class link, no stuck loading, no mutation/crash and Escape returning to the roster. Browser execution remains pending server handover, not claimed passed. No LearnerSheet, route, hook-wide cache or shared-client change was required.

## Pre-browser fixture review corrections

Before browser execution, coordinator review found the copied synthetic API client lacked the production error prefix's colon. Both the read-state and older-history suites now throw `API <status>: synthetic failure`; production parsing is unchanged. The read-state learner fixture now returns a genuinely successful zero-attempt, zero-evidence, empty-skill record with absent readiness/activity, rather than the inherited populated example. Its Activity-tab assertions require a loaded count of zero and the empty ledger state.

Class failure cases now wait for and independently check roster, at-risk, charts and the statistics strip, including an exact four-panel error count. These corrections improve written coverage; they remain unexecuted until server handover. Node syntax and whitespace checks pass. No product behavior changed in this correction.

## Released router phase and integrated verification

Coordinator released the router phase after SEC merged. H rebased cleanly onto integrated local main `afe0c1cb0f35b86a4fddad4d61f83a9ea1067038` before touching routers. The earlier pending-route statements above are superseded by this section.

Added only these endpoints:

- `GET /courses/{course_id}/twin/evidence`: validated student role, token-institution course resolution, scoped own student enrollment, then history query. A query-string user ID cannot override the authenticated identity.
- `GET /dashboard/{course_id}/students/{user_id}/evidence`: validated instructor/admin role, existing `_assert_teaches_course`, existing `_course_ref`, existing `_assert_teaches_student`, then history query, in that order.

Both declare the dedicated Pydantic page response and query limit bounds 1–100/default 25. Existing response shapes and SEC guards are unchanged. AST comparison against integrated main proves every pre-existing twin/dashboard function and class is identical; only the two new route functions and required imports were added. Generated OpenAPI/frontend types remain coordinator-owned and untouched.

Dedicated `test_evidence_history_routes.py` uses the real admitted route/SEC helpers with a synthetic DB boundary and blocks all writes/RPCs. Together with the query tests it covers 69 cases: first/next/final/empty, equal timestamps, limits, malformed/tampered/cross-caller/cross-course cursors, authentication, own enrollment refusal, student staff-route denial, untaught/foreign instructor and foreign admin refusal, unavailable target, allowed teacher/same-institution admin, exact guard order, admission recheck after enrollment removal, identity override prevention and zero writes. Scope/malformed-cursor refusals assert no evidence read.

Integrated API suite: `cd services/api && uv run pytest -q` — **898 passed**, 30 dependency deprecation warnings, 28.84s. Test isolation remains committed `services/conftest.py`, with dotenv disabled and IPv4/IPv6/DNS blocked. No hosted or provider calls.

After the SEC rebase, web lint passes with 18 existing warnings; typecheck and production build pass with existing warnings. All three new browser scripts pass syntax checks. Browser execution still awaits Fred/coordinator handover of the single 5173 server; no browser acceptance claim is made.

The dedicated local Postgres fixture now also executes the route's exact own-enrollment admission predicate with allowed/other-user synthetic cases. Admission and keyset/index checks passed and rolled back all fixtures. All 37 historical migration files remain byte-identical against integrated main; SEC's 0038 was not changed by H. H adds only index migration 0039.

Current H file manifest: twin/dashboard routers (new endpoints/imports only); `app/twin/evidence_history.py`; two dedicated Python history test files and their local SQL fixture; twin history API/schema/hook/wrapper/public export and TwinBody; shared evidence ledger; instructor roster/at-risk/stats/charts/heatmap/learner record/drill-down/triage and feature-local failure helper; three dedicated browser suites; 0039 index/runbook; this evidence record. No shared specs, generated types, infrastructure, dependency manifests, shared DB/config/client/auth files, retained UI/tour fixtures, or class routes were edited.

## Authorized browser handover and results

Fred authorized the temporary 5173 handover. H first rebased cleanly onto coordinator docs commit `105727e`; its difference from the earlier SEC integration base is documentation only. Tests ran against H's own Vite server, with installed Chrome and bundled Playwright 1.62.1 in isolated headless contexts. Synthetic fixture interception blocked non-local requests. No hosted/provider requests or dependency changes were needed.

The full switch/test/restore sequence used an independent Python `try/finally` cleanup process with a restoration signal and deadline. Original U listener **39396**, launcher **39390**, was verified as Vite with command `pnpm --filter web exec vite --port 5173 --strictPort` and cwd in U worktree `2e93` under `apps/web` before stopping only that listener. H launcher **83494**, listener **83515**, was verified in H worktree `7d35/apps/web` with HTTP **200**. After tests, H's process group stopped and U restarted with the same equivalent command. Restored U launcher **85651**, listener **85666**; cwd verified as U `2e93/apps/web`, HTTP **200**. A separate final lsof/cwd/HTTP check confirmed restoration. U source files were never edited.

Passing browser suites:

| Suite | Assertions | Coverage |
| --- | ---: | --- |
| New evidence-history | 80 | Student/instructor older loading through earliest event, retry, invalid cursor reload, ten-row pages, 40px controls, keyboard, reduced/normal motion, 375/1440, no writes |
| New evidence-history-scope | 16 | Actor/role/course/target changes, page reset, unauthorized enablement, 403/404 cached-row hiding, overlapping-page ID deduplication |
| New instructor read-states | 222 | Per-panel 403/404/500/network/slow/empty, genuine empty learner, transient recovery, cached-success refetch failure, actual roster-sheet denials, no writes/crashes |
| Retained Tutor UI overhaul | 219 | Existing synthetic Tutor UI coverage |
| Retained Twin presentation | 148 | Existing readiness/ledger layout, motion and interaction coverage |
| Retained instructor review feedback | 63 | Existing pending/decision feedback behavior |
| Retained diagnostic frontend closeout | 110 | Existing frontend closeout coverage, with active instructor history fixture |
| Retained tour browser | 616 | Both roles/widths, conditional/empty paths and exit behavior; zero mutations |

Total passing browser assertions: **1,474**. Student mobile and instructor desktop history screenshots were visually inspected; the ledger/count/control layout fits and bounded statistics retain their original wording. Screenshots remain temporary local artifacts, not retained evidence assets.

Initial browser fixture failures were investigated and corrected: the scope harness mixed a manually imported query module with Vite's versioned module and used a named hook import from React's CommonJS facade. It now resolves the exact served query-module URL and uses the React default facade. The cached-learner assertion initially matched the persistent session name in shell chrome; it now asserts the actual `tour-standing` region is hidden. No production changes were needed for these fixture failures. A first tour run failed with a missing fixture global while fixture files were changing; the stable rerun passed all 616 assertions.

Coordinator explicitly extended retained fixture ownership to `apps/web/src/features/twin/tests/presentation.browser.mjs` and `apps/web/src/features/diagnostic/tests/frontend-closeout.browser.mjs`: new synthetic history responses and matching active-feed labels only. Their other responses/assertions remain unchanged. The first unadapted runs failed because instructor history received an invalid/missing response; the adapted retained suites pass. No retained Tutor/review/tour browser source was edited.

## Remaining retained unit-test mismatch

Retained frontend/tour unit run with `KALA_TOUR_REQUIRE_DOCS=1`: **31 passed, 1 failed, 0 skipped** (32 total). Separate retained Study renderer tests: **4 passed**. The sole failure is `apps/web/src/components/shell/tests/tour-anchors.test.mjs:14–17`, “attribute-only executable change: features/twin/components/TwinBody.tsx”. It compares all executable TwinBody source to historical `3a6a0aa`, allowing only one tour attribute. WI-25 now intentionally adds the approved history wrapper/prop, so that historical invariant is obsolete. Other six attribute-only checks and the docs-preservation check pass. This test was not edited: the latest retained-fixture grant permits new history responses/label expectations, not changes to that historical AST comparator.

Proposed coordinator-approved correction: retain the historical attribute-only comparison for untouched tour paths; replace TwinBody's obsolete whole-file assertion with a focused before/after inventory of its approved tour anchors after WI-25's behavior change. Do not remove mutation assertions or skip the failure. Until this comparator change is authorized and verified, H does not claim all retained unit checks green.

Post-browser final checks: web lint/typecheck/build pass (18 existing lint warnings and existing build warnings); docs checker and all 18 checker unit tests pass; whitespace checks pass. No product code changed during browser fixture repair. The sole unresolved local check is the retained historical TwinBody attribute-only comparator described above.
