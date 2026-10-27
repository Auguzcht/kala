---
id: WI-32
status: planned
owner: ITO
---

# Side-effect-free reads

APPROVAL-08 Amendment7a blocks the student tour rework on this dependency. The tour and any future prefetching must not assume GET means read-only. Requirements: [TOUR-REQ-002/003/007](../../../features/tour/README.md). The full TOUR-2 branch/audit remains preserved and unmerged.

## Audited GET routes with side effects

| GET route | Observed possible side effects |
| --- | --- |
| /courses/{course_id}/bank/status | Update courses.bank_kicked_at/debounce and invoke bank worker |
| /courses/{course_id}/diagnostic | prepare_missing can enqueue Diagnostic question generation and wake bank work |
| /lessons/{course_id}/skill/{skill_id} | Create/generate a missing guided lesson and steps; ready lessons can still wake bank or lesson-check assignment |
| /flashcards/{course_id}/deck with nonzero limit | Claim cards, ensure schedules and record exposures; limit0 is the separate counts-only safe path |
| /practice/{course_id}/next | Record exposure and, on legacy/empty paths, generate an item |
| /practice/{course_id}/sets/{set_id} | Record item exposures when opening saved-set detail |

The successful GET /flashcards/{course_id}/skills/{skill_id}/cards membership response is read-only, but its frontend404 fallback calls a nonzero deck and inherits that side effect. Study/Test/SkillHub/Diagnostic/Lesson page mounts independently trigger bank/question/lesson reads. Fixing only tour planning is insufficient.

Read-only candidates already available include Diagnostic status, saved-set list, Twin/Next up, successful membership and deck limit0. Future work must distinguish safe reads from explicit work requests, preserve enrollment/tenancy/idempotency, and separately review migration/API/runtime scope before changing it.

## Proof and release boundary

“Zero mutating requests” must be measured by database writes or a request-side-effect log, **not by HTTP method**. Include queue/worker/model calls and schedule/exposure/assignment changes in the effect accounting. Synthetic network-spy checks alone do not establish production no-write behavior. Cover cold/empty/ready/mixed states, client fallback, retries/polling/focus/reconnect, prior in-flight operations, and exit without deferred writes. Preserve normal explicitly requested learning actions.

No API/client/store/query-hook implementation, migration, infrastructure change or hosted inspection is authorized by this planned item. A future design must address uncertain/accepted in-flight work, not assume abort terminates remote effects.
