---
id: WI-21
status: in-progress
owner: Lane B; coordinator owns shared specs
---

# Tutor conversation rename and pin

Authority: [APPROVAL-05](../approval-05.md), section 2 and confirmed amendments. Requirements: [TUTOR-REQ-002/003](../../../features/tutor/README.md#conversation-management-lane-b).

## Scope and scenarios

Add owner/institution-scoped PATCH, strict optional title/pinned validation, additive nullable list pinnedAt and pinned-first ordering. Verify rename boundaries, owner and cross-tenant denial without writes, pin/unpin, combined update, empty/invalid bodies, preserved updated_at and actual SQL ordering. Preserve current create/detail responses and non-tutor behavior.

Apply new migration 0037 once to a throwaway local replay of 0001–0036, preserving historical checksums. Verify type, nullability, existing rows, grants and policies. Record the pinned CLI and actual PostgreSQL version; hosted parity remains unconfirmed. Fred alone applies hosted migration using the reviewed runbook before the new API deploy.

## Ownership and integration

Lane B owns tutor.py's new PATCH and list changes, migration 0037, docs/runbooks/0037-apply.md and new tests/test_tutor_conversation_management.py. Coordinator additionally grants services/api/openapi.json and apps/web/src/lib/api/types.gen.ts for generated additive PATCH/list contracts only: they have no concurrent writer and introduce no behavior outside Tutor. Preserve unrelated generated contracts. Record the grants and generation evidence in the lane report.

Lane U owns the optional/nullable pinnedAt Zod field and capability-gated client controls. Lane B must not edit U's files. packages/schema/supabase.ts remains with the gated DB lane; B reports its regeneration dependency without editing it. Coordinator alone updates shared Tutor/AI specs. If implementation exposes an incorrect spec, stop and submit the correction.

## Evidence and delivery

Readiness audit complete on base 4f3ec29. Implementation, local migration verification, automated checks and review are pending. Nothing merged, deployed or released for this work item. Stop at AUDIT REPORT before merge.
