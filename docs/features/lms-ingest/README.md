---
feature: lms-ingest
req_prefix: INGEST
owner_role: product owner
status: active
code:
  web: apps/web/src/features/instructor/
  api: [services/api/app/lms/, services/api/app/routers/diagnostic.py, services/api/app/routers/ingest_jobs.py]
  worker: [services/worker/app/jobs/ingest_walk.py, services/worker/app/jobs/embed_backfill.py]
  db: [packages/db/migrations/0004_rag.sql, packages/db/migrations/0006_module_scope.sql, packages/db/migrations/0017_ingest_jobs.sql, packages/db/migrations/0018_ingest_job_dedupe_and_backoff.sql]
tests:
  - services/api/tests/test_staff_route_auth.py
  - services/api/tests/test_course_data_routes.py
  - services/api/tests/test_ingest_route.py
  - services/api/tests/test_course_content_upload.py
  - services/api/tests/test_blackboard_content.py
  - services/worker/tests/test_ingest_walk.py
---

# LMS content ingest and legacy gradebook authorization

## Purpose
Bring Blackboard course material into a tenant-scoped, chunked and embedded corpus for learning features. Also restrict the existing REST gradebook routes to authorized course staff. INGEST-REQ-001 and its accepted authorization evidence are retained from Lane S; LTI Assignment and Grade Services (AGS) grade passback remains planned.

## Actors and permissions

| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| student | Use student learning routes; current ingest/status endpoints accept a session | Read assessments or write grades through these routes |
| instructor | Read assessments and write grades for courses they teach | Access another course's gradebook |
| admin | Access gradebooks within their institution using the existing institution-wide staff gate | Resolve a course outside their institution |

## Requirements

### INGEST-REQ-001: LMS gradebook read and write routes are restricted to staff who teach the course
- Rule: both routes use the upload route's `require_role('instructor', 'admin')`
  dependency and `_assert_teaches_course` gate before course resolution or an
  LMS call. The existing gate permits institution-wide admins.
- Acceptance: a student on either staff route receives 403. An instructor
  without the matching instructor enrollment receives generic 404; an
  instructor or admin from another institution receives 404. Correct
  instructors and same-institution admins reach the LMS operation. Reuse
  the gate's 404 without translation, preserving wrong-role 403. The shared
  helper and student preview routes remain unchanged. This amended denial
  contract awaits SEC implementation; earlier Lane S proof records 403.
- Status: implemented
- Verified by: `services/api/tests/test_staff_route_auth.py`, tests named
  `test_INGEST_REQ_001_*`, and the existing student course-data regression in
  `services/api/tests/test_course_data_routes.py`.

### INGEST-REQ-002: Enqueue one resumable ingest job per course
- Rule: POST ingest accepts include_attachments=false by default, enqueues pending work and returns 202 without a Blackboard tree walk. Existing pending/in_progress job is returned unchanged; partial unique index and 409 reread recover a concurrent enqueue. Polling returns newest job or never_ingested.
- Acceptance: double-click returns the live job rather than creating a second walk; worker progress is observable in counters/status; enqueue does not perform model/LMS work.
- Status: implemented
- Verified by: `services/api/tests/test_ingest_route.py`; static `routers/ingest_jobs.py::enqueue_ingest`, `ingest_job_status`. Current route scope is session-only; see authorization finding below.

### INGEST-REQ-003: Walk bounded slices with durable hierarchy and throttle recovery
- Rule: worker handles up to three jobs/run, 20 folders and five PDFs per job slice; checkpoint frontier, seen containers and counters so interrupted work resumes. Preserve full folder ancestry, parent reference and module_ref; deduplicate stored content by LMS reference. On 429, retain frontier and set not_before using Retry-After, or 900 seconds when absent; real errors mark failed.
- Acceptance: a shared/revisited container is expanded once; multiple runs match the whole-tree hierarchy; throttled work resumes after backoff without spin; completed frontier marks complete. Attachments are fetched only when requested; a broken PDF does not discard other slice content.
- Status: implemented
- Verified by: `services/worker/tests/test_ingest_walk.py`, including `test_the_job_advances_by_one_bounded_slice_per_run`, `test_the_incremental_walk_matches_the_apis_whole_tree_paths`, `test_pii_is_stripped_before_storage`, `test_attachments_are_not_fetched_unless_the_job_asked`, `test_a_throttle_sets_not_before_from_retry_after`, `test_the_livelock_is_broken_end_to_end_through_the_handler`. Count bounds are not whole-run time guarantees.

### INGEST-REQ-004: Preserve sanitized chunks and recover missing embeddings
- Rule: strip email/name-pattern PII before chunk storage; store module/folder provenance. Embeddings use 1024 dimensions. Failed/missing vectors remain eligible for worker backfill (up to 200 chunks/run), with one chunk's embedding failure isolated. Active content tagging is a separate approved-skill embedding RPC owned by the skills feature.
- Acceptance: stored chunks mask supported PII patterns, keep source hierarchy and can enter retrieval after a later successful embedding; broad names/other personal data are not claimed removed.
- Status: implemented
- Verified by: worker `test_ingest_walk.py::test_a_long_body_is_chunked_not_stored_whole`, `test_pii_is_stripped_before_storage`; static `jobs/embed_backfill.py`. There is no dedicated committed embed_backfill test; the 117-test worker pass is not a substitute for that missing scenario.

### INGEST-REQ-005: Accept authorized supplementary course documents
- Rule: upload requires instructor/admin plus course-teacher gate (institution-wide admin exemption). Accept text/plain, text/markdown, application/pdf up to 5 MiB, with extension fallback for generic MIME. Normalize basename, extract text and reject empty/scanned-without-OCR material. Archive original best-effort, strip supported PII, insert chunks with lms_ref=null and optional module_ref, then attempt pending embeddings. Report stored/embedded/embedFailed/originalArchived/pendingTagging.
- Acceptance: student/unowned staff is denied before storage; unsupported type 415, oversized 413, extraction/no text 422. Original-storage failure does not discard extracted material. Repeat uploads are not idempotent and can add duplicate chunks.
- Status: implemented
- Verified by: `services/api/tests/test_course_content_upload.py`; static `ai/documents.py`, `routers/diagnostic.py::upload_course_content`. The existing 12-second embed phase budget does not bound the entire upload.

### INGEST-REQ-006: Keep preview and module inventory grounded in actual course structure
- Rule: content preview walks metadata without attachments by default. Modules report distinct nonnull module references from stored content and skills, per-module counts and unscoped counts; no institution-specific module naming assumption. Roster/content preview resolves the course under authenticated institution.
- Acceptance: preview does not download course PDFs; module inventory distinguishes unscoped content; invalid/outside-institution course reference returns 404 on resolver routes.
- Status: implemented
- Verified by: `test_blackboard_content.py`, `test_lms_hierarchy.py`, `test_course_data_routes.py`; static `diagnostic.py::get_content`, `list_modules`. Some route gates are session-only, not course-teacher gates.

### INGEST-REQ-007: Add whole-request bounds for upload and LMS calls
- Rule: planned deadlines must include extraction/storage/chunk persistence/embedding for upload and multi-call LMS work for preview/launch paths, with safe retryable responses.
- Acceptance: a slow dependency cannot overrun the full API budget while a phase timer appears healthy; unfinished work has an explicit recovery path.
- Status: planned
- Verified by: not-run; [WI-15](../../work/handover-2026/work-items/WI-15-content-upload-budget.md) and [WI-16](../../work/handover-2026/work-items/WI-16-lms-request-deadlines.md). No such whole-request budget is claimed in current source.

## API contract

| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| GET /courses/{course_id}/assessments | Read LMS gradebook columns | Instructor enrollment for this course, or institution admin | 403 on role/course denial; existing course lookup and UUID validation retain 404 |
| PATCH /courses/{course_id}/assessments/{column_id}/grade | Existing Blackboard REST grade write-through | Same staff course gate | Body remains `{user_id, score}`; 403 before LMS write; AGS passback remains planned |
| POST /courses/{course_id}/ingest | Enqueue LMS walk | Session only in current implementation | Query include_attachments=false; 202 queued/already_in_progress plus job |
| GET /courses/{course_id}/ingest/status | Latest job and counters | Session only in current implementation | never_ingested/job=null when absent; includes operational error/frontier fields |
| POST /courses/{course_id}/content/upload | Supplementary document | Course instructor or institution admin | Multipart file + optional module_ref; 413/415/422; upload gate retains 404 course denial |
| GET /courses/{course_id}/content | Metadata/content preview | Session + institution course resolution | No attachment download by default |
| GET /courses/{course_id}/roster | LMS roster preview | Session + institution course resolution | Legacy route, distinct from dashboard roster |
| GET /courses/{course_id}/modules | Stored module inventory | Session | Content/skill/unscoped counts |
| POST /courses/{course_id}/content/retag | Embedding-tag recomputation | Course instructor or institution admin | See skills spec; no model call |

## Data
The existing server-side gate reads `enrollments`, filtering by authenticated
`institution_id`, `user_id`, requested `course_id`, and `role=instructor`.
Course resolution reads `courses`, filtered by authenticated institution and
requested course ID. Neither gradebook route writes Supabase rows; grade PATCH writes
through the mocked Blackboard connector in tests. No schema or RLS changes were made by Lane S or this documentation extension.

The content pipeline writes ingest_jobs and content_items through service-role API/worker access; optional original bytes go to storage. Read courses for LMS reference and status; worker persists frontier/seen/not_before/counters and writes embeddings. RLS 0017 gives job reads to course teachers or institution admins; 0023 restricts raw content reads to the same staff scope. Service-role routes bypass these policies: missing API gates below are not rescued by RLS. Content source IDs deduplicate LMS re-walks; supplementary uploads have no LMS reference and no equivalent dedupe. Source content deletion/update refresh semantics are not proven by a repeat ingest.

## AI usage (if any)
None in the two gradebook routes. Content embeddings call the configured provider on sanitized chunk text; active tagging uses vectors without a chat call. Generation/proposal is downstream in the skills/bank features, not a synchronous enqueue operation. The current sanitizer masks emails and explicit name-patterns only; it does not provide comprehensive anonymization.

## Edge cases and known limits
- Admins retain the upload gate's institution-wide exemption from enrollment
  checks; course resolution remains institution-scoped.
- The 403 mapping is local to these two routes. The upload gate continues to
  return 404 for an instructor who does not teach the course.
- Grade passback through AGS is planned; securing the legacy REST route does
  not implement it. No live Blackboard verification is claimed.
- Upload timing correction (comment only): the embedding loop checks a
  12-second phase budget between chunks. In-flight embedding/database calls
  can exceed it; extraction, storage, chunk inserts, and the pending query are
  outside that budget. Upload has no whole-request deadline and can exceed
  the 30-second Lambda ceiling. Tagging remains queued for the worker.

## Contradictions requiring planner resolution

| Locations at source revision | Finding | Proposed resolution (not implemented here) |
| --- | --- | --- |
| `services/api/app/routers/ingest_jobs.py:11` (SCAFFOLD/unwired description); `services/api/app/routers/diagnostic.py:212` (enqueue call); `services/api/tests/test_ingest_route.py:1` | Helper's stale header says wiring is pending, while route and tests demonstrate integration. | Correct the stale module description in an API-owned documentation task; preserve current queue contract. |
| `packages/db/migrations/0017_ingest_jobs.sql:95` (staff/course read RLS); `services/api/app/routers/diagnostic.py:190` and `services/api/app/routers/diagnostic.py:227` (session-only enqueue/status); `services/api/app/db/supabase.py:25` (service role) | Enqueue/status do not assert institution course ownership or staff membership; status helper filters course only. | Authorize explicit course/tenant gates and cross-institution denial tests; review status error/frontier disclosure. |
| `packages/db/migrations/0023_course_scoped_staff_reads.sql:6`; `services/api/app/routers/diagnostic.py:137` and `services/api/app/routers/diagnostic.py:146` | LMS roster/content previews use session + institution resolver, without the staff/course gate used by gradebook/upload. | Decide preview visibility and add route denial coverage in a separately scoped security task. |

## Evidence and verification limits

WI-08 / APPROVAL-05 rev 2, Lane P. Source reviewed at `4f3ec29d3f827a1db92e90c4f395947d37744479` on 2026-10-25. `implemented` means present in that source, with the evidence stated per requirement; it is not a claim of deployed acceptance. `partial` identifies an explicit gap. Planned behavior is not inferred from archived plans.

- Local: `cd services/api && uv run pytest -q` — **431 passed**, 30 dependency deprecation warnings, 28.45s.
- Local: `cd services/worker && uv run pytest -q` — **117 passed**, 0.68s.
- Both processes used committed `services/conftest.py`: dotenv disabled, inherited application settings replaced, IPv4/IPv6/DNS blocked. Tests use mocked boundaries; no hosted data or provider calls.
- No browser acceptance, live LTI/Blackboard check, RLS replay, deployment, migration, lint/typecheck/build claim is made by this documentation-only lane. UI evidence is static source review unless stated otherwise.

## Current source revalidation

Reconciliation source base: `8bc569e36b52488b4e05202a90cb18c8ba0db589` (integrated I, G and U closeout). Rechecked the gradebook/upload gates, enqueue/status helpers, module inventory and ingest worker against the integrated source. Lane G changes Diagnostic selection/status outside this spec; the ingest contracts remain unchanged. Existing source findings are retained, with current Diagnostic-router line anchors refreshed. No LMS call, upload or model operation was performed. Historical test results above remain tied to the original review revision and were not rerun or upgraded.

Documentation validation for this reconciliation passed: YAML and referenced code/test paths, requirement fields and unique IDs, local links, source line bounds, accepted presentation/changelog preservation, exact draft-to-final mapping, unchanged Lane S requirement, auth byte identity and eight-path ownership. Runtime tests were not rerun.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-24 | Minimal freeze spec; reuse upload staff/course gate on gradebook routes; correct upload timing comment | APPROVAL-01 sections 1, 2 Lane S, and confirmed amendment A4; accepted BRIEF-01 endpoint audit | INGEST-REQ-001 |
| 2026-10-25 | Extend to full source-backed ingest spec, retaining accepted INGEST-REQ-001 wording and evidence | APPROVAL-05 rev 2 Lane P; WI-08; Lane S acceptance remains APPROVAL-02 | INGEST-REQ-001 through INGEST-REQ-007 |
| 2026-10-25 | Revalidate source contracts on integrated main; retain historical test limits | Coordinator-approved Lane P reconciliation; APPROVAL-06 | INGEST requirements above |

| 2026-10-25 | Preserve helper 404 for untaught/foreign course gradebook denials; wrong role stays 403 | APPROVAL-07 Amendment 2; coordinator commits before SEC changes and Lane S test updates | INGEST-REQ-001 |
