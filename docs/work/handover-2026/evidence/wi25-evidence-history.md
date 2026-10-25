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
