---
id: WI-01
status: in-progress
owner: Lane X; coordinator owns AI/Tutor specs
---

# Provider 502 follow-up under APPROVAL-05

This continues WI-01 in the initiative registry, not a new identifier. Authority: [APPROVAL-05](../approval-05.md), section 1 and confirmed amendments. Requirements: [AI-REQ-002](../../../features/ai-platform/README.md#ai-req-002-privacy-safe-provider-failure-diagnostics-for-tutor), preserving AI-REQ-001 and TUTOR-REQ-001.

## Findings and approved implementation

The read-only CLI investigation found three primary OpenRouter chat HTTP 429 failures followed by failed fallback attempts with no emitted fallback status. Retrieval completed in each case. This confirms a primary rate-limit response and a logging defect; it does not establish the exact limiting scope, fallback cause, credit exhaustion or recovery.

Coordinator approves the narrowly scoped diagnostics fix after this spec commit: safe failure fields, distinct authorization/payment error classification, unchanged student response and unchanged model/fallback/deadline policy. Lane X may edit router.py, bedrock.py and main.py (error mapping only) as assigned in the approval. Additional grant: services/api/app/ai/request_budget.py, only an opaque per-budget correlation ID exposed to existing budgeted provider calls. No lane currently owns that path; the addition changes neither deadline semantics nor non-budgeted callers. Record the reason and tests in the AUDIT REPORT. No tutor.py edit; it belongs to B.

## Verification and remaining gates

Use new uniquely named tests under services/api/tests, including sensitive-marker exclusion, stable/distinct correlation IDs, all specified error statuses, fallback-attempt metadata, and unchanged default callers. Run the full isolated API suite. Keep live provider/account evidence distinct from mocked verification.

The initial investigation submission reports 500 passing API cases, including 69 new investigation cases, before any production fix. The coordinator additionally authorized reading the configured credential in process memory for the official read-only OpenRouter key/quota endpoint, under Fred's CLI/key-access authorization. Emit only safe allowlisted status/quota metadata, never payloads or credentials; no generation calls, hosted writes, key/config changes or deployment.

Provider recovery, per-UI-shape sanitizer checks and correlated Explain-more timing remain pending. No shorter-style, streaming, global retry or model-selection change is authorized. Return AUDIT REPORT before merge. Fred alone performs operational config changes and deployment.
