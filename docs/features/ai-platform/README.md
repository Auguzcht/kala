---
feature: ai-platform
req_prefix: AI
owner_role: OAICI
status: active
code:
  web: []
  api: services/api/app/ai/
  worker: []
  db: []
tests: [services/api/tests/test_tutor.py, services/api/tests/test_request_budget.py]
---

# Tutor model data boundary

## Purpose
Tutor help sends sanitized copies to embedding and chat providers while preserving conversation records for the learner.

## Actors and permissions
| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| authenticated learner | Ask for course-grounded help, using an owned conversation or stateless mode | Access another user's conversation |

## Requirements

### AI-REQ-001: Sanitize every tutor model-bound text copy
- Rule: Apply the existing sanitizer to RAG embedding input, all history text, current question, system prompt, and built context including attachments. Never replace stored rows with sanitized copies. Do not expand sanitizer patterns in this lane.
- Acceptance: Email in a question never reaches embedding payload; email in prior history never reaches chat payload; stored user content remains original. Non-tutor defaults remain unchanged.
- Status: partial
- Verified by: services/api/tests/test_tutor.py, services/api/tests/test_request_budget.py

## API contract
| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| POST /tutor/ask | Course-grounded help | validated current user; owned conversation when supplied | No response contract change for sanitization |

## Data
Reads course-scoped RAG and owned tutor conversation/messages/attachments. Service-role writes preserve original user question and answer; sanitization affects model-bound copies only. No schema or RLS change.

## AI usage (if any)
Tutor selects the existing chat role and its fallback. Embedding, prompt, context, and prior messages pass the existing sanitizer before reaching a provider. Timeout settings are opt-in; other callers keep their existing defaults.

## Edge cases and known limits
Partial: sanitizer covers email patterns and explicit name: / 姓名: patterns only. It does not remove arbitrary names or other personal data, and is not a guarantee of full de-identification. This freeze lane covers tutor provider calls only; non-tutor caller behavior is unchanged.

## Change log
| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-24 | Minimal freeze spec created before implementation | APPROVAL-01, section 2 Lane T and confirmed amendment A1 | AI-REQ-001 |
