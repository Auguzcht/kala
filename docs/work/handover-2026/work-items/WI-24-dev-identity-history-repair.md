---
id: WI-24
status: blocked
owner: Lane M / Fred
---

# Reconcile historical dev-hosted identity history

Historical authority: [APPROVAL-06 H01(b)](../approval-06.md), including the confirmed identity reconciliation amendment. Branch: no repair branch created; code prevention is separate in codex/identity-convergence.

The existing Alfred and Hanna dev-hosted test records are split across legacy REST-id and LTI-sub users. After the UUID code fix, successful roster reconciliation removes stale alias-user enrollments while retaining their history. Alfred's older 40 events remain on the legacy user and do not appear in the roster until this repair. No history has been merged or deleted. ITO's fresh database does not inherit these test records.

Plan an explicit reviewed identity mapping, dry-run counts, tenant/course checks, evidence/mastery/attempt reconciliation, pre-checks, backup and rollback before any repair. Email or display name alone must never authorize a merge. APPROVAL-07 authorizes local design/implementation today; a named human approves and performs every hosted interaction. Earlier ITO deferral no longer blocks local work. Record actual outcomes separately from the identifier code fix.


## APPROVAL-07 development

Current authority is [APPROVAL-07 section 3](../approval-07.md). Branch: `codex/wi24-identity-repair`; base `d75284ec748ce562c1fe85a223ed5bef4ac53c13`. [Runbook design](../../../runbooks/identity-repair.md) is written before script code. No feature spec changes are proposed by this lane; coordinator owns any historical-repair clarification in AUTH.

Implementation is blocked on exact source-key collisions, legacy exact-identifier/alias conflict, historical actor/consent treatment, attachment storage ownership, and a proved exact affected-row backup/restore procedure. The runbook gives exact source locations and bounded alternatives. No repair script or executable hosted command is released. This is an open development status, not acceptance.

## Verified by

- [Local inventory and limits](../evidence/wi24-identity-repair.md)
