---
feature: skills
req_prefix: SKILL
owner_role: product owner
status: active
code:
  web: apps/web/src/features/instructor/components/SkillReviewPanel.tsx
  api: services/api/app/routers/dashboard.py
  worker: [services/worker/app/skill_proposer.py, services/worker/app/jobs/tag_recompute.py]
  db: [packages/db/migrations/0007_skill_proposals.sql, packages/db/migrations/0022_embedding_tags.sql, packages/db/migrations/0025_reject_approved_skill_retire_bank_items.sql]
tests:
  - services/api/tests/test_skill_proposer.py
  - services/api/tests/test_dashboard_routes.py
  - services/api/tests/test_tag_content.py
  - services/worker/tests/test_skill_proposer.py
  - services/worker/tests/test_tag_recompute.py
---

# Course skills and content tagging

## Purpose
Kala extracts assessable course skills from course material, links content to approved skills and gives instructors a review queue. Reviewed skill identity is shared by lessons, the question bank, diagnostic and the twin; proposals are not automatically student-facing, except explicit high-confidence reuse of a previously approved institutional skill.

## Actors and permissions

| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| student | Use approved skills through learning surfaces | Review, reject or detach skills |
| instructor/admin | Review proposals, inspect inherited skills, detach or reject them | Treat a model proposal as a validated learning outcome without review/reuse rules |
| worker | Propose, ground, deduplicate and tag | Make arbitrary novel proposals approved without the defined canonical match |

Course authorization is incomplete for several review routes; see the finding below. Role gates are not equivalent to proof that the instructor teaches this course.

## Requirements

### SKILL-REQ-001: Queue and resume proposal work from stored course content
- Rule: staff proposal requests persist queued worker_state before waking the worker. Worker proposal state is queued/running/done/failed, resumes module/window cursors and stamps last_skill_seed_at only when all modules finish. No course-description fallback substitutes for stored material.
- Acceptance: interrupted module work resumes after completed windows; budget exhaustion defers further calls; a permanent model error records failed status. The dashboard shows persisted proposalStatus.
- Status: implemented
- Verified by: `test_dashboard_routes.py::test_propose_persists_queued_before_worker_invoke`, `test_proposed_skills_returns_persisted_proposal_status`; worker `test_skill_proposer.py::test_window_cursor_resumes_after_mid_module_kill`, `test_time_budget_guard_chains_without_starting_model_call`, `test_last_seed_timestamp_only_after_all_modules_complete`, `test_permanent_model_error_sets_failed_proposal_status`.

### SKILL-REQ-002: Retain assessable, grounded subject skills
- Rule: validate names, Bloom levels and bounded blueprint weight (0.5..2.0); discard logistics proposals. Ground candidates against embedded module content using similarity 0.544, minimum chunk length 200 and usable context 1000 characters. Insufficient support is not promoted as a fully grounded result. Worker near-duplicate cutoff is 0.90; overlap with approved course skills at that cutoff is dropped.
- Acceptance: malformed/logistics candidates are discarded; thin/ungrounded proposals are handled conservatively; within-window duplicates merge and later windows see persisted earlier results. The legacy API parser additionally rejects vague names; the worker only checks nonempty name/Bloom/category.
- Status: partial
- Verified by: API `test_skill_proposer.py::test_parse_drops_vague_and_malformed_proposals`, `test_parse_drops_logistics_proposals_even_if_prompt_is_ignored`, `test_grounding_drops_ungrounded_and_stages_thin`, `test_proposer_grounding_constants_match_worker_config`; worker `test_within_window_near_duplicates_merge_and_log_dropped_name`, `test_proposal_overlapping_approved_course_skill_is_dropped`.

### SKILL-REQ-003: Make institutional canonical reuse visible and reversible
- Rule: a cross-course match >=0.92 may inherit an approved canonical skill's wording/Bloom/weight and record canonical_skill_id; >=0.82 supplies a possible-duplicate review hint. Other candidates remain proposed. Detach returns an approved canonical match to proposed, clears canonical/review metadata and keeps it off approved-only learner surfaces until reviewed.
- Acceptance: inherited skills appear in auto-matched; only inherited approved rows detach; a nonmatching row returns 404.
- Status: implemented
- Verified by: `test_skill_proposer.py::test_seed_auto_approves_on_strong_match`, `test_seed_flags_possible_duplicate_in_review_band`; `test_dashboard_routes.py::test_list_auto_matched_returns_inherited_skills`, `test_detach_sends_auto_matched_skill_back_to_proposed`, `test_detach_404s_when_skill_is_not_auto_matched`. Worker `_match`/threshold code reviewed separately; API seed tests alone do not prove worker parity.

### SKILL-REQ-004: Persist human review and retire rejected skill bank items
- Rule: proposed rows accept approved/rejected plus optional edits on approval; store reviewer/time and clamp weight. Approval wakes bank building. Rejecting an approved skill uses one service-only RPC to change status and retire active bank items atomically; non-admin callers of that operation must teach the course.
- Acceptance: bad decision status returns 400; missing/non-proposed review target 404; approved rejection returns retiredItems and no half-retired result.
- Status: partial
- Verified by: static `dashboard.py::review_proposed_skill`; `test_dashboard_routes.py::test_reject_approved_skill_is_course_staff_only_and_uses_atomic_rpc`, `test_reject_approved_skill_requires_staff_role`; migration 0025 inspected, not executed by this lane. Ordinary proposal review lacks the same teacher gate.

### SKILL-REQ-005: Recompute content tags by embedding with an ambiguity margin
- Rule: active embedding-tag recomputation compares embedded chunks against approved course skills at threshold 0.544 and minimum top-two margin 0.03. Recompute the full course to remove obsolete mappings and fill gaps; no chat model is invoked by tag_recompute. Missing skill embeddings are reported rather than invented.
- Acceptance: below-threshold/ambiguous chunks are counted; approved-skill changes are reflected by a repeatable RPC; manual retag requires staff/course authorization.
- Status: implemented
- Verified by: `services/worker/tests/test_tag_recompute.py`; static `app/tagging.py`, `worker/app/jobs/tag_recompute.py`, migration `0022_embedding_tags.sql`. Old `test_tag_content.py` tests the retained legacy model tagger, not this active embedding path. Real local SQL execution is outside this doc lane's evidence.

## API contract

| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| POST /courses/{course_id}/skills/propose | Persist queued state and wake worker | Instructor/admin | 202; role-only gate currently |
| GET /dashboard/{course_id}/skills/proposed | Queue plus proposalStatus | Instructor/admin | proposed rows only; absent/unrecognized state normalizes to done |
| GET /dashboard/{course_id}/skills/auto-matched | Inherited approved skills | Instructor/admin | canonical_skill_id nonnull |
| PATCH /dashboard/{course_id}/skills/{skill_id}/review | Review/edit proposal | Instructor/admin | Body status, optional name/bloom_level/blueprint_weight; 400/404 |
| POST /dashboard/{course_id}/skills/{skill_id}/reject-approved | Reject and retire bank items | Course instructor or institution admin | 404 on denied/missing; atomic RPC |
| PATCH /dashboard/{course_id}/skills/{skill_id}/detach | Reopen canonical match for review | Instructor/admin | 404 unless inherited and approved |
| POST /courses/{course_id}/content/retag | Recompute embedding tags | Course instructor or institution admin | tagged/belowThreshold/ambiguous counters |

Review pending/error presentation follows [INSTR-REQ-001](../instructor-insights/README.md#instr-req-001-keep-skill-review-feedback-visible); this spec does not redefine the accepted 350ms feedback interval.

## Data
Read/write skills and content_items tag fields; read courses/material; worker_state stores proposal/cursor operational state. Rejection also updates generated_items.retired_at. `skills_read` (0002) permits same-institution reads, not approved-only reads; approved-only student behavior is enforced in API learning queries. `worker_state` is not browser-readable. Service-role writers bypass RLS; migration 0025 revokes rejection RPC execution from public/anon/authenticated and grants service_role only. Applied migrations remain unchanged.

## AI usage (if any)
Worker proposer uses configured bank model with structured JSON, 8192 completion cap and reasoning budget capped at 3072; bounded per-call work and resumable windows control cost. Proposal and skill embeddings use the configured embedding provider with 1024-dimensional storage. Course material is sanitized on ingest with the limited email/name-pattern stripper; this does not guarantee arbitrary PII removal. Active embedding tagging has no LLM call. Legacy API proposer/tagger modules remain and differ from the worker; retain that distinction when interpreting tests.

## Edge cases and known limits
- Canonical auto-approval reuses a prior human-approved skill; it is an explicit exception to individual per-course review.
- Editing approved proposal wording does not visibly recompute its embedding in the review route; confirm stale-embedding handling before relying on semantic parity.
- Detach does not retire old items; approved-only joins hide them while proposed. Re-approval/reassignment needs deliberate review.
- Proposed Bloom/name fields are plain strings at the route boundary; DB constraints/model parsing cover different cases. Do not claim comprehensive Zod/Pydantic constraint equivalence.
- Full pipeline acceptance still requires real course material, model output review and local SQL integration evidence. Worker name parsing lacks the API parser's vague-name filter; a prompt instruction to use assessable verbs is not code enforcement.

## Contradictions requiring planner resolution

| Locations at source revision | Finding | Proposed resolution (not implemented here) |
| --- | --- | --- |
| `services/api/app/routers/dashboard.py:282` (nothing proposed reaches learners before human approval); `services/api/app/routers/dashboard.py:320` (canonical auto-approval); `services/worker/app/skill_proposer.py:369` (reuse branch) | Absolute review-gate wording omits canonical reuse. | Amend that comment/copy to the explicit reuse exception after product confirmation. |
| `packages/db/migrations/0023_course_scoped_staff_reads.sql:6` (teacher-scoped content); `services/api/app/routers/diagnostic.py:176` and `services/api/app/routers/dashboard.py:340` (role-only proposal/review); `services/api/app/db/supabase.py:25` (privileged client) | API review/proposal routes do not consistently enforce the course boundary implied by staff RLS and course-teacher intent. | Plan course/tenant gate tests and apply shared authorization in a separately owned security task. |
| `services/api/app/ai/skill_proposer.py:410` (API in-batch annotation); `services/worker/app/skill_proposer.py:167` (worker deduplication) | Legacy/API seed tests retaining duplicate candidates do not establish the worker's merge behavior. | Keep tests labeled by path; decide whether to consolidate or retire legacy paths separately. |

## Evidence and verification limits

WI-08 / APPROVAL-05 rev 2, Lane P. Source reviewed at `4f3ec29d3f827a1db92e90c4f395947d37744479` on 2026-10-25. `implemented` means present in that source, with the evidence stated per requirement; it is not a claim of deployed acceptance. `partial` identifies an explicit gap. Planned behavior is not inferred from archived plans.

- Local: `cd services/api && uv run pytest -q` — **431 passed**, 30 dependency deprecation warnings, 28.45s.
- Local: `cd services/worker && uv run pytest -q` — **117 passed**, 0.68s.
- Both processes used committed `services/conftest.py`: dotenv disabled, inherited application settings replaced, IPv4/IPv6/DNS blocked. Tests use mocked boundaries; no hosted data or provider calls.
- No browser acceptance, live LTI/Blackboard check, RLS replay, deployment, migration, lint/typecheck/build claim is made by this documentation-only lane. UI evidence is static source review unless stated otherwise.

## Current source revalidation

Reconciliation source base: `8bc569e36b52488b4e05202a90cb18c8ba0db589` (integrated I, G and U closeout). Rechecked proposal/review routes and worker proposer/tagging against integrated source. The accepted 350ms review feedback and retry behavior remain owned by INSTR-REQ-001; backend course-gate and legacy/worker-parser limitations remain partial. No model or database operation was performed. Historical test results above remain tied to the original review revision and were not rerun or upgraded.

Documentation validation for this reconciliation passed: YAML and referenced code/test paths, requirement fields and unique IDs, local links, source line bounds, accepted presentation/changelog preservation, exact draft-to-final mapping, unchanged Lane S requirement, auth byte identity and eight-path ownership. Runtime tests were not rerun.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-25 | Write full source-backed feature spec; record incomplete acceptance and contradictions | APPROVAL-05 rev 2 Lane P; handover WI-08 | SKILL-REQ-001 through SKILL-REQ-005 |
| 2026-10-25 | Revalidate source contracts on integrated main; retain historical test limits | Coordinator-approved Lane P reconciliation; APPROVAL-06 | SKILL requirements above |
