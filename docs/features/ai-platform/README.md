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

### AI-REQ-002: Privacy-safe provider failure diagnostics for Tutor
- Rule: Every failed budgeted Tutor embedding or chat provider attempt records stage (`embed` or `chat`), provider, attempted model, HTTP status (nullable when unavailable), and an opaque request_id. Correlate embedding, primary chat and fallback chat using one internally generated ID per RequestBudget; this is not an upstream provider ID or a client-supplied identifier. Distinct requests have distinct IDs. CloudWatch invocation metadata remains a separate correlation source.
- Rule: Never log request or response bodies, credentials, tokens, student identity, prompts or arbitrary exception strings. Classify HTTP 401, 403 and 402 distinctly at error level while preserving the student-safe ModelUnavailableError 502 message and existing no-fallback handling for those statuses. Preserve all existing fallback eligibility, model selection, timeouts, retry behavior and TUTOR-REQ-001 deadline precedence, including existing paths that return 503 when the deadline wins. Do not convert previously unwrapped exceptions into a different response solely for logging. Non-budgeted provider behavior remains unchanged.
- Acceptance: Mocked embedding, primary and fallback failures retain all fields for 401, 402, 403, 429, 503 and transport errors; transport/SDK failures with no known HTTP status use null. All attempts in one request share an ID, while different requests differ. Sensitive markers never reach logs. Authorization/payment failures do not gain retries; fallback failures retain their own status and model. Existing deadline, successful-answer persistence recovery and non-budgeted default behavior tests continue to pass.
- Status: planned
- Verified by: Lane X's new provider-diagnostics tests (pending); existing provider dispatch, request-budget and Tutor regressions.

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

APPROVAL-05 diagnostics improve observability; they do not remove provider rate limits or prove live recovery. Three inspected requests received primary OpenRouter HTTP 429 and then a fallback failure whose status was omitted. The attempted fallback was a free variant. Neither the limiting scope nor the fallback cause is established. Model/config changes remain Fred's decision; the reported positive balance must not be described as exhausted credit.

## Change log
| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-24 | Minimal freeze spec created before implementation | APPROVAL-01, section 2 Lane T and confirmed amendment A1 | AI-REQ-001 |
| 2026-10-25 | Specify privacy-safe Tutor provider failure diagnostics and per-budget correlation before implementation | APPROVAL-05 rev 2; confirmed CLI evidence and coordinator review | AI-REQ-002; TUTOR-REQ-001 compatibility |
