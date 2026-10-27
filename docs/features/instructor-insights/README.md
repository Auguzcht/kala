---
feature: instructor-insights
req_prefix: INSTR
owner_role: product owner
status: active
code:
  web:
  - apps/web/src/features/instructor/
  - apps/web/src/features/plan/
  api: services/api/app/routers/dashboard.py
  worker:
  - services/worker/app/jobs/readiness_snapshot.py
  db:
  - packages/db/migrations/0002_rls.sql
  - packages/db/migrations/0009_teacher_loop.sql
tests:
- apps/web/src/features/instructor/tests/review-feedback.browser.mjs
- services/api/tests/test_dashboard_routes.py
- services/api/tests/test_twin_cohort_approved.py
- services/api/tests/test_twin_routes.py
---

# Instructor insights and assigned learning plan

## Purpose

Give the instructor a roster, cohort evidence and an individual learner record from which to decide support actions. Recommendations remain teacher-facing proposals until approved or modified; learners see the assigned action and instructor note, not the model's confidence or raw rationale panel.

This focused amendment defines visible feedback for instructor skill reviews and recommendation decisions. The accepted presentation requirements below retain their original IDs; this consolidation adds the WI-08 backend contract.

## Actors and permissions

| Actor | Can | Cannot |
| --- | --- | --- |
| Instructor with existing course access | Review proposed skills and confirm recommendation decisions through existing APIs | Gain access to another course or bypass the server's decision gate |

### Backend actors and boundaries

| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| student | Read their own approved/modified/completed plan | View undecided/rejected recommendations through the plan API or access dashboard routes |
| instructor | Inspect their class, generate proposals and decide/author actions | Access an untaught course or another institution |
| admin | Support institution-level oversight | Access another institution's data |
| model | Propose bounded actions from an allow-listed context | Publish directly to the learner's plan |

## Requirements

### INSTR-REQ-001: Keep skill-review feedback visible

- Rule: Approve and Reject send their existing request immediately, disable review controls and show Kala's shared Spinner on the selected action. Keep this pending presentation for at least 350ms, or the actual request duration when longer, before refreshing the proposal queue. The brief presentation interval must never delay starting the request or fabricate success. Use static Spinner artwork under reduced motion. A failed review retains the row and an explicit retry direction.
- Acceptance: Fast and slow approve/reject responses expose a busy disabled action before the row changes; exactly one request is sent; failure restores controls and leaves the proposal available for retry.
- Status: implemented
- Verified by: apps/web/src/features/instructor/tests/review-feedback.browser.mjs; synthetic pending-state captures and final checks in docs/work/handover-2026/evidence/ui-overhaul.md.

### INSTR-REQ-002: Confirm recommendation decisions before moving them to history

- Rule: On Confirm, keep the recommendation visible with a disabled “Recording” action and shared Spinner until its server response and the same minimum 350ms presentation interval complete. Do not move it to decision history optimistically. Lock decision choices and editable notes during recording. Success uses the validated returned recommendation and refreshes related queries. Failure preserves the card, selected decision and notes for retry, and shows the existing error notice. Nothing is assigned or reported successful before server confirmation.
- Acceptance: Approve/modify/decline confirmation visibly records before history changes; no duplicate request occurs; a slow request remains pending; failure leaves editable retryable input. Reduced motion uses the same static loading glyph.
- Status: implemented
- Verified by: apps/web/src/features/instructor/tests/review-feedback.browser.mjs; synthetic pending-state captures and final checks in docs/work/handover-2026/evidence/ui-overhaul.md.

### INSTR-REQ-003: Show enrolled students and reviewed skill evidence
- Rule: roster/stats/learner-record use student membership on both enrollment and user roles; exclude instructor/admin identities. Display real teacher-visible names with pseudonym fallback for missing/placeholder profiles, and preserve pseudonyms for de-identified UI mode. Mastery aggregates use approved skills only.
- Acceptance: co-teachers do not become zero-mastery learners; rejected-skill mastery does not change cohort stats; empty class gives valid empty structures.
- Status: implemented
- Verified by: `test_twin_cohort_approved.py::test_cohort_stats_limits_mastery_aggregates_to_approved_skills`; static `twin/cohort.py::student_ids`, `load_identities`, `roster`, `stats`. Comprehensive role/profile/empty-class route tests are absent. Heatmap's older `_cohort` path filters enrollment role but not user role, as recorded below.

### INSTR-REQ-004: Explain cohort standing and support needs with evidence
- Rule: heatmap returns student/approved-skill cells and cohort bands, optionally module-scoped. Roster status orders not-started (zero attempts), needs-support (>=7 days inactive or >=5 attempts with accuracy <0.4), on-track (readiness >=0.7), then developing. At-risk does not flag zero evidence; it explains inactivity, low recent success, or two weakest measured skills below 0.4.
- Acceptance: a fresh enrollee is not automatically a support concern; inactive measured students have supportive reasons; no flagged student yields an empty list.
- Status: implemented
- Verified by: `test_dashboard_routes.py::test_heatmap_builds_student_by_skill_cells`, `test_at_risk_flags_inactive_student_with_supportive_reason`, `test_at_risk_good_news_empty_state`; static `cohort.py::_status_for`, `dashboard.py::_reason_for`.

### INSTR-REQ-005: Provide cohort trends and an individual record
- Rule: stats expose readiness, active counts, distribution/Bloom/skill breakdowns, 28-day activity/readiness history and decision counts. Learner record adds identity, mastery, peer comparison, recent accuracy/momentum, engagement and evidence. Heatmap cohort readiness averages skill means; stats cohort readiness averages measured learner means, so they need not coincide.
- Acceptance: trends use saved snapshots/evidence, not invented points; missing measurements remain absent/null; record returns 404 for a nonstudent outside the course roster.
- Status: implemented
- Verified by: static `twin/cohort.py::stats`, `learner_record`; approved-only aggregation test above; `test_dashboard_routes.py::test_student_twin_drill_down` covers the separate legacy twin drill-down, not full record/trend behavior. Browser chart acceptance remains unverified.

### INSTR-REQ-006: Keep generated recommendations behind a human decision
- Rule: generate at most five cleaned recommendations from current learner record. Persist as suggested with source/evidence/rationale/confidence/expected gain. If a nonempty newer batch exists, mark previous suggested rows rejected with Superseded note; preserve already decided rows. Teacher decisions distinguish approved, modified and rejected, with decider/time and optional notes/edits.
- Acceptance: regeneration keeps decision history; invalid decision status returns 400; missing recommendation 404; no suggested/rejected row appears in learner plan.
- Status: partial
- Verified by: static `dashboard.py::generate_recommendations`, `decide_recommendation`, `ai/prescriber.py`, `routers/twin.py::learning_plan`; committed API tests do not cover the full recommendation/decision/plan loop. No test or live acceptance is inferred from UI presence.

### INSTR-REQ-007: Let instructors author direct actions and learners see only assigned work
- Rule: direct intervention is source=instructor/status=approved immediately; supported kinds are practice, lesson, flashcards, tutor, diagnostic, outreach. Learner plan contains only approved/modified/completed, newest decided first, at most 20; omit model confidence, rationale and raw evidence. Outreach has no invented action link. No endpoint currently marks an action completed.
- Presentation: Tutor Start opens a fresh Tutor draft under TUTOR-REQ-018 using the assigned skill name or title. It makes no create/ask/completion request until the student explicitly submits. Other item destinations and outreach's lack of a CTA remain unchanged.
- Acceptance: assigned text/note appears on From your instructor; empty plan hides the card; completed history can display if present. Invalid intervention kind returns 400.
- Status: partial
- Verified by: static `dashboard.py::create_intervention`, `twin.py::learning_plan`, `features/plan/components/InstructorPlan.tsx`. No full workflow/browser test or automatic completion behavior is claimed.

### INSTR-REQ-008: Enforce staff course ownership before service-role access
- Rule: course staff must teach the requested course; institution admins are institution-scoped. A target learner must be an enrolled student. Apply this before all reads/writes, including recommendation decisions.
- Acceptance: student gets 403; instructor outside course and cross-institution requests get 404 before data access; decisions cannot alter an unowned course.
- Status: done-awaiting-confirmation; locally enforced under INSTR-REQ-009, hosted acceptance pending.
- Verified by: `services/api/tests/test_wi26_course_authorization.py`; course, institution and target-learner guards now precede protected work. The historical role-only finding is locally resolved; 0038 direct-access policies await Fred FG-6.

### INSTR-REQ-009: Authorize staff course and learner access
- Rule: Before any staff-facing course/learner read or staff course action, require instructor/admin role from the validated token. Instructors must have a current instructor enrollment for that exact course in the token institution. Admins may access only courses belonging to their token institution. Learner-specific reads/writes also require the target to be an enrolled student in that course and institution. Enforce before roster, cohort stats/charts, heatmap, at-risk, learner record, another learner's Twin, recommendations read/generate/decide, interventions, skill review and refresh, and shared course sources used by staff screens. UUID validation and institution-filtered result queries alone are insufficient admission checks.
- Rule: Wrong role on a staff route returns 403. Untaught/unavailable course or learner, and cross-institution access by instructors/admins, return generic 404 without revealing existence. Reuse the existing staff course gate plus existing institution-scoped course resolution; do not create a replacement gate. Preserve legitimate own-student and preview access on shared routes; apply staff admission guards without converting those routes to staff-only.
- Rule: Direct recommendation reads expose only approved/modified/completed rows to the owning student. Authorized course instructors and same-institution admins retain decision history. New RLS may only tighten access; applied migrations and helper definitions are immutable in this round.
- Rule: Review authenticated policies on personal learning, identity and course data as well as recommendations. Staff policy access requires the same token role, institution and current taught-course boundary; an unused frontend client is not evidence of safe direct access. Preserve legitimate student own-data access and existing non-staff curriculum/research access. Tightening must be proved against the local replay without changing authorization helpers.
- Rule: Recommendation-ID operations perform one id/token-institution/route-course-scoped lookup, then existing course and target-student guards; absent/out-of-scope is generic 404. Bind mutation to the looked-up `user_id` as well as id/institution/course so a moved/changed target cannot be updated by stale admission. Zero updated rows preserves the existing 404 pattern. Decision semantics, confirmation, response fields and history stay unchanged.
- Acceptance: Each fixed staff route covers student 403, other-course instructor 404, cross-institution instructor/admin 404, correct instructor allowed, same-institution admin allowed, and no protected read/write/queue/model/worker action after denial. Local authenticated RLS tests cover owning student, other-course instructor and correct teacher with before/after policies. Refresh denial queues nothing and kicks no worker. Staff frontend 404s produce truthful unavailable/not-found UI; UI defects are findings, never a reason to loosen API checks.
- Status: done-awaiting-confirmation; local guards/policy proof complete, hosted application and acceptance pending.
- Verified by: `services/api/tests/test_wi26_course_authorization.py` (219 focused cases in the SEC implementation), local `wi26_rls_local.py` (350 authenticated read cases plus write/removal counterexamples), and reviewed Diagnostic AST scope proof at the staff-only checkpoint. The later student proof permits only AUTH-REQ-007 additions. Fred applies reviewed 0038; no hosted policy state is inferred.

### INSTR-REQ-010: Browse authorized learner evidence history
- Rule: `GET /dashboard/{course_id}/students/{user_id}/evidence` uses TWIN-REQ-010's response, cursor and stable `(created_at DESC, id DESC)` paging contract. Enforce SEC's INSTR-REQ-009 staff/course/institution gate and target-student membership before evidence access. Correct instructors and same-institution admins are allowed; wrong role is 403, untaught/unavailable or foreign-institution course/learner is 404. Identity/presentation never grants new access.
- Presentation: The shared ledger and instructor learner views keep ten-row pages and add “Next on the last loaded page (TWIN-REQ-011)” only with a next cursor. A successful active full-history request says “Showing N of this learner's activity”, where N is loaded rows. Preserve existing bounded statistics and legacy labels wherever full paging is inactive. Apply TWIN-REQ-010 cache/scope/reset/deduplication/failure/retry and keyboard/reduced-motion rules.
- Acceptance: Correct teacher and same-institution admin succeed; student, outside-course instructor, foreign-institution instructor/admin and unenrolled target are refused before data access. Cover TWIN-REQ-010 paging/cursor/limit scenarios, browser loading at 375px/1440px and zero evidence/XP writes from views.
- Status: done-awaiting-confirmation; local integration verified, hosted acceptance pending.
- Verified by: `services/api/tests/test_evidence_history.py`, `test_evidence_history_routes.py`, the local index/keyset fixture and Twin history/scope browser suites; no hosted acceptance claim.

- APPROVAL-09 presentation amendment: the shared ledger removes its separate older-batch button. Next fetches older activity at the last loaded page under TWIN-REQ-011, for learner record and Twin drill-down alike. Keep all authorization, keyset, identity cache, error/unavailable/Retry states and instructor summary limits unchanged. Implemented locally with history 118, scope 16, presentation 148 and instructor read-state 222 assertions passing in the final sequential browser run. Human/hosted confirmation remains pending.

### INSTR-REQ-011: Distinguish loading, unavailable, failed and empty instructor views
- Rule: Roster, at-risk, cohort stats/charts, heatmap and learner record/drill-down callers use existing UI primitives and tokens. Loading uses the current skeleton only while loading. Any failed request, including a refetch after cached success, is not an empty class, zero statistics or a stuck skeleton. For 403/404 show “This class isn't available to you”; for other failures show “Couldn't load the class, try again”, with Retry where meaningful. Successful empty data keeps the actual empty state.
- Rule: An inaccessible learner URL uses “Learner unavailable”, non-disclosing course/learner copy and Back to class linking `/class`; transient learner failures retain retry. No API change or additional query retry loop. Never expose raw error bodies or resource existence.
- Acceptance: Synthetic browser cases at 375px/1440px for 404, 403, 500, network failure, slow response and genuine empty class across roster, at-risk, cohort stats and learner record. No false empty roster/zero stats on error, no permanent skeleton, and successful transient Retry recovery. Existing charts/stats/learning behavior and accessible controls remain intact.
- Status: done-awaiting-confirmation; synthetic verification complete, live acceptance pending.
- Verified by: `apps/web/src/features/instructor/tests/read-states.browser.mjs` (222 assertions at 375px/1440px, including denied, failed, slow, empty and retry cases).

### INSTR-REQ-012: Make learner standing and measurement windows explicit

- Rule: Class standing is a course rank among learners with measured readiness from the existing roster, with an explicit measured-learner denominator and shared ranks for ties. Never render the record percentile as an ordinal rank. Unknown or failed roster data leaves rank unavailable rather than inventing a value. Preserve the record's own readiness and the server's evidence calculations.
- Rule: Label drawer accuracy as graded outcomes within the last 200 evidence events. Roster accuracy uses each learner's graded outcomes within the latest 2,000 events across the enrolled class. The roster attempt count sums approved-skill mastery attempts and is not the accuracy denominator. Momentum compares the last ten graded outcomes with the preceding ten inside the record window. A displayed zero is neutral, including a small change that rounds to zero points.
- Investigation gate: Before metric edits, use Fred-proved canonical/legacy identity anchors and the actual roster/drawer request targets for a counts-only ownership and window check. Never infer identity from names or merge legacy history in the UI. Stop immediately on cross-learner mixing. Agents prepare and locally validate read-only SQL. Fred runs hosted counts or explicitly authorizes the agent to use the Supabase CLI for counts only. Zero cross-owner counts prove the checked filters and anchors only, not the semantic authorship of historically misattributed rows.
- Rule: Skills measured uses approved skills for the same institution/course. A change from 14 to 15 requires counts from the same environment/course and a dated comparison before attributing it to an approval or an environment difference.
- Acceptance: Test measured course rank, ties, unmeasured/absent learner and failed roster, explicit accuracy window, positive/negative/zero momentum and both learner surfaces. Validate count-query results with synthetic real local Postgres including wrong-target/cross-alias counterexamples. Do not edit APIs, migrations, identity records or configuration.
- Status: in-progress, owner Codex. Current enrolled-record counts are checked before presentation edits. Historical WI-24 pairs remain unresolved and are not merged or certified.
- Verified by: Static source trace of cohort.py roster and learner_record, LearnerStanding.tsx and the course/learner query keys. The counts-only query and its synthetic local PostgreSQL 17.6 proof pass. Hosted current-record counts are recorded below. Historical semantic attribution remains outside this counts-only proof.

#### Counts review before implementation

Fred privately fills [learner-counts.readonly.sql](../../../apps/web/src/features/instructor/tests/learner-counts.readonly.sql) with independently proved institution/course, canonical/legacy anchors and actual roster/drawer request targets. It runs a repeatable-read, read-only transaction and returns one aggregate JSON object, no identifiers or event rows. Required inputs must be set, all supplied anchors must exist in the institution, both canonical learners must be enrolled, targets must match Hanna's canonical anchor and every cross-family/Alfred-owned counter must be zero. Missing legacy mapping or timestamp boundary ties are unresolved evidence, not clean attribution. Stop on a cross-learner finding. Source filters alone do not prove historical semantic ownership.

Run the [local SQL proof](../../../apps/web/src/features/instructor/tests/learner-counts.local.py) with Python 3.10+ and Docker's cached PostgreSQL image. It creates/removes only its network-disabled, port-free synthetic container. On PostgreSQL 17.6 it verifies separate accuracy windows, attempt totals, 10/10 momentum counts, course/institution scope, 2,000-event cap, missing parameters, wrong drawer target, cross-family anchor collision and cross-family alias owner, and a rejected write in a read-only transaction. The synthetic 286/381 versus 138/200 example recreates the displayed percentages to test arithmetic. It is not Hanna's measured data, an RLS proof or a migration replay.

Fred explicitly authorized hosted Supabase CLI counts on 2026-10-27 and directed use of the CLI rather than a local Supabase stack. The CLI query uses read-only transactions and returns aggregates only. Candidate discovery finds two stored profile-labelled anchors per learner, one currently enrolled anchor each and one common institution/course scope. There are zero cross-family alias owners. Neither non-enrolled candidate has an alias link proving convergence to the current anchor, so those legacy pairs remain unresolved. Do not assign them by name alone, treat their placeholder NULL counts as measured zeros, or merge their history. The source and current-window checks below verify current stored user ownership, not historical semantic authorship or a completed WI-24 repair.

| Current hosted aggregate | Count |
| --- | --- |
| Enrolled learners / measured learners | 25 / 2 |
| Measured learners above Hanna / tied including Hanna | 0 / 1 |
| Hanna current evidence / graded / correct | 396 / 396 / 297 |
| Hanna approved-skill mastery attempts / measured skills | 381 / 11 |
| Alfred current evidence / graded / correct | 13 / 13 / 9 |
| Class-window events, below the 2,000 cap | 409 |
| Hanna drawer events / graded / correct | 200 / 200 / 138 |
| Hanna recent graded / correct | 10 / 9 |
| Hanna prior graded / correct | 10 / 9 |
| Hanna drawer hints | 0 |
| Hanna checked-window events owned by Alfred's current anchor or either Alfred-labelled candidate | 0 |
| Current approved / proposed skills | 15 / 7 |
| Currently approved skills reviewed before 2026-10-27 / on that date | 14 / 1 |
| Currently approved skills reviewed after the first 21:42 screenshot / created on that date | 1 / 0 |

Thus roster accuracy is 297/396 = 75%, drawer accuracy is 138/200 = 69%, and 381 is a separate mastery attempt total. Momentum is 9/10 minus 9/10 = zero. Hanna is first among the two measured learners. No cross-learner mixing was found in the checked current records and source filters. Both record and roster filter institution/course/user and the frontend query keys include course and learner. The SQL target check uses the unique current enrolled candidate, not a captured live browser request, so live DOM target verification is a separate limit.

The local app points to the deployed API and the same Supabase project used for these CLI counts. Approved skills are course/institution-scoped in source. Current approval metadata accounts for 14 becoming 15: one existing skill was reviewed today after the first screenshot, with no approved skill newly created today. This supports an approval change rather than a separate local skill catalogue. Current timestamps are not an immutable approval history or a replay of the earlier hosted dashboard.

[Candidate discovery](../../../apps/web/src/features/instructor/tests/learner-counts.discovery.sql) returns counts only and refuses to imply a real pair from names. Its synthetic SQL proof completed on local PostgreSQL 17.6 before Fred's subsequent CLI-only direction. No further local database run is part of the hosted investigation. Generic aggregate SQL and discovery are retained with tests. Hosted scoped query/aggregate artifacts are in `/tmp/kala-approval09-hosted-counts` and the detail-count counterpart, local only, not retained. No identifiers, rows, credentials, configuration or hosted writes are recorded.

## API contract

### Accepted presentation boundary

| Method/path | Purpose | Auth | Change |
| --- | --- | --- | --- |
| PATCH /dashboard/{course_id}/skills/{skill_id}/review | Approve/reject a proposed skill | Existing instructor/admin course gate | None |
| PATCH /dashboard/{course_id}/recommendations/{rec_id} | Record a confirmed recommendation decision | Existing instructor/admin course gate | None |

### Backend contract
| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| GET /dashboard/{course_id}/roster | Class roster rollups | Instructor/admin | INSTR-REQ-009 staff/course admission |
| GET /dashboard/{course_id}/stats | Cohort KPIs/charts | Instructor/admin | Bounded statistics; INSTR-REQ-009 admission |
| GET /dashboard/{course_id}/heatmap | Approved-skill cells | Instructor/admin | Optional module_ref; INSTR-REQ-009 admission |
| GET /dashboard/{course_id}/at-risk | Support reasons | Instructor/admin | Empty list is normal |
| GET /dashboard/{course_id}/students/{user_id}/twin | Legacy student twin | Instructor/admin | Same-institution user lookup; not full learner record |
| GET /dashboard/{course_id}/students/{user_id}/record | Learner record | Instructor/admin | Target student-membership check; 404 missing |
| GET /dashboard/{course_id}/students/{user_id}/recommendations | Decision history (up to 50) | Instructor/admin | Includes suggested and rejected |
| POST /dashboard/{course_id}/students/{user_id}/recommendations | Analyze current learner | Instructor/admin | May invoke model; supersedes pending only when proposals nonempty |
| PATCH /dashboard/{course_id}/recommendations/{rec_id} | Decide/edit | Instructor/admin | Body status plus title/kind/priority/decision_note/instructor_note; 400/404 |
| POST /dashboard/{course_id}/students/{user_id}/interventions | Teacher-authored action | Instructor/admin | title/kind/priority/skill_id/instructor_note; immediately approved |
| GET /courses/{course_id}/plan | Own assigned learning plan | Session, own identity | approved/modified/completed only; up to 20 |

Skill review API is specified in [skills](../skills/README.md). PATCH decision has no pending-only precondition/idempotency token; it can change a previously decided row. Do not describe an immutable transition history beyond the persisted current row and its timestamps.

## Data

### Accepted presentation boundary

No new persistence or identity mapping. TanStack Query owns server responses. The presentation interval exists only while an existing mutation runs. Hosted identity repair is outside this amendment.

### Backend contract
Read enrollments/users/profiles, skills, mastery_state, evidence_events and readiness_snapshots; write recommendations via API service role. API admission now satisfies INSTR-REQ-009 before service-role operations. Historical 0002/0009 recommendation policies are narrowed by reviewed 0038, locally proved but not yet applied by Fred: own students see only approved/modified/completed, and staff access is course/institution/target scoped. Service-role access bypasses RLS, so both API guards and direct authenticated policy acceptance are required.

The presentation table retains its accepted access description. Service-role admission is implemented locally under INSTR-REQ-009; a role gate alone remains insufficient. Hosted acceptance is separate.

## AI usage (if any)

### Presentation amendment
None added. Reviewing an existing proposal or recommendation does not introduce a model call.

### Backend usage
`ai/prescriber.py::_model_context` allow-lists pseudonym, aggregate numbers and skill name/Bloom/estimate/attempts; no display name/email/LMS ID/raw event row is included. Shared router uses the configured default model; malformed/unavailable output falls back to deterministic heuristic suggestions with source=heuristic. Cleanup bounds title/rationale/evidence counts and numeric confidence/gain. This schema boundary is narrower than raw-record serialization, but skill text still relies on limited shared de-identification. No accuracy guarantee is implied by numeric confidence.

The recommendation proposer calls the router's default role, not the Tutor chat role. Configuration names are OPENROUTER_MODEL_DEFAULT when AI_PROVIDER selects OpenRouter, or BEDROCK_MODEL_DEFAULT for Bedrock. The OpenRouter fallback setting is OPENROUTER_MODEL_FALLBACK. These are setting names only. Fred privately confirmed on 2026-10-27 that the hosted proposer uses a paid :floor model, not :free, and closed drawer finding 4 with no configuration change. The complete current hosted model ID was not supplied to this investigation and is not inferred from repository defaults.

Recommendation source is stored when the proposal is generated and rendered from that saved row. The displayed minimax/minimax-m3:free is historical proposal-time source metadata, not a read of current configuration. Minor ITO finding under INSTR-REQ-006: prescriber.recommend returns get_model_for("default") after the router answers, so a provider fallback answer is still labelled with the configured primary model rather than the actual responding model. Preserve that finding for the provider/provenance lane. This frontend round changes neither routing nor configuration nor stored recommendations.

## Edge cases and known limits

Network errors, fast responses, slow responses, keyboard activation, reduced motion and repeated clicks are covered. This local implementation does not deploy changes to the separate hosted instructor site. Duplicate enrolled/LTI identities require a separately reviewed human-run repair; never merge by display name in the UI.

- Shared queries cap evidence, snapshots and decisions. Roster/statistics evidence is capped at 2,000 events class-wide; learner-record statistics read at most 200 and return only 25 ledger rows. Bounded counts/accuracy/last activity do not represent lifetime history; legacy responses remain bounded; WI-25 implements an independent history feed under INSTR-REQ-010 locally, with hosted deployment and live acceptance still pending.
- Median implementation uses the upper middle element for even samples; percentile uses strict-below peers. Ties and sparse cohorts need cautious interpretation.
- Zero evidence is distinct from zero mastery; roster and at-risk use related but different rules. Heatmap/stats cohort means have different denominators.
- Plans navigate via compatibility routes for lesson/practice/flashcards; routing fixes belong to UI scope. Recommendation lifecycle completion and teacher audit immutability remain incomplete; course admission is locally implemented and awaits hosted acceptance.
- No notifications, email dispatch, AGS grade passback or hosted interventions are performed by this feature.

## Contradictions requiring planner resolution

| Locations at source revision | Finding | Proposed resolution (not implemented here) |
| --- | --- | --- |
| `services/api/app/routers/dashboard.py:516` (teacher/student guard wording); `services/api/app/routers/dashboard.py:520` (target membership only); `services/api/app/db/supabase.py:25` (service role) | The guard does not prove caller teaches the course. Role-only dashboard/decision routes can bypass course-scoped RLS. | Locally resolved by INSTR-REQ-009 shared guards and denial tests. Hosted acceptance remains pending. |
| `services/api/app/routers/twin.py:76` (undecided proposals invisible); `packages/db/migrations/0002_rls.sql:106` (self read regardless of status) | Plan API hides suggested/rejected; direct authenticated table policy does not. | Locally resolved by reviewed forward migration 0038 and authenticated replay; Fred FG-6 hosted application/grants and acceptance remain pending. |
| `services/api/app/twin/cohort.py:63` (both roles must be student); `services/api/app/routers/dashboard.py:55` (heatmap enrollment-only filter) | Older heatmap/at-risk cohort helper does not apply the same dual-role exclusion as roster/stats. | Unify student selection in a separately scoped task and add regression tests. |

## Evidence and verification limits

WI-08 / APPROVAL-05 rev 2, Lane P. Source reviewed at `4f3ec29d3f827a1db92e90c4f395947d37744479` on 2026-10-25. `implemented` means present in that source, with the evidence stated per requirement; it is not a claim of deployed acceptance. `partial` identifies an explicit gap. Planned behavior is not inferred from archived plans.

- Local: `cd services/api && uv run pytest -q` — **431 passed**, 30 dependency deprecation warnings, 28.45s.
- Local: `cd services/worker && uv run pytest -q` — **117 passed**, 0.68s.
- Both processes used committed `services/conftest.py`: dotenv disabled, inherited application settings replaced, IPv4/IPv6/DNS blocked. Tests use mocked boundaries; no hosted data or provider calls.
- No browser acceptance, live LTI/Blackboard check, RLS replay, deployment, migration, lint/typecheck/build claim is made by this documentation-only lane. UI evidence is static source review unless stated otherwise.

The API/worker results above are retained historical evidence from the original Lane P source review, not new runs on this integration base. Accepted presentation evidence remains attributed to the existing browser suites and WI-22 evidence; this documentation reconciliation does not rerun or upgrade that acceptance. H12 copy requirements are retained from main; Lane U closeout source is now integrated at `8bc569e`. The explicit labels were checked in source, not reverified in a browser here.

## Reconciliation lineage and ID mapping

Coordinator-approved consolidation onto `8bc569e36b52488b4e05202a90cb18c8ba0db589` after Lane I merge. AUTH remains byte-for-byte main's file; no auth behavior or identity policy is reintroduced here. Accepted INSTR presentation IDs and change-log entries are unchanged. Only the unmerged backend draft IDs from `2062784` are reassigned below; references to that historical revision must use this mapping.

| Draft ID at `2062784` | Final ID | Backend requirement |
| --- | --- | --- |
| INSTR-REQ-001 | INSTR-REQ-003 | Show enrolled students and reviewed skill evidence |
| INSTR-REQ-002 | INSTR-REQ-004 | Explain cohort standing and support needs with evidence |
| INSTR-REQ-003 | INSTR-REQ-005 | Provide cohort trends and an individual record |
| INSTR-REQ-004 | INSTR-REQ-006 | Keep generated recommendations behind a human decision |
| INSTR-REQ-005 | INSTR-REQ-007 | Let instructors author direct actions and learners see only assigned work |
| INSTR-REQ-006 | INSTR-REQ-008 | Enforce staff course ownership before service-role access |

Historical reconciliation at `8bc569e` confirmed the legacy 20/25-row responses, 200-event learner statistics read and 2,000-event class-wide statistics bound. APPROVAL-07 now supersedes the WI-25 paging deferral: the independent cursor feed is locally implemented while those summary/statistics bounds remain unchanged. Active full-history ledgers use loaded-activity wording; inactive bounded surfaces retain H12 labels. Hosted acceptance remains pending.

## Current source revalidation

Static review at `8bc569e36b52488b4e05202a90cb18c8ba0db589` preserves accepted presentation requirements, H12 wording and the mapped backend rules. Source confirms 20/25 returned-event limits, the internal 200-event learner read, class-wide 2,000-event evidence bound, server-owned calculations and unchanged pending-decision behavior. This is documentation validation only; no test, lint, typecheck, build, browser or hosted check was rerun.

Documentation validation for this reconciliation passed: YAML and referenced code/test paths, requirement fields and unique IDs, local links, source line bounds, accepted presentation/changelog preservation, exact draft-to-final mapping, unchanged Lane S requirement, auth byte identity and eight-path ownership. Runtime tests were not rerun.

## APPROVAL-07 local verification boundary

At integrated source `8e51040f1dda4235f9b12ad344da4cd81442e1e9`, reviewed staff guards, H history/error states, M repair tooling and student-read admission are locally integrated. Full API: 1,014; worker: 117; frontend/tour unit: 33; Study component: four. Web lint/typecheck/build and configuration inventory pass. Final integrated synthetic browser verification passes 1,474 assertions; real LTI acceptance is not inferred. Earlier revision-specific evidence retains its recorded attribution. Hosted 0038/0039 application, release, real-pair repair or safe refusal, and live acceptance are separate human gates; this record upgrades no live result.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-27 | Record explicitly authorized CLI current-record counts before accuracy-window edits, with unresolved legacy mapping kept separate | Fred's CLI direction, WI-34 | INSTR-REQ-012 |
| 2026-10-27 | Record Fred's paid hosted proposer confirmation, historical saved source label and minor fallback provenance finding, with no config change | Fred closes drawer item 4, WI-34 | INSTR-REQ-006 |
| 2026-10-27 | Define course rank, explicit evidence windows, neutral zero and counts-only identity gate before learner standing edits | Fred's instructor learner drawer findings and WI-24 identity constraint, WI-34 | INSTR-REQ-012, INSTR-REQ-003/005 retained |
| 2026-10-27 | Record local unified Next implementation and the final sequential browser checks while retaining human/hosted gates | Fred's APPROVAL-09 unified-pager request, WI-34 | INSTR-REQ-010, TWIN-REQ-011 |
| 2026-10-27 | Route assigned Tutor Start to an editable fresh-chat topic draft without changing plan decisions or other destinations | Fred's APPROVAL-09 assigned Tutor Start request, WI-34 | INSTR-REQ-007, TUTOR-REQ-018 |
| 2026-10-27 | Apply the shared single-pager control to instructor learner/Twin views while preserving H errors, keysets and guards | APPROVAL-09 | INSTR-REQ-010; TWIN-REQ-011 |
| 2026-10-25 | Record merged local verification and supersede stale implementation-pending findings; retain hosted gates and bounded summary/statistics limits | APPROVAL-07 coordinator integration; no new behavior | INSTR-REQ-008–011 |
| 2026-10-25 | Define a minimum visible review interval and confirmed recommendation transition before implementation | Fred's direct instructor feedback request in WI-22; supersedes the old optimistic transition | INSTR-REQ-001, INSTR-REQ-002 |
| 2026-10-25 | Write full source-backed feature spec; record incomplete acceptance and contradictions | APPROVAL-05 rev 2 Lane P; handover WI-08 | INSTR-REQ-003 through INSTR-REQ-008 |
| 2026-10-25 | Consolidate accepted presentation requirements and mapped backend draft; preserve H12 windows, WI-25 deferral and revision-specific evidence | Coordinator-approved Lane P reconciliation after APPROVAL-06 Lane I merge; draft `2062784` mapping above | INSTR-REQ-001 through INSTR-REQ-008 |

| 2026-10-25 | Define complete staff course/learner admission and direct recommendation visibility; preserve own-student access and truthful denials | APPROVAL-07 section 1 and Amendments 2–3, WI-26; coordinator spec before Lane SEC implementation | INSTR-REQ-008, INSTR-REQ-009 |

| 2026-10-25 | Define authorized learner-history endpoint and cursor-backed shared ledger; retain bounded statistics and inactive-feed labels | APPROVAL-07 section 2 and Amendment 1, WI-25; coordinator spec before H implementation | INSTR-REQ-010 |

| 2026-10-25 | Require scoped recommendation lookup/learner-bound updates and truthful instructor loading/error/empty states; clarify all direct staff-data policies need review while preserving legitimate non-staff access | APPROVAL-07 section 1 and Amendments 5–6; coordinator before SEC/H implementation | INSTR-REQ-009, INSTR-REQ-011 |
