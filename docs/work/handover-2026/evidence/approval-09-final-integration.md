# APPROVAL-09 final integration — coordinator review

Date: 2026-10-28, Asia/Manila. Local verification only. Base `eb9409a8dc5617f01f9dc20d888775009894ec78`. Fred approved Amendment 2 after the coordinator stopped on the moved frontend revision. Reviewed and frozen frontend: `bdba1601d628897b8ef7de22fcfe6ffde979f43a`. No further commit was made on that branch.

## Review of the six commits after 2b6789f

The six commits are 84ec8eb (instructor chart/transition tour), 777b6f4 (copy controls/tooltips), 953869c (contextual explanation emoji), f4793b1 (prompt recall), eaad954 (lesson scroll layout), bdba160 (freeze/check record). Their 24 paths are exclusively apps/web/src and docs. All changed application paths in the full frontend branch are explicitly listed in WI-34. No backend, migration, infrastructure, CI, Vercel or configuration file is changed by those commits. Updated requirements include TUTOR-REQ-017/021/022, TOUR-REQ-009, LESSON-REQ-006 and DESIGN-REQ-002; their specifications and WI-34 precede/document the implementations.

### 1. E3 coordinator review

The complete historical proof block is byte-identical between 2b6789f and bdba160: before revision `3a6a0aab27a8212f77b83e96b26127d830a696ba`, accepted revision `c3d6b6351f7adbfc6e8da1d43e371014473c8b74`, all seven hash pairs and all comparison assertions unchanged. The seven paths are CourseShell, TutorSidebar, DiagnosticPanel, FlashcardDeck, PracticePanel, TutorComposer and TwinBody. TwinBody is the seventh historical comparison and retains its separate current-anchor check. The current PracticePanel comment check remains.

Every diff in tour-anchors.test.mjs was reviewed by the coordinator. Exactly three current-renderer mappings are added: `#tour-record-readiness`, `#tour-record-readiness-trend`, `#tour-record-activity`, each on its real Card in LearnerRecord. The selector enumerator additionally includes `activateSelector` so read-only tab targets receive the same current ownership/uniqueness checks. No historical comparison, skip/only/todo, weakened assertion, or anchor deletion. Pre-merge and merged E3: 56 passed, no skips. The three added Card IDs account for the 53-to-56 count change.

### 2. Tutor prompt history and adjacent copy polish

Prompt recall is local component/ref state plus a pure helper. It receives only user prompts from the current owned conversation and visible local turns. It adds no storage, SDK, telemetry, network endpoint or backend file. Up/Down and draft edits send nothing; explicit Enter/Send still invokes `onAsk`, then existing `askTutor` at POST /tutor/ask with one question, style, course and optional conversation ID. No raw history array is transmitted to a new service. Existing backend owned-conversation check, enrollment admission, 26-second RequestBudget (including reserve), and email/name-pattern sanitizer remain. Existing history is assembled and sanitized on the server. This is not comprehensive anonymization.

Copy remains the browser clipboard operation, with icon/tooltip/focus/touch feedback and no submit. Emoji/context filtering is a local common-phrase heuristic, not semantic intent classification. Specs retain that limitation. There is no sent-message edit implementation.

### 3. Instructor tours

The tour remains 27 Next/Done-driven steps. The click metadata permits only allowlisted read/navigation UI (tabs, roster selection, filters, sheet close), never a required user click on an approval, analysis, recommendation or intervention control. Those write-adjacent steps are explain-only and use same-step fallbacks. No instructor studentAction/waitState is allowed. Read-only bounded render waits do not await a write. Existing course-roster data supplies the same concrete progress learner through triage/record/Back; no hard-coded identity. New activateSelector entries only open Decide/Mastery/Activity tabs.

Pre-merge browser: 3,386 assertions passed, all 27 steps at 375px and 1440px, populated/empty/partial/no-progress/absent-target cases, zero mutating/model requests and write-control clicks. Student disable flag and CourseShell/student definitions are byte-identical to the original branch base. Merged rerun is recorded below. Network-spy synthetic proof is not a general guarantee that every GET is side-effect free; WI-32 remains open and the student tour stays hidden.

### 4. Lesson scrolling

The diff changes only two className values and adds a comment: full-surface scroller, restored content inset. A TypeScript AST comparison, excluding className attributes, comment-only JSX nodes and formatting, passes. All other executable nodes, props, handlers, data, requests and grading logic are identical. The first printer-based comparison included an empty JSX comment node and failed; the structural comparison accounts for comments explicitly. No product change was made to satisfy the proof.

### 5. Complete scope and merge

Merged frontend, no-name greeting `65e539ab177c632b0b51de6857021a7c1cb42793`, then FG-1b docs `e84cbec89cd46bf954e6a6ec84c9b205132e699c`, in that order. The Tutor spec's two append conflicts require retaining both sides. A failed resolution-script assertion initially left markers committed; a follow-up docs-only correction removes them and retains REQ-017 through REQ-022 exactly once and both changelogs. No source change accompanied that resolution. Final docs/whitespace checks must pass below.

On merged main, replacing only the module-level _SYSTEM value with a sentinel makes the entire tutor.py AST identical to pre-09. All 19 guarded function ASTs remain identical:

| Router | Functions |
| --- | --- |
| courses | get_course, memory_summary |
| twin | get_twin, next_up, learning_plan |
| diagnostic | get_content, list_modules, get_diagnostic_status, get_diagnostic |
| flashcards | skill_cards, deck |
| gamification | summary |
| practice | next_item, list_sets, get_set, get_set_results |
| lessons | get_lesson |
| tutor | list_conversations, get_conversation |

All 39 migration blobs (0001–0039) match the pre-09 baseline byte for byte. No infrastructure, CI, Vercel or config-file changes. The source diff is exactly the approved branches' union; later coordinator additions are documentation only. Backend changes are the one _SYSTEM literal plus the two existing small-talk test assertions. Isolated OpenAPI/types regeneration has zero diff.

## Merged-main check results

| Check | Result |
| --- | --- |
| API, full suite | 1,016 passed, 30 existing warnings |
| Worker, full suite | 117 passed |
| Enrollment matrix | 116 passed, 2 existing warnings |
| Frontend units, including components/routes | 62 passed, no skips |
| E3 | 56 passed, no skips |
| Routes, separately | 5 passed, no skips |
| Web lint | Zero errors, 18 existing warnings |
| Typecheck / build | Pass, existing route-generator/bundle warnings |
| OpenAPI / frontend API types | Isolated regeneration, zero diff |
| Config inventory | Pass |
| Docs / docs unit tests | Zero violations; 18 passed |
| E1 / guard ASTs / migrations | Pass; 19 guards identical; 39 SQL files byte-identical |

| Sequential browser suite | Assertions |
| --- | --- |
| tour | 3,386 |
| frontend-closeout | 114 |
| final-ui-pass | 238 |
| read-states | 326 |
| review-feedback | 63 |
| message-copy | 97 |
| prompt-history | 62 |
| text-selection | 40 |
| ui-overhaul | 383 |
| evidence-history-scope | 16 |
| evidence-history | 118 |
| presentation | 148 |
| Total | 4,991 |

All 12 browser scripts ran sequentially against one main server at 5173. This includes every one of the previously requested 11 plus the new prompt-history suite. Synthetic fixtures intercept external requests; these are not live LTI/provider acceptance. Server transition: frozen Fred worktree PID 40695 stopped; main Vite PID 98534 served HTTP 200, then stopped after checks; no listener remains on 5173. No server remains running from this integration.

Frontend source is byte-identical to bdba160 after integration; only the separately approved backend prompt/test and coordinator documentation differ. A fresh git fetch leaves origin/main at eb9409a8, with local main ahead and its behind count zero. Exact final SHA/ahead count are reported after the final documentation commit, avoiding a self-referential SHA in this file.


External fixture issue: the old configured browser executable was absent, so the initial pre-merge launch failed before assertions. Installed the browser matching the existing external Playwright runtime, without changing repository packages/locks; pre-merge rerun passes. Renderer fixture remains external. Raw execution artifacts are local only, not retained.

## Runtime and publication boundary

The no-name greeting instruction is present on main and requires Fred's make deploy. The previously delegated secret swap was verified separately (26 to 27 entries, other entries unchanged), not applied by this integration. No new live runtime, latency result, deployment, push or cleanup is claimed. Prior closeout text is preserved in approval-08-closeout-before-09.md with relative links adjusted for its record location. The planner draft's 4,716/55/53 values are replaced by this run's actual local counts; live values remain bracketed. Eight 30-second API Lambda kills are not falsely assigned to one lesson route, and an unsupported overall 15.15-second chat median is not promoted from the draft.


## Files in the final integration

Application paths below are the reviewed WI-34 inventory and Amendment 1 paths. Coordinator additions are documentation only.

```text
apps/web/src/components/ai-elements/dock-layout.ts
apps/web/src/components/kala/evidence-ledger.tsx
apps/web/src/components/shell/TourRunner.tsx
apps/web/src/components/shell/TutorSidebar.tsx
apps/web/src/components/shell/instructor-tour.ts
apps/web/src/components/shell/tests/tour-anchors.test.mjs
apps/web/src/components/shell/tests/tour-route.test.mjs
apps/web/src/components/shell/tests/tour.browser.mjs
apps/web/src/components/shell/tour-learner.ts
apps/web/src/components/shell/tour-route.ts
apps/web/src/components/study/ComposeDock.tsx
apps/web/src/components/study/FollowUpChips.tsx
apps/web/src/components/study/StudyColumn.tsx
apps/web/src/components/study/StudyStream.tsx
apps/web/src/components/study/StudySurface.tsx
apps/web/src/components/ui/input.tsx
apps/web/src/features/flashcards/components/FlashcardDeck.tsx
apps/web/src/features/flashcards/tests/final-ui-pass.browser.mjs
apps/web/src/features/instructor/components/CohortStats.tsx
apps/web/src/features/instructor/components/LearnerRecord.tsx
apps/web/src/features/instructor/components/LearnerStanding.tsx
apps/web/src/features/instructor/components/LearnerTriage.tsx
apps/web/src/features/instructor/lib/standing.ts
apps/web/src/features/instructor/tests/learner-counts.discovery.sql
apps/web/src/features/instructor/tests/learner-counts.local.py
apps/web/src/features/instructor/tests/learner-counts.readonly.sql
apps/web/src/features/instructor/tests/read-states.browser.mjs
apps/web/src/features/instructor/tests/standing.test.ts
apps/web/src/features/lessons/components/LessonChat.tsx
apps/web/src/features/plan/components/InstructorPlan.tsx
apps/web/src/features/tutor/components/TutorChat.test.mjs
apps/web/src/features/tutor/components/TutorChat.tsx
apps/web/src/features/tutor/components/TutorComposer.tsx
apps/web/src/features/tutor/components/TutorMessage.tsx
apps/web/src/features/tutor/index.ts
apps/web/src/features/tutor/lib/assigned-draft.ts
apps/web/src/features/tutor/lib/presentation.ts
apps/web/src/features/tutor/lib/prompt-history.ts
apps/web/src/features/tutor/tests/assigned-draft.test.mjs
apps/web/src/features/tutor/tests/message-copy.browser.mjs
apps/web/src/features/tutor/tests/presentation.test.mjs
apps/web/src/features/tutor/tests/prompt-history.browser.mjs
apps/web/src/features/tutor/tests/prompt-history.test.ts
apps/web/src/features/tutor/tests/text-selection.browser.mjs
apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
apps/web/src/features/twin/components/EvidenceHistoryLedger.tsx
apps/web/src/features/twin/tests/evidence-history-scope.browser.mjs
apps/web/src/features/twin/tests/evidence-history.browser.mjs
apps/web/src/styles/DESIGN.md
apps/web/src/styles/globals.css
docs/engineering/runbooks/README.md
docs/engineering/runbooks/fg1b-chat-model-swap.md
docs/features/instructor-insights/README.md
docs/features/lessons/README.md
docs/features/study/README.md
docs/features/tour/README.md
docs/features/tutor/README.md
docs/features/twin/README.md
docs/work/handover-2026/approval-09.md
docs/work/handover-2026/closeout.md
docs/work/handover-2026/evidence/approval-08-closeout-before-09.md
docs/work/handover-2026/evidence/approval-09-clyde-counts.sql
docs/work/handover-2026/evidence/approval-09-final-integration.md
docs/work/handover-2026/evidence/approval-09-no-name-greeting.md
docs/work/handover-2026/evidence/approval-09-privacy-trace.md
docs/work/handover-2026/work-items/WI-14-lesson-request-budget.md
docs/work/handover-2026/work-items/WI-31-tutor-timing-privacy.md
docs/work/handover-2026/work-items/WI-34-fred-frontend-polish.md
services/api/app/routers/tutor.py
services/api/tests/test_tutor_small_talk_approval08.py
```


```text
AUDIT REPORT
Task / brief ID: APPROVAL-09 final integration, Amendment 2; FG-1b docs
Branch and worktree: main; primary Kala checkout (local only, not retained)
Base revision: eb9409a8dc5617f01f9dc20d888775009894ec78
Files changed: complete inventory above; WI-34 frontend, approved prompt/test,
  specifications, DESIGN.md and coordinator documentation only
REQ / WI IDs touched: TUTOR-REQ-017–022; TOUR-REQ-009; LESSON-REQ-006/007;
  TWIN-REQ-003/010/011; INSTR-REQ-010; DESIGN-REQ-001/002; AUTH-REQ-007
  preserved; WI-14, WI-31, WI-34
Commands run and results: full check and browser tables above; E1, scope,
  immutable SQL, whitespace and documentation checks pass
Spec changes made: preserve both approved Tutor additions; reflect local
  integration only, with live acceptance pending
Evidence added: this review/check report; retained pre-09 closeout snapshot;
  WI-14/WI-31 aggregate timeout trace and prior delegated secret-edit record
Anything not done, and why: no deploy, push, hosted write or cleanup in this
  integration. Live/gate values remain bracketed in the DRAFT
Risks or questions for the planner: external fixtures/existing warnings;
  primary-attempt limit, streaming and lesson generation remain ITO work
Secrets printed: none (confirmed)
```
