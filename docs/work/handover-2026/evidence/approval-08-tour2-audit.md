# TOUR-2 audit and concrete scope decision

2026-10-27. Branch codex/tour-rework, basebeccf5915c4caea045fc5a6e8be2945aaf8812ad. **No source edits, no partial tour implementation and no merge.** This report is a design/audit record; it grants no new ownership or behavior. TOUR-REQ-002/003/004/006/007 and WI-30 apply.

## Stop condition confirmed

APPROVAL-08 Amendment4 says stop if a step would need a write to demonstrate or a required anchor sits in07-protected source. Both occur. The current student prepared-topic tour has17 steps, default9; instructor27. New target is a complete12-step fixed student plan, not a partial rewrite.

| Current path/boundary | Source observation |
| --- | --- |
| CourseShell.tsx:214 | Tour planning itself reads bank status; this call can be replaced inside shell scope. |
| services/api/app/routers/bank.py:56 and app/bank/kick.py | Bank status can update debounce state and invoke worker. |
| features/diagnostic/components/DiagnosticPanel.tsx:32; routers/diagnostic.py:641 | Page mounts question/bank reads; prepare_missing=True can enqueue and wake work. |
| features/lessons/components/LessonChat.tsx:46; app/learn/lessons.py:231,405–407 | Missing lesson can be inserted/generated; even ready content may wake lesson-check/bank work. |
| features/skill-hub/components/SkillHub.tsx:180; StudyBrowser/TestBrowser | Page mount independently primes bank status. |
| features/flashcards/api/flashcards.api.ts:40; routers/flashcards.py:328 | Membership404 falls back to nonzero deck, which can claim/ensure schedule/record exposure. |
| routers/practice.py:636 and /next | Saved-set detail records exposure; next may expose/generate. |

Read-only building blocks include Diagnostic status, saved-set list, Twin/Next up, successful membership and deck limit0. They cannot prevent ordinary destination components from issuing the operations above. Zero POSTs or mocked responses alone would be insufficient proof.

## Required anchors and draft target mapping

| New anchor | Unprotected owner/location |
| --- | --- |
| workspace-next-up | U2/E4 existing Next up card in routes/course/index.tsx |
| workspace-twin-glance | U2/E4 snapshot card in the same file |
| study-start | U2 StudyBrowser primary button only; retain tour-study-actions |
| test-first-saved-set | U2 TestBrowser first saved-set button, conditional existing first index; empty uses existing tour-test-new-set |
| tutor-history-actions | T2 existing overflow trigger; choose one visible first-row control at runtime |

Draft semantic mapping: Diagnostic uses existing diagnostic-header on real question UI because no Start button exists there; Skills uses actual tour-skills-first-card button/card rather than a fictional row; instructor record fallbacks without a real learner remain on /class without fabricated ID. All are proposals awaiting coordinator/Fred decision, not changes already made.

**Existing protected anchors, no edits proposed:** TwinBody.tsx(twin-ledger); CohortStats.tsx(KPI); RosterTable.tsx(search/filter/first row); AtRiskList.tsx(first flag); LearnerRecord.tsx(tabs/radar/intervention/ledger). They are07-protected even though reuse changes zero bytes; a named resolution is required under the literal stop rule. No additional Load older activity anchor in protected EvidenceHistoryLedger is requested.

## Minimum credible frontend-only read-only design — NOT approved

1. Close a real API-client request barrier synchronously before planning. Deny every mutation, unknown endpoint, bank status, lesson retrieval, Diagnostic questions, nonzero deck, practice next and saved-set detail. Permit only an exact audited read-only method/path/query allowlist. Discard blocked operations, never queue/replay them.
2. Track requests from application startup. Refuse entry if an unsafe request is in flight; abort/timeout is not proof the server stopped. The mode cannot revoke accepted requests or earlier queued jobs. Any invariant covering those earlier jobs cannot be proved frontend-only.
3. Unsafe feature queries become cache-only while the barrier is closed. Disable automatic fetch/poll/retry/focus/reconnect plus imperative refetch bypass. Show real cached ready content or centered same-page fallback; never fabricate data. Membership must not use its deck fallback. Test uses list only, never detail. Freeze plan/routes/total before step1.
4. Exit/Escape/completion must **not** simply release the barrier, which would defer writes until exit. Retain a read-only holding state on the current page. A new explicit Open this page action resumes a deliberate normal page, stripping tour start/session/set-detail parameters. Back/history alone cannot release protection. This is a new UX decision beyond the original tour-only scope.
5. During the tour, learning mutation controls are noninteractive. Permit only the named UI-only sheet/tab/history operations. This changes current manual-action semantics and needs explicit approval, not an inferred guard-only grant.

| Proposed owner | Exact scope requiring approval |
| --- | --- |
| TOUR-2 | apps/web/src/lib/api/client.ts and new lib/api/tour-read-policy.ts; request barrier, strict allowlist, in-flight tracking |
| TOUR-2 | apps/web/src/stores/ui-store.ts; planning/walking/holding lifecycle/epoch, no server payloads |
| TOUR-2 | CourseShell.tsx, InstructorShell.tsx, new TourReadBoundary.tsx and existing tour files/definitions/browser tests; InstructorShell ownership confirmed explicitly |
| U2 | features/bank/hooks/use-bank-status.ts; diagnostic/hooks/use-diagnostic.ts; lessons/hooks/use-lessons.ts; flashcards/hooks/use-flashcards.ts; practice/hooks/use-practice.ts — tour-only cache/refetch gating, default normal behavior unchanged |
| U2/T2 | Attribute-only additions in owned components listed above |
| Coordinator | Specs, records and E3 current-target catalog only; historical7 checks and existing attributes unchanged |

No backend/schema/DTO/config change is proposed, but this is broader app-client/store/hook work. Same-day feasibility is not established. No implementation is released by this design.

## Required proof before any merge

Test the **real API client**, not a mock replacement. Local synthetic endpoint responses/counters and normal-mode positive controls must show no forbidden transport during planning, all steps, Back, exit and holding; unsafe preexisting requests refuse entry; polling/focus/reconnect/invalidation/manual refetch cannot bypass; no delayed request on exit; explicit resume starts only the chosen normal page.

Then complete happy/empty/mixed students at375px/1440px, all12 in order, fixed N, one highlight/fallback each, no toasts/mutations, precise fixed padding, non-overlapping popover, cross-page Back, bounded waits, draft/dismissal/Escape behavior. Instructor order stays27, repair shared-rule violations only. E3 historical proof/current comment retained; current-target coverage extended only by coordinator to the approved definitions. Report tour browser count beside old616. No partial merge.

## Instructor audit

Current shared runner silently skips/toasts on missing targets, can change visible sequence, lacks fixed progress/fallback guarantees, does not restore closed sheet/tab content on Back, and lacks required geometry assertions. Copy exceeds two sentences and includes semicolon wording. Empty roster supplies no learner ID. Keep27-step order, use valid /class fallbacks for unresolved learner pages, and never invent identity. Audited instructor reads/UI-only tab/row operations did not expose the student GET-write blockers, but full runtime proof remains required.

## Commands and audit result

Source/protected-path audit clean; no source changes. E3 plus tour-route tests: **56 passed** (53+3), no skips/failures/todos. No browser/server run, no new assertion count, no lint/typecheck/build claim for an unimplemented tour. No hosted, migration, config, push or deploy operation.

```text
AUDIT REPORT
Task / brief ID: APPROVAL-08 Amendment4 TOUR-2; WI-30
Branch and worktree: codex/tour-rework; own lane checkout
Base revision: beccf5915c4caea045fc5a6e8be2945aaf8812ad
Files changed: none
REQ / WI IDs touched: assessed TOUR-REQ-002/003/004/006/007; WI-30
Commands run and results: source/anchor/query/store/client audit;
  unchanged E3+route56 passed; no implementation/browser/web checks.
Spec changes made: none by lane; coordinator owns requirements.
Evidence added: this reviewed audit and unapproved design.
Anything not done, and why: implementation stopped on protected
  required anchors and write-capable destination GETs. No partial merge.
Risks or questions for planner: scope/holding-resume/manual-action
  semantics and full-matrix feasibility need explicit decision.
Secrets printed: none (confirmed).
```
