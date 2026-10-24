---
feature: question-bank
req_prefix: BANK
owner_role: product owner
status: active
code:
  web: apps/web/src/features/bank/
  api: services/api/app/bank/
  worker: [services/worker/app/jobs/bank_build.py, services/worker/app/jobs/embed_bank_items.py]
  db: [packages/db/migrations/0021_question_bank.sql, packages/db/migrations/0024_bank_saturation.sql, packages/db/migrations/0036_bank_lesson_embeddings.sql]
tests:
  - services/api/tests/test_bank.py
  - services/api/tests/test_bank_serving.py
  - services/api/tests/test_lane_g_diagnostic_availability.py
  - services/worker/tests/test_bank_build.py
  - services/worker/tests/test_embed_bank_items.py
  - services/worker/tests/test_handler_bank_chain.py
---

# Reusable question bank

## Purpose
Build reusable course-grounded MCQs in the worker so student serving can select prepared questions without waiting for generation. A per-course bank_serving switch controls the bank path; legacy generation remains a separate supported path where the switch is off.

## Actors and permissions

| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| enrolled student | See safe status and receive eligible items through learning routes | Read raw bank answer keys or worker errors from status |
| instructor/admin | Read status including failure detail for their institution's course | Treat status readiness as proof of content quality |
| worker | Generate, validate, embed and replenish approved-skill items | Build against unreviewed skills |

## Requirements

### BANK-REQ-001: Build only from approved skills and sufficient material
- Rule: use approved course skills and embedded grounded content. Ignore chunks shorter than 200 characters; require at least 1000 usable context characters. Thin or absent material yields no_material and no model call. Initial MCQ target is min(20, 6 * depth, 80); replenishment may grow it to min(6 * depth, 80); readiness/usable are separate, usable begins at 5 prepared MCQs.
- Acceptance: thin content cannot repeatedly spend generation calls; new/retagged content causes depth recomputation; serving can begin at usable depth while the target is still building.
- Status: implemented
- Verified by: worker `test_bank_build.py::test_thin_context_makes_zero_model_calls`, `test_thin_context_policy_flips_to_building_when_context_grows`, `test_new_or_retagged_content_triggers_recompute`; static `_target_from_context` and `bank_config.py`. No real course quality acceptance is claimed.

### BANK-REQ-002: Validate and deduplicate each generated batch
- Rule: generate up to 5 items per batch, clamped to remaining need. Validate schema/choices/answer key and quality filters; retain valid partial batches. Reject exact normalized stems, lexical near-duplicates and semantic cosine >=0.94 against live and newly accepted candidates. Shuffle choices while preserving the correct ID; persist prompt embeddings and generation provenance, not a set_id.
- Acceptance: duplicate candidates do not inflate ready count; valid distinct candidates survive; inserted row count uses returned rows, including insert races.
- Status: implemented
- Verified by: `test_bank_build.py::test_partial_batch_keeps_valid_items_and_rejects_duplicates`, `test_duplicate_stem_hash_and_jaccard_are_rejected`, `test_choice_shuffle_preserves_correct_id_and_varies_position`, `test_bank_candidate_cosine_dedupe_rejects_above_threshold`, `test_bank_candidate_checks_old_rows_missing_embeddings`, `test_bank_insert_payload_never_has_set_id`, `test_insert_count_uses_rows_returned_by_supabase`.

### BANK-REQ-003: Bound and resume bank work fairly
- Rule: conditionally lease one state row for 110 seconds; job budget 100 seconds, at most two concurrent calls, 45-second per-call cap, chain depth at most 12. Breadth-first pending order develops usable coverage across skills. Debounce API wake-up to once per course per 60 seconds; wake-up failure does not fail the caller.
- Acceptance: leased/backoff/no-material rows are skipped; one targeted course does not mutate others; duplicate kicks do not create duplicate progress work.
- Status: implemented
- Verified by: `test_bank_build.py::test_breadth_first_pending_ordering`, `test_pending_excludes_leased_backoff_no_material_and_failed_skill`, `test_targeted_run_queries_and_touches_exactly_one_course`, `test_lease_is_one_conditional_update`; `test_bank.py::test_kick_bank_debounces_second_call`; `test_handler_bank_chain.py`.

### BANK-REQ-004: Stop futile generation and replenish eligible banks
- Rule: transient failures back off in 15/30/60/120/240-minute steps; error after five failures. Permanent model errors stop retries. Two duplicate-dominated zero-valid batches (combined duplicate share >=0.5), with at least five items already ready, mark saturation at current depth. Saturation blocks growth until depth changes. Active-course low-water replenishment adds 15 toward the cap using a 14-day activity window and low-water 10.
- Acceptance: duplicate saturation stops repeated spending; unrelated schema/quality failures keep their error/backoff path; content-depth changes clear saturation; scheduled work includes serving and non-serving courses.
- Status: implemented
- Verified by: `test_bank_build.py::test_duplicate_saturation_triggers_after_two_zero_valid_batches`, `test_non_duplicate_zero_valid_batches_keep_backoff`, `test_saturation_blocks_replenishment_and_depth_change_clears_it`, `test_permanent_model_error_is_recorded_without_retry`, `test_scheduled_run_includes_serving_and_non_serving_courses`, `test_serving_course_replenishment_runs_on_scheduled_build`.

### BANK-REQ-005: Select reusable items without generating or exposing answer keys
- Rule: active, nonretired approved-skill MCQs feed test/diagnostic; Study also accepts native flashcards. Study new selection excludes tracked SRS IDs. Test priority is never tested, then previously incorrect oldest-answer first, then oldest-tested; source-chunk round-robin broadens unseen coverage. Diagnostic uses oldest untested per skill with deterministic created_at/id ordering and paged pool/exposure reads; tested-only pools return no candidate. Selection alone writes no exposures; callers record intentional presentation/answer events.
- Acceptance: selection calls no model; retired/rejected items cannot reappear; tests can flag repeat-tier use; clients receive each learning route's safe shape.
- Status: implemented
- Verified by: `test_bank_serving.py`; `test_learn_routes.py::test_saved_set_counts_only_live_approved_items`, `test_flashcard_due_rows_cannot_reintroduce_retired_items`; static `bank/serving.py`. Study scheduling rules remain in its separate spec.

### BANK-REQ-006: Publish safe progress for enrolled students
- Rule: status lists approved skills only with status, mcqReady/Target, depth and usable; hide lastError from students. Missing state becomes waiting_content. Student must be enrolled; staff course lookup is institution-scoped. Status can wake eligible pending work.
- Acceptance: student cannot read another unenrolled course and does not receive provider error detail; building is true for waiting_content/building states.
- Status: implemented
- Verified by: `test_bank.py::test_student_status_hides_last_error_and_other_course_is_404`; `routers/bank.py::bank_status`.

## API contract

| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| GET /courses/{course_id}/bank/status | Safe progress and bankServing flag | Session; student enrollment or institution staff | 404 outside institution/unenrolled; optional staff lastError |

This feature exposes no raw bank CRUD endpoint. Study/test/diagnostic/lesson delivery endpoints are owned by their feature contracts. `kick_bank` and worker invocation are internal service operations.

## Data
Read courses, approved skills, tagged/embedded content and activity. Write generated_items (origin=bank, active/retired flags, source chunks, normalized hash, embedding), skill_bank_state, course kick timestamps and internal worker_state. Serving reads item_exposures and SRS; exposure recording is tenant/user/item scoped. RLS in 0021 denies authenticated/anon access to skill_bank_state and worker_state. Migration 0023 limits raw generated_items/content/set reads to course teachers or institution admins; students receive server-shaped content. Service-role worker writes bypass RLS and require scoped queries. No migration is altered or run in this documentation lane.

## AI usage (if any)
Worker uses the configured OpenRouter bank model, structured schema, 8192 completion cap, 3072 reasoning cap and rotated course context capped at 12,000 characters. Embeddings are 1024-dimensional and reused/backfilled before cosine matching. Work budgets, dedupe and saturation control cost; configured model IDs/costs are not inferred as live settings. Sanitization upstream covers emails and name-patterns only. Error reasons may be derived from provider responses; logging privacy needs separate review (finding below).

## Edge cases and known limits
- ready is not the same as usable: saturation may lower the effective target; unusable status may be error/no_material instead of building.
- Status is not a read-only DB operation: it may debounce/wake work. It does not itself generate questions or grade a learner.
- Old rows without embeddings need backfill; 0036 supports shared item/lesson-step embeddings. Matching quality needs real reviewed samples.
- Bank status staff access checks institution, not instructor enrollment. Do not describe it as the stricter course-teacher policy.
- Retakes, XP, attempt identity and Study memory are outside this feature's requirements.

## Contradictions requiring planner resolution

| Locations at source revision | Finding | Proposed resolution (not implemented here) |
| --- | --- | --- |
| `AGENTS.md:36` (de-identify before model calls); `services/worker/app/jobs/bank_build.py:189` and `services/worker/app/model_errors.py:20` (provider-derived reason) | Worker failure logging retains a provider-derived reason under error_body, rather than the tutor lane's metadata-only pattern. It is not proven free of unrelated reflected content. | Review/redact worker logging in its own authorized task; do not claim comprehensive privacy from current sanitizer. |
| `packages/db/migrations/0023_course_scoped_staff_reads.sql:13`; `services/api/app/routers/bank.py:17` | Raw-table RLS is teacher-scoped; status API admits any same-institution staff. | Product/security owner decides intended status visibility; add teacher-gate tests if access should match raw-table policy. |

## Evidence and verification limits

WI-08 / APPROVAL-05 rev 2, Lane P. Source reviewed at `4f3ec29d3f827a1db92e90c4f395947d37744479` on 2026-10-25. `implemented` means present in that source, with the evidence stated per requirement; it is not a claim of deployed acceptance. `partial` identifies an explicit gap. Planned behavior is not inferred from archived plans.

- Local: `cd services/api && uv run pytest -q` — **431 passed**, 30 dependency deprecation warnings, 28.45s.
- Local: `cd services/worker && uv run pytest -q` — **117 passed**, 0.68s.
- Both processes used committed `services/conftest.py`: dotenv disabled, inherited application settings replaced, IPv4/IPv6/DNS blocked. Tests use mocked boundaries; no hosted data or provider calls.
- No browser acceptance, live LTI/Blackboard check, RLS replay, deployment, migration, lint/typecheck/build claim is made by this documentation-only lane. UI evidence is static source review unless stated otherwise.

## Current source revalidation

Reconciliation source base: `8bc569e36b52488b4e05202a90cb18c8ba0db589` (integrated I, G and U closeout). Rechecked worker build/serving contracts against integrated source. Lane G now batches oldest-untested Diagnostic selection by up to 100 skills, paginates pool/exposure reads in 500-row pages and orders ties by item ID; it still does not fall back to tested items or write exposures. Diagnostic eligibility and actionable counts belong to the coordinator-owned DIAG-REQ-009–011; this spec does not redefine them. No question generation or hosted query was performed. Historical test results above remain tied to the original review revision and were not rerun or upgraded.

Documentation validation for this reconciliation passed: YAML and referenced code/test paths, requirement fields and unique IDs, local links, source line bounds, accepted presentation/changelog preservation, exact draft-to-final mapping, unchanged Lane S requirement, auth byte identity and eight-path ownership. Runtime tests were not rerun.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-25 | Write full source-backed feature spec; record incomplete acceptance and contradictions | APPROVAL-05 rev 2 Lane P; handover WI-08 | BANK-REQ-001 through BANK-REQ-006 |
| 2026-10-25 | Revalidate source contracts on integrated main; retain historical test limits | Coordinator-approved Lane P reconciliation; APPROVAL-06 | BANK requirements above |
