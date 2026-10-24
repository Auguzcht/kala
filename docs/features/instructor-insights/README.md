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
| instructor | Inspect their class, generate proposals and decide/author actions | Access arbitrary courses merely by guessing IDs (intended; enforcement gap below) |
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
- Acceptance: assigned text/note appears on From your instructor; empty plan hides the card; completed history can display if present. Invalid intervention kind returns 400.
- Status: partial
- Verified by: static `dashboard.py::create_intervention`, `twin.py::learning_plan`, `features/plan/components/InstructorPlan.tsx`. No full workflow/browser test or automatic completion behavior is claimed.

### INSTR-REQ-008: Enforce staff course ownership before service-role access
- Rule: course staff must teach the requested course; institution admins are institution-scoped. A target learner must be an enrolled student. Apply this before all reads/writes, including recommendation decisions.
- Acceptance: student gets 403; instructor outside course and cross-institution requests get 404 before data access; decisions cannot alter an unowned course.
- Status: partial
- Verified by: `test_dashboard_routes.py::test_heatmap_requires_instructor` proves role denial only; approved-skill rejection has a teacher gate. `_assert_teaches_student` only checks the target learner's membership; it does not check caller enrollment. Most dashboard endpoints use require_role plus data filters rather than this full requirement. Enforcement is an explicit unresolved finding, not asserted as complete.

## API contract

### Accepted presentation boundary

| Method/path | Purpose | Auth | Change |
| --- | --- | --- | --- |
| PATCH /dashboard/{course_id}/skills/{skill_id}/review | Approve/reject a proposed skill | Existing instructor/admin course gate | None |
| PATCH /dashboard/{course_id}/recommendations/{rec_id} | Record a confirmed recommendation decision | Existing instructor/admin course gate | None |

### Backend contract
| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| GET /dashboard/{course_id}/roster | Class roster rollups | Instructor/admin | Institution-scoped data; teacher-gate gap |
| GET /dashboard/{course_id}/stats | Cohort KPIs/charts | Instructor/admin | Bounded histories; teacher-gate gap |
| GET /dashboard/{course_id}/heatmap | Approved-skill cells | Instructor/admin | Optional module_ref; teacher-gate gap |
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
Read enrollments/users/profiles, skills, mastery_state, evidence_events and readiness_snapshots; write recommendations via API service role. RLS 0002 allows self/course teachers/institution admins to read recommendations; 0009 allows teacher/admin insert/update. The own-student RLS read policy does not filter recommendation status, so hiding undecided proposals is currently a plan-API boundary, not a proven direct-DB confidentiality boundary. Service-role access bypasses RLS; missing caller course gates are material.

The presentation table retains its accepted access description. Actual service-role enforcement remains partial under INSTR-REQ-008; a successful role gate is not proof that the caller teaches the course.

## AI usage (if any)

### Presentation amendment
None added. Reviewing an existing proposal or recommendation does not introduce a model call.

### Backend usage
`ai/prescriber.py::_model_context` allow-lists pseudonym, aggregate numbers and skill name/Bloom/estimate/attempts; no display name/email/LMS ID/raw event row is included. Shared router uses the configured default model; malformed/unavailable output falls back to deterministic heuristic suggestions with source=heuristic. Cleanup bounds title/rationale/evidence counts and numeric confidence/gain. This schema boundary is narrower than raw-record serialization, but skill text still relies on limited shared de-identification. No accuracy guarantee is implied by numeric confidence.

## Edge cases and known limits

Network errors, fast responses, slow responses, keyboard activation, reduced motion and repeated clicks are covered. This local implementation does not deploy changes to the separate hosted instructor site. Duplicate enrolled/LTI identities require a separately reviewed human-run repair; never merge by display name in the UI.

- Shared queries cap evidence, snapshots and decisions. Roster/statistics evidence is capped at 2,000 events class-wide; learner-record statistics read at most 200 and return only 25 ledger rows. Bounded counts/accuracy/last activity do not represent lifetime history; full-history paging is deferred under WI-25.
- Median implementation uses the upper middle element for even samples; percentile uses strict-below peers. Ties and sparse cohorts need cautious interpretation.
- Zero evidence is distinct from zero mastery; roster and at-risk use related but different rules. Heatmap/stats cohort means have different denominators.
- Plans navigate via compatibility routes for lesson/practice/flashcards; routing fixes belong to UI scope. Recommendation lifecycle completion, teacher audit immutability and course gate hardening remain incomplete.
- No notifications, email dispatch, AGS grade passback or hosted interventions are performed by this feature.

## Contradictions requiring planner resolution

| Locations at source revision | Finding | Proposed resolution (not implemented here) |
| --- | --- | --- |
| `services/api/app/routers/dashboard.py:516` (teacher/student guard wording); `services/api/app/routers/dashboard.py:520` (target membership only); `services/api/app/db/supabase.py:25` (service role) | The guard does not prove caller teaches the course. Role-only dashboard/decision routes can bypass course-scoped RLS. | Authorize a security lane to add shared course gates and denial tests across all dashboard paths. |
| `services/api/app/routers/twin.py:76` (undecided proposals invisible); `packages/db/migrations/0002_rls.sql:106` (self read regardless of status) | Plan API hides suggested/rejected; direct authenticated table policy does not. | Review Data API exposure and decide whether status filtering must be enforced with a forward RLS change; no hosted check claimed. |
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

Static reconciliation review confirms returned Twin evidence is capped at 20, learner-record statistics read at most 200 events and serialize 25 ledger rows, and cohort roster/statistics evidence reads are capped at 2,000 class-wide. H12 labels remain “Last 20 events”, “Last 25 events” and “Based on recent activity”; full-history paging stays deferred under [WI-25](../../work/handover-2026/work-items/WI-25-full-history-evidence-paging.md). These are bounded-window counts, not lifetime totals.

## Current source revalidation

Static review at `8bc569e36b52488b4e05202a90cb18c8ba0db589` preserves accepted presentation requirements, H12 wording and the mapped backend rules. Source confirms 20/25 returned-event limits, the internal 200-event learner read, class-wide 2,000-event evidence bound, server-owned calculations and unchanged pending-decision behavior. This is documentation validation only; no test, lint, typecheck, build, browser or hosted check was rerun.

Documentation validation for this reconciliation passed: YAML and referenced code/test paths, requirement fields and unique IDs, local links, source line bounds, accepted presentation/changelog preservation, exact draft-to-final mapping, unchanged Lane S requirement, auth byte identity and eight-path ownership. Runtime tests were not rerun.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-25 | Define a minimum visible review interval and confirmed recommendation transition before implementation | Fred's direct instructor feedback request in WI-22; supersedes the old optimistic transition | INSTR-REQ-001, INSTR-REQ-002 |
| 2026-10-25 | Write full source-backed feature spec; record incomplete acceptance and contradictions | APPROVAL-05 rev 2 Lane P; handover WI-08 | INSTR-REQ-003 through INSTR-REQ-008 |
| 2026-10-25 | Consolidate accepted presentation requirements and mapped backend draft; preserve H12 windows, WI-25 deferral and revision-specific evidence | Coordinator-approved Lane P reconciliation after APPROVAL-06 Lane I merge; draft `2062784` mapping above | INSTR-REQ-001 through INSTR-REQ-008 |
