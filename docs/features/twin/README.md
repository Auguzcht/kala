---
feature: twin
req_prefix: TWIN
owner_role: product owner
status: active
code:
  web:
  - apps/web/src/features/twin/
  - apps/web/src/components/kala/mastery-ring.tsx
  - apps/web/src/components/kala/evidence-ledger.tsx
  api: services/api/app/twin/
  worker:
  - services/worker/app/jobs/reconcile_mastery.py
  - services/worker/app/jobs/readiness_snapshot.py
  db:
  - packages/db/migrations/0001_init.sql
  - packages/db/migrations/0002_rls.sql
tests:
- apps/web/src/features/twin/tests/presentation.browser.mjs
- services/api/tests/test_twin_routes.py
- services/api/tests/test_twin_cohort_approved.py
- services/worker/tests/test_reconcile_mastery.py
- services/worker/tests/test_readiness_snapshot_approved.py
---

# Digital learning twin

## Purpose

The twin turns recorded learning evidence into per-skill mastery and a course readiness summary. Students can inspect their evidence; instructors use the same state through guarded instructor surfaces. Readiness is a learning proxy, not an LMS grade or a validated exam prediction.

This focused WI-22 amendment defines readiness-number legibility and bounded evidence browsing for student and instructor views. The accepted presentation requirements below retain their original IDs; this consolidation adds the WI-08 backend contract.

## Actors and permissions

| Actor | Can | Cannot |
| --- | --- | --- |
| Student | Browse the evidence returned for their own twin | Read another student's record |
| Instructor with existing course access | Browse a learner's returned evidence and readiness through existing authorized routes | Gain new course or learner access through this presentation amendment |

### Backend actors and boundaries

| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| student | Read their own course twin and next suggested skill | Submit a trusted mastery estimate |
| instructor/admin | Use the instructor twin/record endpoints | Infer authorization solely from a requested student ID |
| worker | Rebuild derived mastery and append readiness history | Treat snapshots as replacement evidence |

## Student read admission

Own Twin, next-up and assigned-plan GETs follow [AUTH-REQ-007](../lti-auth/README.md#auth-req-007-require-existing-course-enrollment-on-student-reads). The full-history endpoint keeps TWIN-REQ-010’s explicit student-role and scoped-enrollment guard; staff admission remains INSTR-REQ-009. Admission is implemented locally and verified by the 116-case AUTH-REQ-007 route/import matrix and strict AST scope proof; hosted deployment and live acceptance remain pending.

## Requirements

### TWIN-REQ-001: Make readiness values legible inside large rings

- Rule: The shared MasteryRing uses a prominent 48px token-sized, monospaced center value for readiness rings of 128px or more, including the student's 176px board-readiness ring and instructor's 144px readiness ring. Preserve the compact 12px value in 56px skill rings. Keep existing values, null state, fill calculation and motion semantics; reduced motion renders a static number. Zero and 100 must fit without clipping. Expose the value and band with the ring's accessible label.
- Acceptance: Student and instructor readiness centers use the same 48px number style; compact rings retain their original density; null/0/100 render correctly with motion allowed and reduced.
- Status: implemented
- Verified by: apps/web/src/features/twin/tests/presentation.browser.mjs; desktop/mobile captures and final checks in docs/work/handover-2026/evidence/ui-overhaul.md.

### TWIN-REQ-002: Keep Focus area heading plain

- Rule: Remove the decorative icon next to the Focus area heading in shared TwinBody. Preserve its text, skill, mastery band and practice action, including the instructor twin drill-down.
- Acceptance: Focus area has no heading icon and retains the underlying data/action.
- Status: implemented
- Verified by: apps/web/src/features/twin/tests/presentation.browser.mjs; desktop/mobile captures and final checks in docs/work/handover-2026/evidence/ui-overhaul.md.

### TWIN-REQ-003: Page the evidence ledger consistently

- Rule: The shared EvidenceLedger shows ten returned events per page in the existing server order, using Kala's Pagination primitives at the same default 40px control size as the instructor roster. Display the current range and label bounded fallback totals as recent events, not lifetime history. When TWIN-REQ-010 or INSTR-REQ-010 full paging is active, use its loaded-activity wording instead; ten-row pages and controls remain unchanged. Show the shared pager when multiple loaded pages exist or an older server cursor remains; handle empty/one-page lists. Next follows TWIN-REQ-011, including at the last loaded page. The student twin, instructor twin drill-down and learner record use this same component.
- Rule: Page changes replace rows immediately without animating an entire page as new evidence. New events arriving on the current page retain the existing short reveal, disabled by reduced motion. Keep pagination controls keyboard accessible, explicitly disable endpoints, clamp the selected page when the returned list shrinks, and fit mobile widths without horizontal overflow. Use the existing pageWindow helper on larger screens and compact the visible number links on small screens without shrinking controls.
- Acceptance: Ten rows at most are shown; next/previous/numbered/keyboard navigation retains order and stable controls; final-page ranges and disabled endpoints are correct; empty lists and shrinking data are safe at 375px and desktop widths. Both instructor/student views inherit the behavior.
- Status: in-progress; APPROVAL-09 changes the frontend paging control; H keyset/error/scope behavior is retained and final Fred checks are pending.
- Verified by: apps/web/src/features/twin/tests/presentation.browser.mjs; desktop/mobile captures and final checks in docs/work/handover-2026/evidence/ui-overhaul.md.

### TWIN-REQ-004: Derive mastery from graded evidence on the server
- Rule: start at 0.5; for each boolean result update estimate to clamp(prior + 0.15 * (target - prior), 0, 1), target 1 for correct and 0 for incorrect; increment attempts. Self-rated Study recall does not move mastery.
- Acceptance: an initial correct response gives 0.575; an incorrect response 0.425. Clients receive derived state, never choose it.
- Status: implemented
- Verified by: static `app/twin/tracer.py::apply_evidence`; `test_diagnostic_mastery_delta.py`, `test_learn_routes.py::test_flashcards_review_is_a_self_mark_that_never_moves_the_twin`; worker replay tests in `test_reconcile_mastery.py`.

### TWIN-REQ-005: Show approved skills, qualitative bands and recent evidence
- Rule: only approved course skills reach the twin. Missing mastery is null/zero attempts/no-evidence. Bands are developing below 0.4, proficient from 0.4 to below 0.7, mastered at 0.7 or above. Return at most 20 newest evidence events.
- Acceptance: no approved skills gives null readiness and empty skills/evidence; reviewed skills show module/Bloom, estimate, attempts and band. Evidence for an absent skill may read Unknown skill.
- Status: implemented
- Verified by: `test_twin_routes.py::test_twin_returns_skills_bands_and_evidence`, `test_twin_empty_when_course_has_no_skills`; static `summary.py::band_for`, `twin_payload`.

### TWIN-REQ-006: Compute readiness from approved skills with evidence
- Rule: return the arithmetic mean of existing mastery estimates for approved course skills, rounded to three decimals. Missing estimates are excluded, not zero-filled. If approved skills exist but none has mastery, return 0.0; no approved skills gives null at the payload level.
- Acceptance: rejected/proposed skill mastery cannot change the readiness rollup; an unmeasured skill does not depress the measured mean.
- Status: implemented
- Verified by: `test_twin_routes.py::test_readiness_uses_approved_skills_only`, `test_readiness_without_approved_skills_is_zero_without_mastery_query`; `readiness.py::compute`.

### TWIN-REQ-007: Reconcile mastery and preserve readiness history
- Rule: worker replays evidence in ascending created_at order for each user/skill, skips null skill IDs and upserts only changed estimates/attempt counts. Snapshot runs append one row per enrolled student/course with approved-skill mastery, using the same mean; students without that signal get no row.
- Acceptance: unchanged replay performs no correction; missing/drifted state is repaired; repeated snapshot runs append history rather than overwrite it.
- Status: partial
- Verified by: `services/worker/tests/test_reconcile_mastery.py`, `test_readiness_snapshot_approved.py`. Replay caps each institution at 50,000 events without pagination, and worker K is configurable while API K is fixed (finding below).

### TWIN-REQ-008: Suggest a next skill without generating an item
- Rule: next-up reuses the weakest approved-skill picker; unseen skills precede measured skills. Return null when none is eligible and explain whether the choice is unmeasured or low mastery.
- Acceptance: GET next-up returns skill metadata/reason without model generation; it does not append evidence.
- Status: implemented
- Verified by: static `routers/twin.py::next_up`, `learn/items.py::weakest_skill`; related weakest-skill serving tests in `test_learn_routes.py`. There is no dedicated browser next-up acceptance test.

### TWIN-REQ-009: Preserve own-data and guarded staff Twin boundaries
- Rule: Own Twin, next-up and plan derive user/institution from the validated session; students cannot select another user. Staff access to any course/learner data satisfies INSTR-REQ-009 before data access, with target-student membership for learner views. Student GETs also satisfy AUTH-REQ-007; preserve enrolled own-student access and existing response shapes. Presentation or paging grants no extra access. Own plans contain only approved/modified/completed recommendations.
- Acceptance: Existing own-student reads remain intact. Staff wrong-role, untaught-course, foreign-institution and target-membership cases follow INSTR-REQ-009, with allowed correct instructors and same-institution admins. No protected operation occurs after denial.
- Status: done-awaiting-confirmation; local implementation verified, hosted acceptance pending.
- Verified by: `services/api/tests/test_wi26_course_authorization.py`, `test_wi26_student_read_admission.py` and the student AST scope verifier; INSTR-REQ-009 states the separate local policy proof and hosted gate.

### TWIN-REQ-010: Browse complete own evidence history
- Rule: An authenticated student with student enrollment in the requested course and token institution can read only their own evidence through `GET /courses/{course_id}/twin/evidence`. UUID validation alone does not authorize access. This is a new history endpoint; existing Twin/next-up/plan responses remain unchanged.
- Contract: Return `courseId` and `evidence` using the existing event fields (`id`, `type`, `correct`, optional nullable `latencyMs`, `skillName`, optional nullable `createdAt`). Add optional nullable `nextCursor`, returning null or omitting it at the last page. Do not add required fields to existing responses or alter `createdAt`.
- Pagination: Keyset on `(created_at DESC, id DESC)` with default limit 25, minimum 1, maximum 100. Fetch limit plus one, return at most limit; provide a next cursor only when another row exists. Index review covers `(user_id, course_id, created_at)` plus `id` for the tie; 0039, if needed, is index-only with `create index if not exists`.
- Cursor: Use a versioned URL-safe opaque payload authenticated with a domain-separated HMAC derived from the existing server JWT secret, bound to caller, target learner, course and institution. Validate signature, shape, timestamp and UUID before query construction. Invalid/tampered/scope-mismatched cursors return generic 422 without echoing input. Every page rechecks current authorization. No additional cursor TTL or database anchor-existence requirement is introduced; a valid signed cutoff remains usable even if a repair re-attributed the anchor. Secret rotation invalidates old cursors; offer Reload activity on 422.
- Concurrency: Read strictly below the last returned tuple. Equal timestamps order by ID; newer arrivals appear after refreshing the first page. Merge loaded pages deterministically and deduplicate by ID. Cache identity includes institution, caller, validated role, target learner, course and cursor; reset visible pagination on scope changes and never keep another scope's previous data. Do not claim snapshot isolation or lifetime totals.
- Presentation: Keep ten-row ledger pages, keyboard access, reduced motion and 40px controls. Active own-history surfaces say “Showing N of your activity”, where N is the loaded count. Under TWIN-REQ-011 remove the separate “Load older activity” action. Next on the last loaded page fetches the older batch when a cursor remains, and advances only after success. Start the independent history feed rather than mixing its first page with legacy 20/25-row arrays. On a transient own-history fetch failure retain loaded rows and offer retry; a 403/404 hides loaded and fallback rows and shows unavailability. Instructor callers also follow INSTR-REQ-011's failed-request state. Full-history labels appear only after the new request succeeds; retain bounded labels elsewhere.
- Acceptance: First/next/last/empty pages, equal timestamps, invalid/tampered/cross-scope cursors, limit bounds, unavailable course, account/role/course switches, concurrent arrivals, retry and deduplication, and 375px/1440px keyboard/reduced-motion browser tests. Reading creates no evidence or XP; existing charts/statistics and response fields remain unchanged.
- Status: in-progress; APPROVAL-09 changes the frontend paging control; H keyset/error/scope behavior is retained and final Fred checks are pending.
- Verified by: `services/api/tests/test_evidence_history.py`, `test_evidence_history_routes.py`, `tests/fixtures/evidence_history_local.sql` and the Twin evidence-history/scope browser suites at 375px/1440px. No hosted acceptance claim.

### TWIN-REQ-011: Use the ledger pager to load older activity
- Rule: Remove the separate Load older activity button. Next advances through already-loaded ten-row pages. On the last loaded page with a live next cursor, that same Next control requests one older batch using H's existing keyset hook and advances to the next page only after new rows arrive. Disable duplicate activation while pending. At the actual end, disable Next. Do not auto-fetch merely by rendering or pressing Previous.
- Rule: Preserve `(created_at DESC,id DESC)` order, opaque cursor validation, ID deduplication, identity/role/course-scoped cache/reset and all existing API fields/limits. Errors retain the established unavailable, transient-failure, cursor-reload and retry behavior; no failed request becomes an empty ledger or false total. A failed/empty/duplicate-only batch does not advance to a fabricated page or create an automatic fetch loop. Loaded-activity counts remain honest, not lifetime statistics.
- Rule: The same shared behavior applies to student Twin, instructor Twin drill-down and instructor learner record. Preserve H's role denial/error states and all instructor data/summary boundaries. No backend, SQL, evidence/mastery write or API change.
- Acceptance: Next within loaded pages; final-loaded Next delayed/success/error/retry; genuine end, empty and duplicate-only batches; Previous and numbered navigation; scope switches, student/instructor denial and cursor errors;375px/1440px keyboard/reduced motion. Remove only obsolete separate-load-button expectations from affected tests while retaining H fixtures, cursor and identity-scope assertions.
- Status: planned; Fred implements under APPROVAL-09 after this specification.
- Verified by: pending affected Twin/history/instructor browser suites after Fred finishes; existing keyset API tests stay unchanged.

## API contract

### Accepted presentation boundary

The original presentation-only amendment retained bounded legacy responses: Twin returns at most 20 events; learner-record statistics read at most 200 and serialize 25. WI-25 now implements an independent authorized keyset history feed under TWIN-REQ-010 / INSTR-REQ-010. Active feeds use loaded-activity wording and ten-row local pages with the unified Next behavior under TWIN-REQ-011; bounded fallback surfaces retain “Last 20 events” / “Last 25 events”. Statistics still say “Based on recent activity” and remain bounded. Paging does not change existing summary responses, calculations or evidence. The earlier 200-row response description confused internal reads with serialized ledger rows.

### Backend contract
| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| GET /courses/{course_id}/twin | Own skills/readiness/recent evidence | Session; student enrollment under AUTH-REQ-007 | Read only; unavailable course/enrollment 404 |
| GET /courses/{course_id}/twin/evidence | Independent own full-history feed | Student, token institution and current student enrollment | TWIN-REQ-010 cursor/limit contract; no writes |
| GET /dashboard/{course_id}/students/{user_id}/evidence | Independent learner history | INSTR-REQ-009 staff/course/learner admission | INSTR-REQ-010; no writes |
| GET /courses/{course_id}/next-up | Own next suggested skill | Session | Returns next=null when no candidate; no generation |
| GET /dashboard/{course_id}/students/{user_id}/twin | Staff drill-down | Instructor/admin | INSTR-REQ-009 staff/course/learner admission |

`/courses/{course_id}/plan` belongs to [instructor-insights](../instructor-insights/README.md). Student twin UI groups skills by module and Bloom (`TwinBody.tsx`, `lib/group-by-module.ts`); it does not write mastery.

## Data

### Accepted presentation boundary

No new persistence. Readiness and evidence remain server-owned; only the current presentation page is local UI state. Evidence remains append-only and is never edited or deleted by pagination.

### Backend contract
Read skills, mastery_state and evidence_events. Server grading writes append-only evidence and tracer-derived mastery; worker reconciles mastery and writes readiness_snapshots. RLS `evidence_read`, `mastery_read` and `readiness_read` allow self, course teacher and institution admin. API/worker service-role calls bypass RLS; own-user route arguments and explicit course/institution filters are therefore part of the boundary. Some helper queries scope by user/course or globally unique skill IDs without an explicit institution predicate; this is not a complete API tenancy audit.

## AI usage (if any)

### Presentation amendment
None added.

### Backend usage
No model computes mastery, bands, readiness or snapshots. Recommendations/generation belong to other features. No claim of BKT, learned forgetting, confidence intervals, blueprint weighting or exam-score calibration is made.

## Edge cases and known limits

Long skill names, mobile widths, empty/one-page lists, list shrinkage, null/0/100 readiness and reduced motion are part of done. Focus and pagination must remain usable without pointer input. No hosted mutation or deployment is authorized by this amendment.

- Readiness over measured skills can look high with thin coverage; interpret with attempts/coverage. Students have no readiness-history endpoint in this feature; instructor stats do read snapshot history.
- Reconciliation does not delete stale mastery rows that have no remaining evidence; event order ties have no explicit secondary sort.
- Snapshot inserts are per run, not once per day; history can contain multiple rows on one date.
- Student GET routes use authenticated user identity but do not explicitly enforce course enrollment before computing. No cross-course access test is claimed.

## Contradictions requiring planner resolution

| Locations at source revision | Finding | Proposed resolution (not implemented here) |
| --- | --- | --- |
| `services/api/app/twin/readiness.py:1` (weighted blueprint description); `services/api/app/twin/readiness.py:22` (plain mean) | Weighting is described but not applied. | Correct the source description to this observed contract, or approve a separately tested weighting change. |
| `services/api/app/twin/tracer.py:8`; `services/worker/app/config.py:129`; `services/worker/app/jobs/reconcile_mastery.py:85` | API uses fixed K=0.15; replay uses configurable tracer_k. Divergence is possible under nondefault configuration. | Centralize or validate the parameter and prove live/replay equivalence for supported settings. |
| `services/api/app/twin/summary.py:13`; `services/api/app/learn/xp.py:35` | Twin calls 0.7 mastered; badges call 0.7 proficient and 0.85 mastered. | Decide whether badge tiers intentionally differ, then update wording or thresholds through scoped implementation. |

## Evidence and verification limits

WI-08 / APPROVAL-05 rev 2, Lane P. Source reviewed at `4f3ec29d3f827a1db92e90c4f395947d37744479` on 2026-10-25. `implemented` means present in that source, with the evidence stated per requirement; it is not a claim of deployed acceptance. `partial` identifies an explicit gap. Planned behavior is not inferred from archived plans.

- Local: `cd services/api && uv run pytest -q` — **431 passed**, 30 dependency deprecation warnings, 28.45s.
- Local: `cd services/worker && uv run pytest -q` — **117 passed**, 0.68s.
- Both processes used committed `services/conftest.py`: dotenv disabled, inherited application settings replaced, IPv4/IPv6/DNS blocked. Tests use mocked boundaries; no hosted data or provider calls.
- No browser acceptance, live LTI/Blackboard check, RLS replay, deployment, migration, lint/typecheck/build claim is made by this documentation-only lane. UI evidence is static source review unless stated otherwise.

The API/worker results above are retained historical evidence from the original Lane P source review, not new runs on this integration base. Accepted presentation evidence remains attributed to the existing browser suites and WI-22 evidence; this documentation reconciliation does not rerun or upgrade that acceptance. H12 copy requirements are retained from main; Lane U closeout source is now integrated at `8bc569e`. The explicit labels were checked in source, not reverified in a browser here.

## Reconciliation lineage and ID mapping

Coordinator-approved consolidation onto `8bc569e36b52488b4e05202a90cb18c8ba0db589` after Lane I merge. AUTH remains byte-for-byte main's file; no auth behavior or identity policy is reintroduced here. Accepted TWIN presentation IDs and change-log entries are unchanged. Only the unmerged backend draft IDs from `2062784` are reassigned below; references to that historical revision must use this mapping.

| Draft ID at `2062784` | Final ID | Backend requirement |
| --- | --- | --- |
| TWIN-REQ-001 | TWIN-REQ-004 | Derive mastery from graded evidence on the server |
| TWIN-REQ-002 | TWIN-REQ-005 | Show approved skills, qualitative bands and recent evidence |
| TWIN-REQ-003 | TWIN-REQ-006 | Compute readiness from approved skills with evidence |
| TWIN-REQ-004 | TWIN-REQ-007 | Reconcile mastery and preserve readiness history |
| TWIN-REQ-005 | TWIN-REQ-008 | Suggest a next skill without generating an item |

Historical reconciliation at `8bc569e` confirmed the legacy 20/25-row responses, 200-event learner statistics read and 2,000-event class-wide statistics bound. APPROVAL-07 now supersedes the WI-25 paging deferral: the independent cursor feed is locally implemented while those summary/statistics bounds remain unchanged. Active full-history ledgers use loaded-activity wording; inactive bounded surfaces retain H12 labels. Hosted acceptance remains pending.

## Current source revalidation

Static review at `8bc569e36b52488b4e05202a90cb18c8ba0db589` preserves accepted presentation requirements, H12 wording and the mapped backend rules. Source confirms 20/25 returned-event limits, the internal 200-event learner read, class-wide 2,000-event evidence bound, server-owned calculations and unchanged pending-decision behavior. This is documentation validation only; no test, lint, typecheck, build, browser or hosted check was rerun.

Documentation validation for this reconciliation passed: YAML and referenced code/test paths, requirement fields and unique IDs, local links, source line bounds, accepted presentation/changelog preservation, exact draft-to-final mapping, unchanged Lane S requirement, auth byte identity and eight-path ownership. Runtime tests were not rerun.

## APPROVAL-07 local verification boundary

At integrated source `8e51040f1dda4235f9b12ad344da4cd81442e1e9`, reviewed staff guards, H history/error states, M repair tooling and student-read admission are locally integrated. Full API: 1,014; worker: 117; frontend/tour unit: 33; Study component: four. Web lint/typecheck/build and configuration inventory pass. Final integrated synthetic browser verification passes 1,474 assertions; real LTI acceptance is not inferred. Earlier revision-specific evidence retains its recorded attribution. Hosted 0038/0039 application, release, real-pair repair or safe refusal, and live acceptance are separate human gates; this record upgrades no live result.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-27 | Specify one pager: final-loaded Next fetches the next keyset batch for student/instructor views; preserve H errors/scope and backend contracts | APPROVAL-09 | TWIN-REQ-003/010/011 |
| 2026-10-25 | Record merged local verification and supersede stale implementation-pending findings; retain hosted gates and bounded summary/statistics limits | APPROVAL-07 coordinator integration; no new behavior | TWIN-REQ-003/009/010; AUTH-REQ-007 |
| 2026-10-25 | Require existing enrollment admission on inventoried student GETs; preserve staff, mutations and enrolled processing | APPROVAL-07 Amendment 7; coordinator spec before follow-up implementation | AUTH-REQ-007; WI-26 |
| 2026-10-25 | Define prominent readiness numbers, plain Focus area heading and shared ten-row ledger pagination before implementation | Fred's direct WI-22 visual/pagination request for student and instructor views | TWIN-REQ-001, TWIN-REQ-002, TWIN-REQ-003 |
| 2026-10-25 | Correct the observed instructor ledger response window to 25; distinguish the internal 200-event statistics read | Final UI/UX handoff source trace of cohort.learner_record; no runtime or intended-behavior change | TWIN-REQ-003 |
| 2026-10-25 | Require explicit 20/25-event window labels and recent-activity wording; full-history pagination deferred | APPROVAL-06 H12; Lane U close-out implements copy | TWIN-REQ-003 |
| 2026-10-25 | Write full source-backed feature spec; identify limits and contradictions | APPROVAL-05 rev 2 Lane P; handover WI-08 | TWIN-REQ-004 through TWIN-REQ-008 |
| 2026-10-25 | Consolidate accepted presentation requirements and mapped backend draft; preserve H12 windows, WI-25 deferral and revision-specific evidence | Coordinator-approved Lane P reconciliation after APPROVAL-06 Lane I merge; draft `2062784` mapping above | TWIN-REQ-001 through TWIN-REQ-008 |

| 2026-10-25 | Define own-student and staff-authorized Twin access before guard implementation | APPROVAL-07 section 1 and Amendments 2–3, WI-26; coordinator | TWIN-REQ-009 |

| 2026-10-25 | Define authorized cursor-backed full-history loading; preserve bounded fallback responses/statistics and clarify active-feed labels | APPROVAL-07 section 2 and Amendment 1, WI-25; coordinator spec before H implementation | TWIN-REQ-003, TWIN-REQ-010 |

| 2026-10-25 | Make history cache isolation explicit for validated-role changes; hide cached/fallback rows on 403/404 and follow instructor error states | Existing TWIN-REQ-010 isolation acceptance; APPROVAL-07 Amendments 5–6, coordinator review | TWIN-REQ-009, TWIN-REQ-010 |
