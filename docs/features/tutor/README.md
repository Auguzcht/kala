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
tests: [services/api/tests/test_tutor.py, services/api/tests/test_request_budget.py, apps/web/src/features/tutor/components/TutorChat.test.mjs, apps/web/src/lib/api-error.test.ts, apps/web/src/features/tutor/schema/tutor.schema.test.ts]
---

# Tutor help and conversation management

## Purpose
Learners get course-grounded help and a usable retry message within the inline request budget. An answer remains usable even if saving its conversation fails.

## Actors and permissions
| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| authenticated learner | Ask for course-grounded help, using an owned conversation or stateless mode | Access another user's conversation |

## Requirements

### TUTOR-REQ-001: One 26-second budget per ask request
- Rule: Start one monotonic 26s budget at handler entry. Each outbound call uses min(current timeout, remaining minus 3s reserve), with a separate elapsed-time guard. Skip fallback below 6s remaining. Before an answer, deadline exhaustion returns 503 tutor_timeout with a plain retry message. After an answer, persistence failure or insufficient budget returns the answer and warns with stage and conversation ID prefix. Emit one privacy-safe tutor_timing line with stage milliseconds, mode, provider role, fallback use, and outcome.
- Acceptance: Slow mocked chat returns 503 within budget; late fallback is skipped; failed or slow persistence returns 200 with the answer. Frontend reads flat detail, detail plus optional/nullable code, and safely handles non-JSON errors. TutorChat shows the retry detail and preserves returned answers when persistence refetch fails or lacks them; saved responses retain the normal handoff.
- Status: implemented
- Verified by: services/api/tests/test_tutor.py, services/api/tests/test_request_budget.py, apps/web/src/features/tutor/components/TutorChat.test.mjs, apps/web/src/lib/api-error.test.ts, apps/web/src/features/tutor/schema/tutor.schema.test.ts

## Conversation management (Lane B)

### TUTOR-REQ-002: Rename an owned conversation
- Rule: PATCH /tutor/conversations/{conversation_id} accepts optional title, a string of 1–80 characters. Omitted fields remain unchanged. The mutation filters by conversation ID and the validated session's user ID and institution ID. Missing, malformed, other-user and cross-institution conversations return 404. An empty body, explicit null, invalid field type or unsupported field returns 422. Success returns the updated conversation. Rename changes title only and preserves pinned_at and updated_at.
- Acceptance: Owner rename persists and returns 200. Other-user and cross-institution requests return 404 without a write. Titles of 1 and 80 characters succeed; empty and over-80-character titles return 422. Empty and invalid bodies produce no write.
- Status: planned
- Verified by: services/api/tests/test_tutor_conversation_management.py (planned)

### TUTOR-REQ-003: Pin owned conversations and list pins first
- Rule: The same PATCH route accepts optional pinned: boolean. true sets pinned_at to the database's current transaction time; false clears it. Repeating true refreshes the pin time. Omitting pinned preserves its value. title and pinned may be updated together in one scoped mutation. Pinning preserves updated_at. GET /tutor/conversations retains its course, owner and institution filters and existing response fields, and adds pinnedAt to each conversation: a timestamp when pinned, otherwise null. Frontend consumers accept pinnedAt as optional and nullable for compatibility with older APIs. Order is pinned_at descending with nulls last, then updated_at descending.
- Acceptance: Pin and unpin persist and return the resulting pinnedAt. Unauthorized mutations return 404 without a write. Combined rename/pin succeeds atomically. Pinned conversations precede unpinned conversations; newer pins precede older pins; unpinned conversations retain updated_at descending order.
- Status: planned
- Verified by: services/api/tests/test_tutor_conversation_management.py (planned)

## API contract
| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| POST /tutor/ask | Course-grounded help | validated current user; owned conversation when supplied | 503 {detail: string, code: tutor_timeout}; successful answer contract unchanged |
| PATCH /tutor/conversations/{conversation_id} | Rename, pin or unpin an owned conversation | validated current user and institution | Body {title?: string 1..80, pinned?: boolean}; at least one field required; 200 updated conversation including nullable pinnedAt; 404 unavailable conversation; 422 invalid body |
| GET /tutor/conversations?course_id={course_id} | List owned course conversations | validated current user and institution | Existing conversations envelope and fields retained; adds nullable pinnedAt; order pinned_at.desc.nullslast,updated_at.desc |

## Data
Reads course-scoped RAG and owned tutor conversations/messages/attachments. Service-role writes preserve original user question and answer; sanitization affects model-bound copies only. Planned migration 0037_tutor_conversation_pin.sql adds nullable pinned_at timestamptz to tutor_conversations without a default or backfill. Existing RLS policies and grants remain unchanged. Conversation-management mutations explicitly filter by conversation ID, validated session user ID and institution ID because the API service role bypasses RLS. Existing create/detail response contracts remain unchanged; the pin projection is added to list and PATCH only.

## AI usage (if any)
Tutor selects the existing chat role and its fallback. Embedding, prompt, context, and prior messages pass the existing sanitizer before reaching a provider. Timeout settings are opt-in; other callers keep their existing defaults.

## Edge cases and known limits
TutorChat retains an unconfirmed answer locally when its refetch fails or lacks the returned turn, and removes the duplicate display if that turn later arrives from storage. This local copy lasts only while the conversation remains open and does not retry saving automatically. The budget begins after authentication, at handler entry. It reserves 3s for response work. Synchronous provider operations may continue in a worker after the handler stops waiting; they cannot start later tutor stages. On Lambda, an abandoned synchronous call can resume when the warm execution environment serves the next request; returning a response does not terminate that call or guarantee cancellation of its remote side effects. An in-flight persistence write can commit after timeout, so persistence completion is uncertain. No live Lambda/Blackboard recovery claim.

## Change log
| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-24 | Minimal freeze spec created before implementation | APPROVAL-01, section 2 Lane T and confirmed amendment A1 | TUTOR-REQ-001 |
| 2026-10-24 | Complete timeout detail and unconfirmed-answer display in TutorChat | APPROVAL-01 standing rule; coordinating planner grant for TutorChat.tsx and dedicated UI tests | TUTOR-REQ-001 |
| 2026-10-24 | Explicitly document that an abandoned synchronous call can resume during the next request in a warm Lambda environment | APPROVAL-02 from Fred | TUTOR-REQ-001 |
| 2026-10-25 | Define owner-scoped conversation rename and pin, additive pinnedAt responses and pinned-first listing | APPROVAL-05 rev 2, section 2 and confirmed coordinator amendments | TUTOR-REQ-002, TUTOR-REQ-003 |
