---
id: WI-24
status: planned
owner: ITO
---

# Reconcile historical dev-hosted identity history

Authority: [APPROVAL-06 H01(b)](../approval-06.md), including the confirmed identity reconciliation amendment. Branch: no repair branch created; code prevention is separate in codex/identity-convergence.

The existing Alfred and Hanna dev-hosted test records are split across legacy REST-id and LTI-sub users. After the UUID code fix, successful roster reconciliation removes stale alias-user enrollments while retaining their history. Alfred's older 40 events remain on the legacy user and do not appear in the roster until this repair. No history has been merged or deleted. ITO's fresh database does not inherit these test records.

Plan an explicit reviewed identity mapping, dry-run counts, tenant/course checks, evidence/mastery/attempt reconciliation, pre-checks, backup and rollback before any repair. Email or display name alone must never authorize a merge. No script is built or run today; a named human approves and performs any hosted write. Record actual outcomes separately from the identifier code fix.
