---
id: WI-26
status: in-progress
owner: ITO
---

# Close instructor course-access and recommendation visibility gaps

Priority: high, review before institutional production sign-off. Current requirements: [INSTR-REQ-009](../../../features/instructor-insights/README.md#instr-req-009-authorize-staff-course-and-learner-access). APPROVAL-07 authorizes implementation on `codex/wi26-course-authorization`; the branch is merged locally, with hosted gates and integrated acceptance still pending. Owner remains ITO.

## Original findings

Some dashboard reads/decisions use an instructor/admin role gate and institution filters without proving that the caller teaches the requested course. `_assert_teaches_student` checks the target learner's enrollment, not caller enrollment. Service-role persistence bypasses RLS. Separately, the plan API hides undecided/rejected recommendations, while the authenticated self-read policy in 0002 does not filter status. Direct Data API exposure and hosted policy state were not tested by this audit.

Define and review course ownership/admin policy before changing behavior. Add denial tests for same-institution instructors outside a course, removed instructors, students, cross-institution calls and decisions against an unowned course. Verify legitimate teachers and institution admins retain intended access. Review every dashboard route, not only the learner-record helper. Determine whether direct authenticated recommendation reads need status filtering; any SQL correction is a new forward migration with real local RLS tests, then a reviewed Fred/ITO apply runbook. Never edit applied0002.

The H01(a) UUID fix removes stale enrollments after a complete successful roster sync, but it does not supply missing checks to routes that never consult that enrollment. The original finding is now addressed locally below; no hosted exploit check or acceptance is claimed. Record this risk explicitly in release review; passing UI/API regression suites is not a security sign-off.

## APPROVAL-07 implementation round

Lane SEC followed coordinator-owned INSTR-REQ-009 / TWIN-REQ-009, INGEST-REQ-001/008 and SKILL-REQ-006. APPROVAL-07 Amendments 2–5 set wrong-role 403 and course/learner/institution 404, authorize all diagnostic staff-branch guards and the scoped recommendation lookup/learner-bound update, and preserve student content reads, helper and queue logic. Migration 0038 tightens 22 existing policies only; its hosted application is still Fred FG-6.

Final SEC revision `9208875cb5bc22f50ce903cf90ef1e680a709e25` merged locally at `afe0c1cb0f35b86a4fddad4d61f83a9ea1067038`. Lane verification: 829 API tests, 117 worker tests, 219 focused authorization cases, 350 local authenticated read cases plus recommendation writes/removed-membership counterexamples, strict 13-route Diagnostic AST proof, unchanged 0001–0037 checksums, and web/docs checks passed. These are local implementation results, not deployed security acceptance. H owns the approved denial/error browser checks. Full merged integration, FG-6, FG-8 and FG-9 remain open.

The initial staff lane preserved student branches. Amendment 7 subsequently authorized the 19 inventoried student GET enrollment guards under AUTH-REQ-007. Revision `9f2d5fb9b527d96ba8b766057ce74e8c0b78d5e0` merged at `63230a3`, after H then M. Dedicated admission/import tests pass 116; exact AST proof permits only those student branches/imports and proves staff, helpers, mutations, response fields and H history unchanged. Full merged API passes 1,014; worker 117; generated contracts are committed. The coordinator report contains every pre-fix route and source line.

Thirteen student mutation methods remain outside Amendment7 and unchanged: Diagnostic submit; flashcard review; Lesson check; Test create/from-items/retake/submit; Tutor create/patch/upload/delete-attachment/delete-conversation/ask. They remain an explicit follow-up finding, not a claimed guard fix. Hosted grants and Data API state have not been inspected in this round. FG-6/8/9 remain open; owner remains ITO.

## Verified by

- [SEC inventory, proof and full report](../evidence/wi26-course-authorization.md)
- [0038 apply runbook](../../../runbooks/0038-apply.md)


## Fred's FG-6 acceptance — 2026-10-27

Fred applied0038/0039 and accepts FG-6 with the pre-existing SELECT-grant finding assigned to Lane DB / WI-04, owner ITO.0038's22 changed policies on20 tables, all36 public policies and20 application functions match; all inspected public tables have RLS with no anon/public policies.0039 has the exact valid/ready history index. No grants are changed. This acceptance supersedes earlier pending-hosted-migration statements; it does not claim hosted authenticated-role acceptance, which is explicitly FG-9.

The backend is deployed from616dfc66: API live8 without weights, worker Active/Successful, deployed image/source mapping and health200 verified. One docs-only frontend push/status check is delegated to Codex; its actual result is in the final coordinator response. WI status remains in-progress and owner ITO pending FG-9; no confirmed-done upgrade.

## Verified by — FG-6

- [Fred's acceptance, grant finding and backend checks](../evidence/fg6-fg8-acceptance-2026-10-27.md)
