# APPROVAL-08 coordinator progress and E3 proof

2026-10-27. Initial local main d46e3e482bf07678b73e8aee0199630e2ca0a259. C1/C2 and Amendments1/2 specified at71c799a before lane audit. E3/TOUR acceptance policy specified at7ed8944 before test changes. The opening sections retain their initial pre-implementation checkpoint. Later reviewed integration is recorded below; no app push/deploy is claimed. All human gates retain FG-6→FG-8→FG-7a/b→FG-9 order.

## APPROVAL-07 status verified before dispatch

H is merged after browser green, M final governance report/revision is merged, and Amendment7's19 student GET guards are merged, in that order. Generated contracts8e51040 and final docs526aec7 precede this round. Final07 local API1,014, worker117, frontend/tour33, Study4 and browser1,474 pass; web/config/docs/AST/local migration checks passed. The isolated compact-context utility was later published and merged locally; it did not publish07. Main was54 ahead/0behind cached origin/main before08, clean. No hosted gates were inspected or assumed complete.

## E3 baseline and portable historical proof

Old tour-anchor suite ran on main7ed8944 before changing the test: **9 passed,0 failed,0 skipped** with KALA_TOUR_REQUIRE_DOCS=1. No08 application edit existed at that point, so no old assertion had yet failed because of08. Any old-test failure observed against later approved08 components must be reported as a separate result, not backdated.

All seven original comparisons are retained:

1. components/shell/CourseShell.tsx
2. components/shell/TutorSidebar.tsx
3. features/diagnostic/components/DiagnosticPanel.tsx
4. features/flashcards/components/FlashcardDeck.tsx
5. features/practice/components/PracticePanel.tsx
6. features/tutor/components/TutorComposer.tsx
7. features/twin/components/TwinBody.tsx

TwinBody is the one comparison already using the historical accepted revision, rather than today's body, after WI-25. Its historical proof remains intact. The other six now use that same immutable accepted-tour boundary rather than incorrectly freezing later feature bodies.

Pinned baseline:3a6a0aab27a8212f77b83e96b26127d830a696ba. Accepted TOUR-REFRESH:c3d6b6351f7adbfc6e8da1d43e371014473c8b74. Coordinator independently loaded all14 committed source blobs and repeated the original TypeScript5.9.3 transform: remove only data-tour attributes, print with removeComments:true, compare normalized executable ASTs, and check exactly one added attribute per file. All seven before/after AST SHA-256 pairs match; attributes0→1. Both sides' committed checksums/counts are stored inline in E3, avoiding runtime Git-object dependencies. No checksum was derived from08 components.

The new test enumerates current default/hub student and instructor definitions, main/wait/click/prefill selectors and composite alternatives. **43 selector branches** are checked at their current owner/rendering attribute. Four forwarded/dynamic targets additionally validate caller bindings and exactly one renderer ID. Reused component call sites/mutually exclusive return paths are not mistaken for duplicate runtime DOM nodes. Conditional/route-specific visibility and geometry remain mandatory browser checks, not claims from AST presence. The current Twin anchor check and current PracticePanel Study-spec comment check remain. No skip/only/todo or anchor deletion/rename was added.

New E3 result on main before lane source changes: **53 passed,0 failed,0 skipped**. It also passes53 in a fresh git-archive source export with **no .git directory or history**, using only ignored links to unchanged installed dependencies. No runtime historical Git read is needed. Docs checker0violations/18unit tests and whitespace check pass. Coordinator alone edits E3; lanes fix components if it fails, never the verifier. After T2/U2/TOUR-2 integration rerun E3 and full tour browser, reporting new count next to old616 and zero mutating requests. Those integrated results are still pending.

## Initial audit findings and release constraints

T2 E1 confirms _SYSTEM is one module-level string constant and current router AST matches71c799a. Student guards are present in list_conversations and get_conversation, with ownership resolution preceding detail admission and messages/attachments afterward. Full implementation proof/full API/enrollment suite is pending.

Conditional last-prompt editing is deferred to ITO under TUTOR-REQ-015 / WI-29. Current message rows lack an exchange/revision/idempotency contract; equal timestamps, a frozen concurrent/best-effort ask writer and separate DB operations prevent recoverable replacement in a new function alone. Evidence/mastery references were not the blocker. No edit route/control, partial delete, migration or lock workaround is released.

U2 source audit confirms completion reload resets completion/session cards and clears the posted-rating guard before its refetch. This can resurface already-rated items; a browser reproduction and fix must be separately recorded. The existing review API supplies actual dueAt, dropped by current frontend schema, so a frontend-only date path is available without scheduler/write changes. Missing dates cannot be fabricated.

Workspace material notice is outside the original U2 paths. Fred's named E4 now grants only notice/unused-variable removal after role/07 checks plus proposed attribute-only Next up/Twin-glance anchors. No other query/count/navigation/layout edit. TOUR-2 owns tour definitions/shell/browser tests, not U2. CourseShell tour-start logic/C1 button is reserved for TOUR-2; U2 reports its inventory and makes no competing edit.

FG-L preflight source field finding: user_id_prefix. Hosted presence and latency numbers are not established by source review. Delegated CloudWatch read must either produce privacy-safe aggregates or stop under Fred's exact conditions, without raw data. No config change is authorized. Raw data is local only, not retained.

## Outstanding at this checkpoint

E3/spec commits must be incorporated before lane implementation. T2 dialog/prompt/loading, U2 learning UI/role/corrected completion and TOUR-2 first anchor/no-write feasibility audit are pending. No protected07 path is generally released. TOUR-2 stops before implementation for required protected anchors or a write needed to demonstrate. Its12-step happy/empty/mixed matrix must pass in full; no partial merge.


## T2 reviewed merge and TOUR-2 stop

T2 candidate4da2304 merged locally at3375647 after its clean nine-file report, API1,016/enrollment116/frontend21/E3 53/browser258/web proofs. Coordinator independently normalized only the _SYSTEM string and compared full Tutor AST to base; all other pre-existing code is identical. All19 guard functions are reconciled in the T2 report, not only its two owned handlers. Synthetic dialog layout/focus at375px/1440px was visually reviewed. PID3878 was stopped and5173 released to U2; no unrelated server was stopped. U2 must rebase on this merge before final checks. T2 retains ownership of its mixed browser expectation update after U2 integration.

FG-L actually reached the discovered API group, then stopped on field user_id_prefix. No raw row/value retained; raw data is local only, not retained. Metrics and primary/fallback attribution remain unavailable; no configuration recommendation beyond keeping it unchanged can be justified by this stopped sample.

TOUR-2 initial anchor/source audit is complete, with no implementation. Existing protected Twin/instructor anchors and write-capable destination GETs trigger Fred's Amendment4 stops. Bank status can wake work; Diagnostic can enqueue; Lesson can generate/assign/wake; membership404 fallback and saved-set/next reads can claim/record exposure. Zero POSTs is insufficient. A concrete design-only minimum frontend read-only proposal is requested for Fred's decision; no workaround, synthetic-only guarantee or partial tour merge is released. U2/T2 continue their independent approved work. Existing required protected anchors have not been silently reused or edited. New unprotected anchors remain a proposal until the named resolution.

Fred directly clarified E2 in U2 via Amendment6: not-ready, completed/caught-up and fetch-error/Retry remain distinct. Main0fef4e0 reconciles the shared spec and record. Only material/course-team expected-copy lines may change; all other assertions/fixtures remain frozen.


## Reviewed U2 integration and Amendment7a

U2 candidate795b10f41a634ae5e4b4ed1aee31f6af87cc29f6 rebased onto0f7da69 after T2. Coordinator reviewed26 files, E2's exact two-line exception/E4's staff-only notice condition, preserved98 frozen paths and retained T2/source guard proof, then merged atad7a9acbeefaae05a3a4d6d77a722db5a9179ccb. Role/state copy, Test wording and loading width343px/752px are synthetic-verified. Component21, unit77, U2 browser146, retained H643 and legacy tour616 pass. The original rated-card resurfacing/duplicate-review defect is fixed with a pinned same-scope session and retained posted guard. An intermediate genuine scope-reset regression was reproduced against original/candidate and fixed before merge; all21 final cases pass. Full inventory/manifest is in approval-08-u2.md.

Amendment7a preserves the full codex/tour-rework branch atbeccf5915c4caea045fc5a6e8be2945aaf8812ad and original audit unchanged. Audit SHA-256:e80a3c91f6a0ac85881adcd4d41150da61e01d66dc1a4fa860ce5b98278f80d4. WI-30 is blocked; WI-32 Side-effect-free reads is planned for ITO, listing all dirty GET routes and the database-write/request-side-effect-log proof requirement. No client/store/query-hook read-only mode was authorized or built.

New minimal branch candidate0dbc3e31679bf67594942bcee8ca859c61b93c8c rebased onto U2 and merged ateb3e739795f0f0ece5c9e4568cb68b71216b19c0. Coordinator independently removes the one flag/four render gates and recovers the original CourseShell source byte-for-byte. Instructor source audit traces10 mounted GET handlers/42 reachable functions with SELECT-only database operations, so its code stays unchanged. Role/instructor browser646 assertions passes versus old616, including all27 instructor steps and empty roster. E3 53/routes3 and web checks pass. Lane PID16268/parent16219 stopped;5173 released to T2. Minimal scope/caveats are in approval-08-tour-disable.md. No student twelve-step or production no-write claim.

FG-9 removes student tour walkthrough checks and adds absent offer/manual entry; instructor end-to-end remains because it is retained. Human gates stay FG-6→FG-8→FG-7a/b→FG-9. WI-24/25/26 remain open with owner ITO. No human live row is filled by local proof.

## Integrated source, historical and unit proofs

After T2/U2/minimal shell integration, root full API passes1,016 (30 existing dependency warnings), worker117. Shared conftest disables dotenv, generates a test-only signing key and blocks IPv4/IPv6/DNS. Frontend units21 plus E3/routes56 pass with no skips, Study component21 passes using the external matching renderer fixture. No dependency/config change.

OpenAPI export under that isolation and frontend openapi-typescript regeneration produce zero diff. Independent E1 whole-module AST normalization confirms only one _SYSTEM literal differs from the pre08 source. All19 Amendment7 guarded functions are byte-for-byte AST-identical; seven other routers are byte-identical. The only08 intersections with07 frozen source/test paths are the named E1/E2/E3 exceptions. All37 historical SQL files remain byte-identical to da765cbd; Terraform/infra/CI/Vercel are unchanged. There are no deleted files in08.

E3 reconciliation: old suite on original main was9/0. Against final approved08 source, the unchanged old assertions fail only the six formerly current-body freezes: CourseShell, TutorSidebar, DiagnosticPanel, FlashcardDeck, PracticePanel and TutorComposer. The historical TwinBody proof, current Twin anchor and current PracticePanel comment/attribute checks pass:3 passed/6 expected obsolete-body failures. These are diagnostic old-test results, not a failing current suite. E3's53 current/pinned checks remain intact without skips or Git-history dependencies. All seven original accepted-tour comparisons stay preserved.


## Strict T2 test follow-up and final validation boundary

T2 test-only candidated379004d903fa848ba0954e4ff69ddd8dcae6053 was reviewed and merged atdebe79146783c891e270ac2c2f0fe6dd333dd27e after the minimal tour flag. Its only changed file is the owned mixed browser test. It now enforces zero loading spinners, exact mascot/text/skeleton regions and one model-wait line, plus stable disabled busy upload Send. UTF-8 is explicitly declared in the synthetic fixture. Initial encoding/obsolete-upload-expectation failures and the final267 passing assertions are retained in the T2 report. Units21, E3/routes56 and web checks pass with no added skips or source changes.

Coordinator's sequential integrated browser batch uses one main-aligned Vite server, PID19203, verified cwd and HTTP200 at5173. No other server runs concurrently. Its source revision isdebe791; subsequent edits are documentation-only. Final results are appended only after completion. Synthetic tests cannot advance live FG-9 or infer database-side no-write behavior from HTTP methods.

A fresh git fetch origin reports main75 commits ahead/0behind before this evidence commit. No push, pull/rebase of main, deployment, hosted SQL/data operation, key/config change or worktree deletion occurred.

## Prepared FG-6 handoff

Fred remains the named operator. Use docs/runbooks/0038-apply.md then docs/runbooks/0039-apply.md, with intended environment/revision and pre-checks before apply.0038 tightens22 existing policy expressions on20 tables;0039 adds only the exact(user_id,course_id,created_at DESC,id DESC) index. Existing0001–0037 stay byte-identical. Current checksums:

-0038:aef2053f98368d691bb2735ec6ffbeafc603426b10eef6b24b516f076ad83485.
-0039:d0e727d0ce33eecd12fcbb8a169e7efcb2a649943e925a0434af4f7511a20f95.

Verify0038 final policies and unchanged grants/helpers/views/rows, and0039's exact definition with indisvalid/indisready true. On uncommitted failure, ROLLBACK and investigate. Successful stricter policies are not automatically weakened during an app rollback; fix forward after review. The additive index can remain during app rollback; any removal is a separately reviewed human action. Unknown execution outcomes require inspection before retry, not a blind second apply. Local SQL proof from07 is retained, not recast as hosted proof.

Return sanitized operator/environment/time/revision and pre/post-check pass/fail, with no credentials or user rows. Then review FG-8, not before. Human gates remain FG-6→FG-8→FG-7a/b→FG-9. No closeout completion is declared.

## Exact08 implementation/test/design manifest

- apps/web/src/components/ai-elements/prompt-input.tsx
- apps/web/src/components/shared/BriefLoading.tsx
- apps/web/src/components/shared/LoadingPanel.tsx
- apps/web/src/components/shared/LoadingRegion.tsx
- apps/web/src/components/shell/CourseShell.tsx
- apps/web/src/components/shell/TutorSidebar.tsx
- apps/web/src/components/shell/tests/tour-anchors.test.mjs
- apps/web/src/components/shell/tests/tour.browser.mjs
- apps/web/src/components/study/AnswerableCard.tsx
- apps/web/src/components/study/AssistantBlock.tsx
- apps/web/src/components/study/ComposeDock.tsx
- apps/web/src/components/study/StudyStream.tsx
- apps/web/src/components/study/TopicLanding.tsx
- apps/web/src/components/ui/sonner.tsx
- apps/web/src/features/diagnostic/components/DiagnosticPanel.tsx
- apps/web/src/features/diagnostic/tests/frontend-closeout.browser.mjs
- apps/web/src/features/flashcards/components/FlashcardDeck.tsx
- apps/web/src/features/flashcards/hooks/use-flashcards.ts
- apps/web/src/features/flashcards/schema/flashcards.schema.ts
- apps/web/src/features/flashcards/tests/final-ui-pass.browser.mjs
- apps/web/src/features/flashcards/tests/study-deck.test.mjs
- apps/web/src/features/gamification/components/GamificationSummary.tsx
- apps/web/src/features/instructor/components/DecisionCenter.tsx
- apps/web/src/features/instructor/components/SkillReviewPanel.tsx
- apps/web/src/features/lessons/components/LessonChat.tsx
- apps/web/src/features/practice/components/PracticePanel.tsx
- apps/web/src/features/skill-hub/components/StudyBrowser.tsx
- apps/web/src/features/skill-hub/components/TestBrowser.tsx
- apps/web/src/features/tutor/components/TutorChat.tsx
- apps/web/src/features/tutor/components/TutorComposer.tsx
- apps/web/src/features/tutor/components/TutorConversationRow.tsx
- apps/web/src/features/tutor/components/TutorFileCard.tsx
- apps/web/src/features/tutor/components/TutorFilePreview.tsx
- apps/web/src/features/tutor/components/TutorRenameDialog.tsx
- apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
- apps/web/src/routes/course/index.tsx
- apps/web/src/styles/DESIGN.md
- services/api/app/routers/tutor.py
- services/api/tests/test_tutor_small_talk_approval08.py


## Final merged-main verification — all green

Executed on source revisiondebe79146783c891e270ac2c2f0fe6dd333dd27e; this closing evidence commit changes documentation only. One main-aligned Vite, PID19203/correct cwd/HTTP200, served the nine browser suites sequentially. It was stopped afterward;5173 is released. No pre-existing process was stopped by the coordinator.

| Check / exact runner | Result |
| --- | --- |
| services/api: uv run pytest |1,016 passed;30 existing dependency warnings |
| services/worker: uv run pytest |117 passed |
| Node strip-types frontend/schema/API-error/Tutor/E3/route tests |77 passed,0 failed,0 skipped |
| KALA_STUDY_TEST_DEPS external matching renderer, experimental-vm-modules study-deck.test.mjs |21 passed,0 failed,0 skipped |
| tour.browser.mjs |646 assertions, versus historical616; zero mutating HTTP requests under synthetic fixtures |
| ui-overhaul.browser.mjs |267 assertions, versus initial T2 candidate258 |
| final-ui-pass.browser.mjs |146 assertions; controlled loading/content widths343px/752px |
| frontend-closeout.browser.mjs |114 assertions |
| evidence-history.browser.mjs |80 assertions |
| evidence-history-scope.browser.mjs |16 assertions |
| presentation.browser.mjs |148 assertions |
| read-states.browser.mjs |222 assertions |
| review-feedback.browser.mjs |63 assertions |
| All nine sequential integrated browser suites |1,702 assertions passed |
| pnpm --filter web lint |0 errors;18 existing Fast Refresh warnings |
| pnpm --filter web typecheck / build |PASS; retained circular-dependency/bundle-size warnings |
| Isolated OpenAPI export + openapi-typescript regeneration |PASS; zero generated contract diff |
| python3 scripts/config_inventory.py --check |PASS |
| Config checker unit tests |11 passed |
| python3 scripts/docs_check.py |0 record-link violations,0 unmarked machine-local paths |
| Docs checker unit tests |18 passed |
| E1/19 guards, E2/E4 scope, E3 seven proofs/current anchors, minimal flag restoration |PASS |
|0001–0037 SQL, infra/Terraform/CI/Vercel, original TOUR-2 branch/audit |UNCHANGED |
| File deletions in08 |none |

All UI runs use synthetic fixtures at375px/1440px, with role/error/empty/slow/recovery cases and reduced motion where required. Coordinator visually reviewed synthetic mobile Diagnostic pending feedback: choices disabled, no per-choice spinner and one disabled footer-submit indicator. Renderer/browser fixtures remain external, as recorded by WI-20. Local screenshots are local only, not retained. No real LTI session, provider answer, hosted mutation or deployment was used to fill acceptance.

The API/worker checks preceded the final shell/test-only merges; their source remains identical afterward. Web checks include the minimal shell branch; the later T2 commit changes one browser test only, and that lane freshly reran lint/typecheck/build. This documentation commit does not justify or claim another application rerun.

```text
AUDIT REPORT
Task / brief ID: APPROVAL-08 coordinator, Amendments1–6/7a; E1/E2/E3/E4
Branch and worktree: main; primary repository (local only, not retained)
Base revision: d46e3e482bf07678b73e8aee0199630e2ca0a259
Files changed: exact39-file implementation/test/design manifest above; specs,
  APPROVAL-08/WI records, closeout progress, acceptance checklist and
  coordinator/T2/U2/minimal-tour evidence. No file deletions.
REQ / WI IDs touched: DIAG-REQ-008/012/013/014;
  STUDY-REQ-003/006/007; TUTOR-REQ-005/010/012–016;
  TOUR-REQ-001–008; AUTH-REQ-007 retained; WI-27–33.
Commands run and results: full table above; all final checks green.
Spec changes made: coordinator-first C1/C2, named amendments, conditional
  edit deferral, E3 historical/current boundary, blocked full TOUR-2,
  minimal student hide and retained instructor decision; local proof states
  reconciled after implementation. No human acceptance marked complete.
Evidence added: coordinator report; T2/U2/minimal-disable reports;
  original TOUR-2 audit preserved unchanged; prepared FG-9 rows not run.
Anything not done, and why: no push/deploy/hosted SQL/data repair;
  human FG-6→FG-8→FG-7a/b→FG-9; full TOUR-2 blocked; editing/images planned;
  FG-L stopped on user_id_prefix, timing/attribution unavailable.
Risks or questions for the planner: external renderer/browser fixtures;
  retained dependency/build warnings and history timeout/retest;
  WI-24/25/26 remain open with ITO; source/synthetic evidence is not
  hosted no-write proof or live acceptance. No closeout completion.
Secrets printed: none (confirmed).
```
