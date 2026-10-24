---
feature: instructor-insights
req_prefix: INSTR
owner_role: product owner
status: active
code:
  web: apps/web/src/features/instructor/
  api: services/api/app/routers/dashboard.py
  worker: []
  db: []
tests: [apps/web/src/features/instructor/tests/review-feedback.browser.mjs]
---

# Instructor decision feedback

## Purpose

This focused amendment defines visible feedback for instructor skill reviews and recommendation decisions. The broader instructor specification is still incomplete under WI-08; this document does not redefine roster arithmetic, identity resolution or backend permissions.

## Actors and permissions

| Actor | Can | Cannot |
| --- | --- | --- |
| Instructor with existing course access | Review proposed skills and confirm recommendation decisions through existing APIs | Gain access to another course or bypass the server's decision gate |

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

## API contract

| Method/path | Purpose | Auth | Change |
| --- | --- | --- | --- |
| PATCH /dashboard/{course_id}/skills/{skill_id}/review | Approve/reject a proposed skill | Existing instructor/admin course gate | None |
| PATCH /dashboard/{course_id}/recommendations/{rec_id} | Record a confirmed recommendation decision | Existing instructor/admin course gate | None |

## Data

No new persistence or identity mapping. TanStack Query owns server responses. The presentation interval exists only while an existing mutation runs. Hosted identity repair is outside this amendment.

## AI usage

None added. Reviewing an existing proposal or recommendation does not introduce a model call.

## Edge cases and known limits

Network errors, fast responses, slow responses, keyboard activation, reduced motion and repeated clicks are covered. This local implementation does not deploy changes to the separate hosted instructor site. Duplicate enrolled/LTI identities require a separately reviewed human-run repair; never merge by display name in the UI.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-25 | Define a minimum visible review interval and confirmed recommendation transition before implementation | Fred's direct instructor feedback request in WI-22; supersedes the old optimistic transition | INSTR-REQ-001, INSTR-REQ-002 |
