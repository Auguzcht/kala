---
feature: tutor
req_prefix: TUTOR
owner_role: OAICI
status: active
code:
  web: apps/web/src/features/tutor/
  api: services/api/app/routers/tutor.py
  worker: []
  db: []
tests: [services/api/tests/test_tutor.py, services/api/tests/test_request_budget.py]
---

# Tutor request deadline

## Purpose
Learners get course-grounded help and a usable retry message within the inline request budget. An answer remains usable even if saving its conversation fails.

## Actors and permissions
| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| authenticated learner | Ask for course-grounded help, using an owned conversation or stateless mode | Access another user's conversation |

## Requirements

### TUTOR-REQ-001: One 26-second budget per ask request
- Rule: Start one monotonic 26s budget at handler entry. Each outbound call uses min(current timeout, remaining minus 3s reserve), with a separate elapsed-time guard. Skip fallback below 6s remaining. Before an answer, deadline exhaustion returns 503 tutor_timeout with a plain retry message. After an answer, persistence failure or insufficient budget returns the answer and warns with stage and conversation ID prefix. Emit one privacy-safe tutor_timing line with stage milliseconds, mode, provider role, fallback use, and outcome.
- Acceptance: Slow mocked chat returns 503 within budget; late fallback is skipped; failed or slow persistence returns 200 with the answer. Frontend reads flat detail, detail plus optional/nullable code, and safely handles non-JSON errors.
- Status: partial
- Verified by: services/api/tests/test_tutor.py, services/api/tests/test_request_budget.py

## API contract
| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| POST /tutor/ask | Course-grounded help | validated current user; owned conversation when supplied | 503 {detail: string, code: tutor_timeout}; successful answer contract unchanged |

## Data
Reads course-scoped RAG and owned tutor conversation/messages/attachments. Service-role writes preserve original user question and answer; sanitization affects model-bound copies only. No schema or RLS change.

## AI usage (if any)
Tutor selects the existing chat role and its fallback. Embedding, prompt, context, and prior messages pass the existing sanitizer before reaching a provider. Timeout settings are opt-in; other callers keep their existing defaults.

## Edge cases and known limits
Frontend TutorChat message display awaits an ownership grant for its component file; the backend and error/schema contracts are implemented and tested. The budget begins after authentication, at handler entry. It reserves 3s for response work. Synchronous provider operations may continue in a worker after the handler stops waiting; they cannot start later tutor stages. An in-flight persistence write can commit after timeout, so persistence completion is uncertain. No live Lambda/Blackboard recovery claim.

## Change log
| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-24 | Minimal freeze spec created before implementation | APPROVAL-01, section 2 Lane T and confirmed amendment A1 | TUTOR-REQ-001 |
