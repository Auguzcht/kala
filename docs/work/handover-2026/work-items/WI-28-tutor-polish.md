---
id: WI-28
status: done-awaiting-confirmation
owner: coordinator; implementation Lane T2
---

# Tutor dialog, pending feedback and conditional editing

Delivery record: [APPROVAL-08 with Amendments1/2](../approval-08.md). Requirements: TUTOR-REQ-005/010/012–016, DESIGN.md Pending and loading states. Branch codex/tutor-polish. Coordinator owns all specs/design/records; lane owns only its brief's implementation/tests. All07 paths are frozen except the named E1/E2 and conditional new Tutor function. No application push/deploy before the human release gates.

Implementation and lane audit reviewed; candidate4da2304 merged locally at3375647. API1016, enrollment116, frontend21, E3 53 and initial browser258 pass. Strict test-only follow-upd379004 mergeddebe791 after U2; mixed browser267, units21/E3/routes56 and web checks pass. Edit message is deferred under WI-29; delegated timing stopped on user_id_prefix under WI-31. No live acceptance is implied. Local tests and screenshots remain separate from FG-9. End at AUDIT REPORT; coordinator merges T2 first, then U2 rebased with retained proofs. Timing is delegated by Fred, read-only; raw data is local only, not retained. Conditional editing requires the feasibility/contract checkpoint; image support remains planned.
