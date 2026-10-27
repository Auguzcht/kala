---
id: WI-33
status: in-progress
owner: coordinator; implementation TOUR-2 minimal-disable lane
---

# Hide student tour entry while reads can cause work

Requirement: [TOUR-REQ-008](../../../features/tour/README.md#tour-req-008-hide-student-tour-entry-until-reads-are-side-effect-free). APPROVAL-08 Amendment7a authorizes a **new small branch**, separate from preserved codex/tour-rework. One source flag in tour shell hides student auto-offer/manual entry; definitions/copy/anchors remain unchanged. Audit instructor destination GETs first: hide only if side-effecting; otherwise retain unchanged and verify end to end.

Required: role-entry tests, E3 anchors/historical proofs and instructor case matching audit; lint/typecheck/build for changed shell code. No backend/config/evidence/migration change. Full TOUR-2 remains blocked, not partly merged. Report Amendment7a and exact source/role proof. Coordinator merges only the reviewed minimal change after U2 as a distinct deliverable.
