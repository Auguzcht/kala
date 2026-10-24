---
feature: lms-ingest
req_prefix: INGEST
owner_role: product owner
status: active
code:
  web: []
  api: services/api/app/routers/diagnostic.py
  worker: []
  db: []
tests:
  - services/api/tests/test_staff_route_auth.py
  - services/api/tests/test_course_data_routes.py
---

# LMS gradebook route authorization

## Purpose
Restrict the existing LMS gradebook read and write routes to staff authorized
for the requested course. This minimal freeze spec covers authorization only;
LTI Assignment and Grade Services (AGS) grade passback remains planned.

## Actors and permissions
| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| student | Use student learning routes | Read assessments or write grades through these routes |
| instructor | Read assessments and write grades for courses they teach | Access another course's gradebook |
| admin | Access gradebooks within their institution using the existing institution-wide staff gate | Resolve a course outside their institution |

## Requirements

### INGEST-REQ-001: LMS gradebook read and write routes are restricted to staff who teach the course
- Rule: both routes use the upload route's `require_role('instructor', 'admin')`
  dependency and `_assert_teaches_course` gate before course resolution or an
  LMS call. The existing gate permits institution-wide admins.
- Acceptance: a student receives 403; an instructor without an instructor
  enrollment in this institution and course receives 403; an instructor of
  this course reaches the mocked LMS operation. These two routes translate
  the gate's 404 denial to 403 without changing the shared gate or upload.
- Status: implemented
- Verified by: `services/api/tests/test_staff_route_auth.py`, tests named
  `test_INGEST_REQ_001_*`, and the existing student course-data regression in
  `services/api/tests/test_course_data_routes.py`.

## API contract
| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| GET /courses/{course_id}/assessments | Read LMS gradebook columns | Instructor enrollment for this course, or institution admin | 403 on role/course denial; existing course lookup and UUID validation retain 404 |
| PATCH /courses/{course_id}/assessments/{column_id}/grade | Existing Blackboard REST grade write-through | Same staff course gate | Body remains `{user_id, score}`; 403 before LMS write; AGS passback remains planned |

## Data
The existing server-side gate reads `enrollments`, filtering by authenticated
`institution_id`, `user_id`, requested `course_id`, and `role=instructor`.
Course resolution reads `courses`, filtered by authenticated institution and
requested course ID. Neither route writes Supabase rows; grade PATCH writes
through the mocked Blackboard connector in tests. No schema or RLS changes.

## AI usage (if any)
None in these two routes.

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

## Change log
| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-24 | Minimal freeze spec; reuse upload staff/course gate on gradebook routes; correct upload timing comment | APPROVAL-01 sections 1, 2 Lane S, and confirmed amendment A4; accepted BRIEF-01 endpoint audit | INGEST-REQ-001 |
