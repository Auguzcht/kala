---
feature: lessons
req_prefix: LESSON
owner_role: product owner
status: active
code:
  web: apps/web/src/features/lessons/
  api: services/api/app/routers/lessons.py
  worker: [services/worker/app/jobs/assign_lesson_checks.py, services/worker/app/jobs/item_generation.py]
  db: [packages/db/migrations/0008_learn_loop_v2.sql, packages/db/migrations/0020_async_lesson_checks.sql, packages/db/migrations/0036_bank_lesson_embeddings.sql]
tests:
  - services/api/tests/test_lessons.py
  - services/api/tests/test_lessons_route_scoping.py
  - services/api/tests/test_lesson_reclaim.py
  - services/api/tests/test_retired_lesson_checks.py
  - services/worker/tests/test_assign_lesson_checks.py
  - services/worker/tests/test_lesson_matching.py
---

# Guided lessons and comprehension checks

## Purpose
Guided lessons teach an approved course skill through persisted teaching steps and server-graded checks. Students read one step at a time and can ask text-only, step-scoped follow-ups; reading alone is not mastery evidence.

## Actors and permissions

| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| authenticated learner | Open an approved skill's lesson, answer its linked check and ask about the current step | Choose mastery or grade another course's step through a forged URL |
| worker | Assign prepared bank checks or finish queued legacy checks | Replace already assigned checks during ordinary assignment |
| instructor | Influence course skills/material through their own feature | Treat reading completion as a graded outcome |

## Student read admission

Lesson-retrieval GET follows [AUTH-REQ-007](../lti-auth/README.md#auth-req-007-require-existing-course-enrollment-on-student-reads) before existing lesson generation, persistence or assignment work. Enrolled teaching behavior and check-submission methods remain unchanged. Admission is implemented locally and verified by the 116-case AUTH-REQ-007 route/import matrix and strict AST scope proof; hosted deployment and live acceptance remain pending.

## Requirements

### LESSON-REQ-001: Persist and reuse teaching content per approved skill
- Rule: GET validates institution/course/approved skill, returns stored ready content, or creates a shell and generates an outline (at most six steps) followed by ordered teaching content. Failed/nonready shells can be reclaimed; missing asynchronous checks on a ready lesson must not trigger regeneration.
- Acceptance: reopening ready content does not regenerate; concurrent insert conflicts reread the winner; steps persist in outline order despite parallel content completion; failure is marked failed for retry.
- Status: implemented
- Verified by: `test_lessons.py::test_get_or_generate_returns_stored_lesson_without_regenerating`, `test_ready_lesson_fast_path_selects_guided_lessons_only_once`, `test_ready_lesson_with_null_check_is_never_reclaimed`, `test_generation_persists_steps_in_position_order_even_when_parallel_completion_is_out_of_order`; `test_lesson_reclaim.py`.

### LESSON-REQ-002: Produce renderable teaching even when generation is thin
- Rule: retrieve four relevant course chunks; outline uses reasoning role with configured reasoning fallback and defaults to a single skill-named step on invalid output. Step content uses reasoning role, at most two attempts; ask for two detail points and 200 characters but retain a thin second result with warning, or deterministic content on failure.
- Acceptance: invalid output still gives a renderable lesson; invalid Bloom falls back; thin output is retried once, not indefinitely.
- Status: partial
- Verified by: `test_lessons.py::test_outline_falls_back_to_single_step_on_garbage`, `test_outline_passes_the_reasoning_fallback`, `test_step_content_uses_the_lesson_reasoning_role`, `test_step_content_retries_thin_output_once`, `test_step_content_keeps_thin_second_result_with_warning`. Real teaching quality and fully grounded fallback are not established by these tests.

### LESSON-REQ-003: Assign asynchronous checks without revealing their answer keys
- Rule: teaching steps initially have null check_item_id. Bank-serving courses wake resumable matching; other courses enqueue legacy lesson item jobs after step insertion. Reads return only active check items whose skill remains approved, stripping correct-choice/explanation. Pending checks are nullable and do not make ready teaching invalid.
- Acceptance: GET never writes a newly generated check inline; retired/rejected checks are hidden; ready lesson reads can kick assignment without rewriting content.
- Status: implemented
- Verified by: `test_lessons.py::test_generation_persists_steps_with_null_check_and_enqueues_it`, `test_assembly_kicks_check_assignment_without_writing_checks`; `test_retired_lesson_checks.py::test_lesson_check_read_filters_retired_and_rejected_skill_items`.

### LESSON-REQ-004: Match bank checks to step meaning and preserve assignments
- Rule: worker holds a per-lesson 180-second lease. Embed missing step text (summary/detail, optional title) and active practice-bank prompts in 1024 dimensions. Greedily pick highest cosine with a 0.05 equal-Bloom bonus, minimum score 0.35; remove near-duplicate candidates at cosine >=0.85. Fill null assignments only; checkpoint each step and reuse embeddings on resume.
- Acceptance: semantic best pair wins; weak candidates leave a step unassigned; an existing assignment is kept and its duplicates excluded; another worker's live lease prevents work.
- Status: implemented
- Verified by: `test_assign_lesson_checks.py` and `test_lesson_matching.py`, including `test_assignment_checkpoints_each_step_and_is_resumable`, `test_missing_step_and_item_embeddings_are_saved_and_reused`, `test_assignment_does_not_run_when_another_worker_holds_the_lease`, `test_minimum_score_floor_leaves_step_unassigned`.

### LESSON-REQ-005: Grade linked checks under the correct course and tenant
- Rule: POST proves step/check relation, lesson course/institution ownership and graded item's course before writes. Grade server-side; both correct and incorrect attempts append tutor evidence, move tracer, update legacy SRS and record answered/tested exposure. Correct returns advance=true plus stored explanation; incorrect advance=false with a nudge that does not reveal the stored answer key.
- Acceptance: cross-course or mismatched item returns 404 before evidence; only a correct response unlocks a checked step in the UI; reward is recomputed from saved state.
- Status: partial
- Verified by: `test_lessons_route_scoping.py::test_check_belonging_to_a_different_course_is_rejected`, `test_check_belonging_to_this_course_is_accepted`, `test_check_item_mismatch_still_404s`; static `routers/lessons.py::submit_check`. No idempotency key/transaction wraps these sequential writes; retried submissions can duplicate evidence.

### LESSON-REQ-006: Keep step interaction local and card-scoped
- Rule: the UI renders one explanation/check slot, opens checks from Continue, requires result.advance before advancing a checked step, and allows a teaching-only step to continue when no check exists. Retry clears prior answer/explanation state. Follow-ups use the text-only ComposeDock and stateless tutor asks; they do not create saved conversations or attachments.
- Presentation: Teaching, reinforcement checks and graded feedback use the shared content/dock column in DESIGN-REQ-002. Their scroll region spans the full available page surface so its native scrollbar stays at the browser’s right edge, outside the centered card column. Apply inherited gutters once, preserve fixed session bar/dock, bottom clearance, check/thread state and all tour anchors. Verify overflowing teaching, question and graded feedback at 375px/1440px, including persistent scrollbars, with no layout-triggered write.
- Acceptance: missing check does not trap the learner; a miss offers Try again; question context names the current step/check. Reopening does not claim durable per-student lesson progression.
- Status: implemented
- Verified by: static `LessonChat.tsx::openCheck`, `advanceStep`, `retry` and its dock wiring; `use-lessons.ts` polls every 2 seconds only while status=generating and invalidates twin/next-up/gamification after checks. No browser interaction test in the original lane. APPROVAL-09 scrollbar correction: final-ui-pass.browser.mjs passes 238 assertions, including overflowing teaching/check/feedback and persistent page-edge scrollbars at 375px/1440px. Card/dock edges are 16–359px and 344–1096px respectively, matching within 1px. Layout causes zero writes, with one explicit synthetic grading request from choosing an answer. Live acceptance remains pending.

### LESSON-REQ-007: Bound first-open generation within an explicit request deadline
- Rule: planned whole-request budget must include RAG, outline, step generation, persistence and response shaping.
- Acceptance: slow dependencies cannot leave the first open exceeding the configured API deadline; budget failure is student-safe and retryable.
- Status: planned
- Verified by: not-run; [WI-14](../../work/handover-2026/work-items/WI-14-lesson-request-budget.md) owns this gap. Current generation is inline and has no whole-request deadline.

## API contract

| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| GET /lessons/{course_id}/skill/{skill_id} | Load or generate shared lesson | Session; approved skill in course/institution | 404 absent/unapproved; ready reuse; first GET writes/generates |
| POST /lessons/{course_id}/steps/{step_id}/check | Grade linked MCQ | Session; relation + course/institution proof | Body item_id, choice_id, latency_ms=0, hints_used=0; 404 invalid relation/item; result correct/explanation/advance/mastery/reward |

GET response: lessonId, skillId, moduleRef, title, status, ordered steps; each step has id, position, summary, detailPoints, misconception, keyTakeaway, bloomLevel and nullable safe check. UUID path shape failures return 404; model/Pydantic validation errors follow shared handling. item_id/choice_id are strings, not UUID body dependencies.

## Data
Service role writes guided_lessons/steps, queue/kick state, evidence_events, mastery_state, srs_state and item_exposures; reads skills, generated_items and content. Guided lesson RLS (0008) allows same-institution reads through the parent lesson; steps inherit tenancy through lesson_id rather than carrying institution_id. Check answer keys stay in server-readable generated_items under 0023 staff RLS; API shapes the student response. No student-specific completion table exists in this flow.

## AI usage (if any)
RAG embeds the skill query and retrieves course chunks; reasoning outline/step calls use 1536 output-token caps each. Provider fallback is explicit on outline, not on step calls. Thin-step retry can multiply first-open cost. Bank assignment uses embeddings only; legacy check generation runs in the worker. Model boundaries use the shared limited email/name-pattern sanitizer; this is not comprehensive anonymization. Tutor follow-up deadlines belong to the tutor/AI specs.

## Edge cases and known limits
- No retrieved chunks falls back to skill name, so a renderable result is not proof of course grounding.
- No atomic generation claim protects against every simultaneous nonready-shell reclaim; tests cover selected replay/reclaim races, not live concurrency.
- Check assignment reads up to 1000 active items and preserves existing links. Reassigning legacy poor matches and regenerating thin teaching remain WI-11 carry-over, not completed here.
- A ready response with pending checks is cached for five minutes; frontend polling is tied to generating status, not missing check IDs. Background completion may not appear immediately.
- Check grading also filters nonretired items and approved skills in `learn/items.py::grade`; stale linked checks fail rather than restoring hidden items. Choice IDs are compared to the saved key without a separate choices-membership query.

## Contradictions requiring planner resolution

| Locations at source revision | Finding | Proposed resolution (not implemented here) |
| --- | --- | --- |
| `services/api/app/routers/lessons.py:6` and `services/api/app/routers/lessons.py:65` (passing writes evidence); `services/api/app/routers/lessons.py:109` (unconditional evidence) | Both misses and passes write evidence, whereas introductory wording suggests passes only. | Correct comments to match the graded-attempt rule; do not suppress incorrect evidence without a spec decision. |
| `services/api/app/learn/lessons.py:15` (checks described with teaching generation); `services/api/app/learn/lessons.py:311` (asynchronous checks) | Legacy module prose can imply inline checks. | Update module lifecycle description; preserve asynchronous contract/tests. |
| `AGENTS.md:33`; `packages/db/migrations/0008_learn_loop_v2.sql:123` (step definition) | Lesson-step tenancy is inherited through parent; steps lack row-local institution_id. | Record deliberate schema exception or plan forward migration centrally. |

## Evidence and verification limits

WI-08 / APPROVAL-05 rev 2, Lane P. Source reviewed at `4f3ec29d3f827a1db92e90c4f395947d37744479` on 2026-10-25. `implemented` means present in that source, with the evidence stated per requirement; it is not a claim of deployed acceptance. `partial` identifies an explicit gap. Planned behavior is not inferred from archived plans.

- Local: `cd services/api && uv run pytest -q` — **431 passed**, 30 dependency deprecation warnings, 28.45s.
- Local: `cd services/worker && uv run pytest -q` — **117 passed**, 0.68s.
- Both processes used committed `services/conftest.py`: dotenv disabled, inherited application settings replaced, IPv4/IPv6/DNS blocked. Tests use mocked boundaries; no hosted data or provider calls.
- No browser acceptance, live LTI/Blackboard check, RLS replay, deployment, migration, lint/typecheck/build claim is made by this documentation-only lane. UI evidence is static source review unless stated otherwise.

## Current source revalidation

Reconciliation source base: `8bc569e36b52488b4e05202a90cb18c8ba0db589` (integrated I, G and U closeout). Rechecked lesson generation, grading, assignment and UI source against integrated source. The UI now uses the shared Spinner during pending Hint/Explain requests; lesson progression, text-only stateless dock behavior, server grading and request-budget limits are unchanged. No lesson generation or browser acceptance was run. Historical test results above remain tied to the original review revision and were not rerun or upgraded.

Documentation validation for this reconciliation passed: YAML and referenced code/test paths, requirement fields and unique IDs, local links, source line bounds, accepted presentation/changelog preservation, exact draft-to-final mapping, unchanged Lane S requirement, auth byte identity and eight-path ownership. Runtime tests were not rerun.

## APPROVAL-07 local verification boundary

At integrated source `8e51040f1dda4235f9b12ad344da4cd81442e1e9`, reviewed staff guards, H history/error states, M repair tooling and student-read admission are locally integrated. Full API: 1,014; worker: 117; frontend/tour unit: 33; Study component: four. Web lint/typecheck/build and configuration inventory pass. Final integrated synthetic browser verification passes 1,474 assertions; real LTI acceptance is not inferred. Earlier revision-specific evidence retains its recorded attribution. Hosted 0038/0039 application, release, real-pair repair or safe refusal, and live acceptance are separate human gates; this record upgrades no live result.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-28 | Extend the outer-scroll/shared-column rule explicitly to Lesson teaching, reinforcement checks and feedback before the scrollbar correction | Fred’s APPROVAL-09 screenshot and direct request, WI-34 | LESSON-REQ-006; DESIGN-REQ-002 |
| 2026-10-25 | Record merged local verification and supersede stale implementation-pending findings; retain hosted gates and bounded summary/statistics limits | APPROVAL-07 coordinator integration; no new behavior | AUTH-REQ-007 |
| 2026-10-25 | Require existing enrollment admission on inventoried student GETs; preserve staff, mutations and enrolled processing | APPROVAL-07 Amendment 7; coordinator spec before follow-up implementation | AUTH-REQ-007; WI-26 |
| 2026-10-25 | Write full source-backed feature spec; record incomplete acceptance and contradictions | APPROVAL-05 rev 2 Lane P; handover WI-08 | LESSON-REQ-001 through LESSON-REQ-007 |
| 2026-10-25 | Revalidate source contracts on integrated main; retain historical test limits | Coordinator-approved Lane P reconciliation; APPROVAL-06 | LESSON requirements above |
