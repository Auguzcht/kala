---
id: WI-26
status: planned
owner: ITO
---

# Close instructor course-access and recommendation visibility gaps

Priority: high, review before institutional production sign-off. Source findings: [INSTR-REQ-008 and contradictions](../../../features/instructor-insights/README.md#contradictions-requiring-planner-resolution). Authority: APPROVAL-06 permits documentation of open handover items; implementation is outside the current identity/availability/UI lanes. Branch: not started.

Some dashboard reads/decisions use an instructor/admin role gate and institution filters without proving that the caller teaches the requested course. `_assert_teaches_student` checks the target learner's enrollment, not caller enrollment. Service-role persistence bypasses RLS. Separately, the plan API hides undecided/rejected recommendations, while the authenticated self-read policy in 0002 does not filter status. Direct Data API exposure and hosted policy state were not tested by this audit.

Define and review course ownership/admin policy before changing behavior. Add denial tests for same-institution instructors outside a course, removed instructors, students, cross-institution calls and decisions against an unowned course. Verify legitimate teachers and institution admins retain intended access. Review every dashboard route, not only the learner-record helper. Determine whether direct authenticated recommendation reads need status filtering; any SQL correction is a new forward migration with real local RLS tests, then a reviewed Fred/ITO apply runbook. Never edit applied0002.

The H01(a) UUID fix removes stale enrollments after a complete successful roster sync, but it does not supply missing checks to routes that never consult that enrollment. No security fix or hosted exploit check is claimed here. Record this risk explicitly in release review; passing UI/API regression suites is not a security sign-off.
