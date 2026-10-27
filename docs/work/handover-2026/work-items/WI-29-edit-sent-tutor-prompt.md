---
id: WI-29
status: planned
owner: ITO
---

# Edit a sent Tutor prompt

Requirement: [TUTOR-REQ-015](../../../features/tutor/README.md#tutor-req-015-edit-only-the-most-recent-sent-prompt-after-feasibility-approval). APPROVAL-08 Amendment2B allowed only migration-free latest-exchange replacement without changes to existing writers or evidence/mastery.

T2 source review finds no durable exchange/revision/idempotency contract or transactional replacement operation. Existing _ask reads history, generates, then persists best-effort; another tab/invocation or late write can race a new delete/replacement route. Equal message timestamps also prevent a reliable last-pair identity. A delete followed by a failed replacement can lose the old exchange and cannot safely recover a retry. No evidence/mastery dependency was found; that alone does not make replacement safe.

Deferred to ITO for a separately approved concurrency, transaction, ordering and recovery design. Do not add an edit endpoint/control, lock hack or partial delete workaround in APPROVAL-08. Scope remains most recent user prompt only when implementation is eventually approved.
