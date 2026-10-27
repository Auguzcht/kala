---
id: WI-34
status: in-progress
owner: Fred; coordinator for specs/privacy audit/final checks
---

# Fred's direct frontend polish

Source base eb9409a8dc5617f01f9dc20d888775009894ec78; branch codex/fred-polish. Brief: [APPROVAL-09](../approval-09.md). Intended behavior is TUTOR-REQ-017/018, TWIN-REQ-003/010/011, INSTR-REQ-010 presentation and DESIGN-REQ-001/002. Sent-message edit remains deferred, TUTOR-REQ-015 / WI-29.

Coordinator specifies first and prepares the workspace; Fred writes UI code. Web server runs only from this worktree on5173. Existing web configuration uses the deployed API; local interactions can write hosted rows. No second local API is currently needed. If started later with existing env, it also uses hosted Supabase.

Fred classifies Hello Clyde as course material under Amendment1: one embedded AWS101 chunk, all reported own-history/attachment/profile/memory and ownership-mismatch counts zero; no cross-user data reported. Attribution remains limited because request retrieval results are not retained. Queries were prepared and not run by Codex; sanitizer/cache/hosted changes stay prohibited, with only the separate Amendment1 prompt literal/test exception allowed. A cross-user finding stops all work. Course names and ordinary personal names are not comprehensively removed by the existing sanitizer; do not infer source from a greeting alone.

After Fred finishes, coordinator reviews the bounded diff and runs affected browser/E3/web/docs checks, then reports and stops. Fred separately delegates any final push. No code implementation, final acceptance, hosted query or data repair is inferred from setup/specification work.

## Verified by

- [Input trace and unresolved classification](../evidence/approval-09-privacy-trace.md)
- [Prepared COUNT query, not executed](../evidence/approval-09-clyde-counts.sql)

Amendment1 grants the separate _SYSTEM-only backend branch codex/no-name-greeting under TUTOR-REQ-019, with E1 AST/19-guard proof and full API/enrollment tests. This narrow grant supersedes the backend stop only for that literal and existing test extension. Combined integration waits for Fred's frontend completion/checks; no deploy or push is delegated.

## Item 1: Shared column edges

2026-10-27. Fred directly delegates item 1 frontend implementation and a single local commit to Codex in this chat. This supersedes the earlier Fred-only source ownership for this item. DESIGN-REQ-002 was updated first with an observable 1px tolerance, one common ancestor owning the 800px shell and 16px/24px responsive gutters, and a change-log entry. Status: done-awaiting-confirmation for item 1 only. Planner review and Fred's visual confirmation remain pending. Other WI-34 items remain in-progress.

Implementation: StudyColumn owns the shared content inset above both stream and dock. StudySurface and TutorChat use it and supply the inline-size container. StudyStream bleeds to the full surface width, then restores the inherited inset inside its scroller. A persistent native scrollbar does not shift the column. ComposeDock and the shared dock footer no longer add independent horizontal widths/gutters. Tutor empty/conversation/attachment layouts use the same column. Lesson check takeover also removes its redundant gutter because it consumes StudySurface. No action, request, identity, evidence or tour-anchor behavior changes.

### Scenarios and measured evidence

All measurements below are CSS pixels from getBoundingClientRect in Chromium, using the existing worktree server on port 5173 with synthetic auth/API fixtures and external traffic blocked. Study rows cover card, Kala reply, complete action dock row and complete compose dock row. Loading cards have the same edges. Tutor rows cover the Kala message container and composer in empty, conversation and attachment states. Short user bubbles retain their content width and align with the column's right edge. Every corresponding edge difference was 0px.

| Scenario | Viewport | Left | Right | Width |
| --- | --- | --- | --- | --- |
| WI-34-T01: Study full-page card/reply/loading/action/compose | 375 | 72 | 359 | 287 |
| WI-34-T01: Study full-page card/reply/loading/action/compose | 1440 | 372 | 1124 | 752 |
| WI-34-T02: Tutor message/empty/conversation/attachment composer | 375 | 72 | 359 | 287 |
| WI-34-T02: Tutor message/empty/conversation/attachment composer | 1440 | 532 | 1284 | 752 |
| WI-34-T03: U2 full-viewport Study review/all card/reply/action/compose | 375 | 16 | 359 | 343 |
| WI-34-T03: U2 full-viewport Study review/all card/reply/action/compose | 1440 | 344 | 1096 | 752 |

The 56px navigation rail explains the full-page mobile width. U2's full-viewport loading/content widths remain 343px/752px for Study, Test and Diagnostic. Tutor desktop measurements use the default 320px history sidebar. Existing sidebar resize, floating dock overlap, last-action scroll clearance, keyboard and reduced-motion assertions pass. Lesson teaching/dock/check widths match at both viewports with no grading writes.

### Verification and delivery

Files changed in item 1:

```text
apps/web/src/components/study/StudyColumn.tsx
apps/web/src/components/study/StudySurface.tsx
apps/web/src/components/study/StudyStream.tsx
apps/web/src/components/study/ComposeDock.tsx
apps/web/src/components/ai-elements/dock-layout.ts
apps/web/src/features/tutor/components/TutorChat.tsx
apps/web/src/features/lessons/components/LessonChat.tsx
apps/web/src/features/flashcards/tests/final-ui-pass.browser.mjs
apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
apps/web/src/styles/DESIGN.md
docs/work/handover-2026/work-items/WI-34-fred-frontend-polish.md
```

- Source revision: b041201 plus this item's working-tree files, recorded in one local item commit. Environment: local with synthetic browser requests. No hosted requests or writes were made.
- `node apps/web/src/features/flashcards/tests/final-ui-pass.browser.mjs`: 184 assertions passed. Extended DESIGN-REQ-002 checks retain every existing request/idempotency and role assertion. The first added full-page run failed because the synthetic counts request consumed its first deck fixture. The fixture now treats limit=0 as a counts-only request, then the full suite passed.
- `node apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs`: 275 assertions passed, including empty/conversation/attachment edges and preserved sidebar/attachment behavior.
- `node --test apps/web/src/components/shell/tests/tour-anchors.test.mjs`: 53 passed, including all seven unchanged historical E3 proofs.
- `pnpm --filter web lint`: passed with 18 existing Fast Refresh warnings and zero errors. `pnpm --filter web typecheck` and `pnpm --filter web build`: passed. Existing route-generator circular-dependency and bundle-size warnings remain.
- `python3 scripts/docs_check.py` and `python3 -m unittest discover -s scripts -p 'test_docs_check.py'`: passed, 18 documentation unit tests. `git diff --check`: passed.
- Screenshots: `/tmp/kala-approval09-item1-study` and `/tmp/kala-approval09-item1-tutor`, local only, not retained.
- Scope: frontend source, matching browser tests, DESIGN.md and this work item only. No merge, push, deployment, API, migration, hosted or configuration change. Secrets printed: none.

### Scrollbar correction before the item commit

Fred observed a centered native scrollbar in the first implementation despite its passing column measurements. That implementation constrained the scroll region along with the content. DESIGN-REQ-002 was clarified before correcting the code: the scroll region spans the full available surface, while content and dock retain the same inherited inset. The initial 184/275 browser results above did not prove the scrollbar placement.

The added long-conversation fixture checks actual vertical overflow, wheel scrolling in the stream without document movement, page-edge placement, and retained content/composer edges with both native overlay and a forced 16px persistent scrollbar. Its first scroll-ownership assertion raced initial stick-to-bottom animation. The fixture now uses separate saved paragraphs, lets initial scrolling settle and verifies a real upward wheel gesture. No existing permission or data assertion was removed or weakened.

Full-page Study scroller bounds are x=56..375 and x=56..1440. Tutor scroller bounds are x=56..375 and x=376..1440 with the default desktop history sidebar. Thus the native scrollbar is at the viewport's right edge at both widths. Card/reply/dock and loading measurements in the table remain unchanged.

Final correction verification: final-ui-pass.browser.mjs 186 assertions passed and ui-overhaul.browser.mjs 289 assertions passed. All earlier behavioral assertions remain. The table above reflects the corrected implementation. Planner/Fred review is still pending and no merge or publication was performed.

## Text selection: Light-blue highlight

2026-10-27. Fred requests this after the scrollbar correction. Base: item 1 commit 5386c5d. Requirement: DESIGN-REQ-001. Status: done-awaiting-confirmation for this item only. DESIGN.md and its change log were updated before code to specify the same BCD3F4 background and dark ink foreground in both themes. `globals.css` defines semantic selection tokens and a global ::selection rule. The Input primitive removes its local primary-color selection override. Primary and brand values are unchanged.

Files changed: `apps/web/src/styles/DESIGN.md`, `apps/web/src/styles/globals.css`, `apps/web/src/components/ui/input.tsx`, `apps/web/src/features/tutor/tests/text-selection.browser.mjs` and this work item.

WI-34-T04: `node apps/web/src/features/tutor/tests/text-selection.browser.mjs` passed 40 assertions across 375px/1440px and light/dark styles. Real DOM selection of body text, the shared Input used by Rename chat, and Textarea retains the exact native selection range. Computed selection colors are rgb(188, 211, 244) and rgb(14, 27, 51) for every case. No horizontal overflow or runtime errors. The synthetic local fixture blocks all external traffic. Screenshots are in `/tmp/kala-approval09-selection`, local only, not retained. Human visual confirmation remains pending.

Web lint/typecheck/build passed, retaining the same 18 existing lint warnings and route-generator/bundle-size warnings. Documentation checker, 18 documentation unit tests and `git diff --check` passed. No hosted action or configuration change. Secrets printed: none.

## Tutor loading copy: Skeleton-only read states

2026-10-27. Fred requests removal of visible conversation loading text, showing both saved-conversation and history-list loading in the screenshot. Base: text-selection commit a02345c. Requirement TUTOR-REQ-020 and its change log are specified first. WI-34-T05 covers delayed detail/history reads at 375px/1440px, desktop/mobile history, accessible status/busy state, no visible copy or spinner, reduced motion, successful replacement and unchanged mutation counts. Status: in-progress, owner Codex. This item does not alter model waiting messages or error/retry copy.

Implementation complete, status: done-awaiting-confirmation for this item only. TutorChat and TutorSidebar use the existing LoadingRegion status wrapper with descriptive aria-label/aria-busy and skeleton children. The visible loading sentences are removed. Detail uses two existing skeleton blocks and the history list uses three short rows. No spinner was added.

Files changed: `docs/features/tutor/README.md`, `apps/web/src/features/tutor/components/TutorChat.tsx`, `apps/web/src/components/shell/TutorSidebar.tsx`, `apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs` and this work item.

`node apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs` passed 295 assertions, preserving its existing data/recovery/sidebar/attachment/scrollbar checks. New held list/detail requests prove empty visible status text, accessible labels/busy state, skeleton-only desktop/mobile history, static reduced-motion skeletons, no spinner and no create/ask/upload/patch/delete. Both loading regions disappear on successful reads. Screenshots are in `/tmp/kala-approval09-skeleton`, local only, not retained.

Web lint/typecheck/build passed with the same 18 existing lint warnings and route-generator/bundle-size warnings. E3/tour anchors: 53 passed, including all seven unmodified historical proofs. Documentation checker, 18 documentation unit tests and `git diff --check` passed. Synthetic local requests only. Human review remains pending. No merge, push, hosted/configuration change or deployment. Secrets printed: none.

## Load older activity: Initial documentation/source answer

Fred asks whether the extra button has value. Current EvidenceLedger pagination slices only the loaded rows into groups of ten. EvidenceHistoryLedger's separate button fetches another server batch through useEvidenceHistory, normally 25 rows under TWIN-REQ-010. Thus three local pages of 25 loaded events do not include all server history. TWIN-REQ-011 already specifies removing the separate button and fetching the next batch through Next on the final loaded page, preserving keysets, permissions, errors and scope. This behavior remains planned and is not implemented by the three fixes above. This request was a documentation/source check, with no ledger edit made.

## Follow-up actions: Explicit Tutor requests and Study user turns

2026-10-27. Fred requests explanation chips that ask for the chosen treatment of the previous answer and visible student turns for flashcard hint/explain actions. Base 74e5f92. TUTOR-REQ-021 and STUDY-REQ-008 are specified first with change-log entries. This is one follow-up interaction item, kept in one local commit. Frontend only. Scope: TutorChat, FlashcardDeck, their matching tests and the owning specs/work item. No API, provider, migration, configuration or hosted change. Status: in-progress, owner Codex.

WI-34-T06 covers Tutor chip request text/style/conversation, immediate user bubble, saved/reopened/returned-unsaved answers, retry and scope changes. WI-34-T07 covers ordered Study hint/explain/freeform turns, pending/error/retry, front-side answer protection, repeated actions and late replies after card changes. Existing browser loading/geometry/anchors, Study review/idempotency and Tutor recovery remain required checks.

Implementation complete, status: done-awaiting-confirmation for this item only. Tutor chips now submit explicit instructions about the last answer with the existing eli5/detail styles and active conversation ID. They also work after reopening a saved chat. Returned-unsaved answer text is included in the next request when needed, with the user bubble showing exactly the submitted question. No original question is silently resent. Study keeps one ordered local assistance thread for hint, explain and typed actions. A student bubble appears before each pending answer, repeated actions retain their own turns, a failure retains its request with Retry, and captured request text/style are reused without duplicating that user turn. Card/session changes clear the thread and reject stale callbacks. Front-side hint requests exclude the back, while explanations include the revealed card context. Existing stateless/persisted ask contracts are reused.

Files changed:

```text
docs/features/tutor/README.md
docs/features/study/README.md
docs/work/handover-2026/work-items/WI-34-fred-frontend-polish.md
apps/web/src/features/tutor/components/TutorChat.tsx
apps/web/src/features/tutor/components/TutorChat.test.mjs
apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
apps/web/src/features/flashcards/components/FlashcardDeck.tsx
apps/web/src/features/flashcards/tests/final-ui-pass.browser.mjs
```

Verification at base 74e5f92 plus these working-tree paths, local environment:

- `ui-overhaul.browser.mjs`: 317 assertions passed at 375px/1440px. New explicit follow-up requests/styles/conversation IDs, immediate student turns, no copied original question, one pending indicator and exact retry payload pass. Existing loading, sidebar, attachment, recovery and scrollbar assertions remain.
- `final-ui-pass.browser.mjs`: 216 assertions passed at 375px/1440px. New hint/explain/freeform turn order, styles/context, pending/error/retry, repeated/double activation, last-answer clearance and late-response/card-reset cases pass. Original review/idempotency, loading-width and geometry assertions remain.
- `node --experimental-vm-modules --test` for TutorChat.test.mjs, tutor.schema.test.ts, api-error.test.ts and presentation.test.mjs: 23 passed. Added reopened saved-chat and returned-unsaved follow-up tests pass, alongside existing answer-recovery tests.
- `study-deck.test.mjs` with the documented external renderer fixture: 21 passed. Existing review/replay/scope/idempotency cases are unchanged.
- `node --test apps/web/src/components/shell/tests/tour-anchors.test.mjs`: 53 passed, including seven untouched historical E3 proofs.
- Web lint/typecheck/build passed. Lint retains 18 existing warnings. Route-generator circular-dependency and bundle-size warnings remain.
- Documentation checker, 18 documentation unit tests and `git diff --check` passed.
- Screenshots: `/tmp/kala-approval09-followups-tutor` and `/tmp/kala-approval09-followups-study`, local only, not retained. Browser fixtures block external traffic and intercept synthetic auth/API requests. No hosted or real provider request was run. Live explanation quality and human click-through remain unverified.

No backend, API schema, migration, configuration, hosted data or sent-message editing change. No merge, push or deployment. Secrets printed: none.

## Assigned Tutor Start: Fresh editable topic draft

2026-10-27. Fred requests that dashboard From your instructor / Start open a new Tutor chat with the relevant topic already in the composer, waiting for Enter or Send. Base: 44599f0. TUTOR-REQ-018 and INSTR-REQ-007 presentation are updated first with change-log entries. Status: in-progress, owner Codex. This item stays frontend-only and receives one local commit.

WI-34-T08 covers assigned skill/title fallback, editable focused draft, no automatic resume or mutations, repeated/reopened navigation, New chat and saved-chat selection, invalid/other-course handoff rejection, unchanged non-Tutor destinations, and first explicit Enter/Send creating only the new conversation and one ask. Fred also requests final lint/typecheck/build, frontend units, E3, every browser suite sequentially against the one existing 5173 server, then documentation checks and a cumulative report.

Implementation: InstructorPlan uses Tutor's public draft factory, then passes a single fresh handoff through browser history state and clears conversation search state. The handoff schema rejects malformed/other-course state. TutorChat suppresses auto-resume for this entry and owns an explicit composer-session key so query re-renders do not remount an edited draft. TutorComposer seeds local text once and autofocuses it. Existing lazy creation and explicit Send/Enter remain the only mutation trigger. No URL prompt, note/profile payload, local-storage draft, recommendation completion or tour change.

Files: InstructorPlan.tsx, Tutor's public index, lib/assigned-draft.ts, TutorChat.tsx, TutorComposer.tsx, TutorChat.test.mjs, tests/assigned-draft.test.mjs, ui-overhaul.browser.mjs, Tutor/Instructor specifications and this work item. Scoped verification: Tutor browser 339 assertions passed, focused Tutor/draft units 13 passed, lint/typecheck passed with the same existing warnings. The first extra practice-destination assertion expected the legacy intermediate URL. It was corrected to the existing practice route's Skills redirect, then passed. Final combined regression gate remains pending until the separately requested ledger item is complete.

## Unified evidence pagination

2026-10-27. Fred confirms the separate Load older activity button should be replaced by Next. Base 9c24b4a. TWIN-REQ-011 is clarified first with its change log: fetching into a partial terminal page fills that page before advancing so the 25-row server batch does not cause unseen events to be skipped. Existing TWIN-REQ-003/010 and INSTR-REQ-010 presentation apply. Status: in-progress, owner Codex. One local commit for this item and the final cumulative regression evidence.

WI-34-T09 covers loaded-page navigation, delayed/successful boundary fetch, duplicate clicks, full/partial terminal pages, empty/duplicate-only batches without loops, genuine end, errors/Retry/Reload, Previous during fetch, and student/instructor role/account/course/learner isolation. Preserve the history hook, backend limits/cursors, deduplication, H fixtures and all permission/data assertions. No API, migration, configuration or hosted change.

## Historical preparation checkpoint

Preparation: frontend specs223aa36 committed before edits; web5173/PID40695/HTTP200 verified. Separate prompt candidate65e539a passes API1016, enrollment116, E1 and19-guard proof; it remains unmerged until Fred's UI checks pass. At that preparation checkpoint, no frontend application edits had been made by Codex. The implementation and final frontend verification below supersede that preparation-only state.

## Final cumulative frontend verification

2026-10-27. Every item directly requested in this chat is implemented locally and done-awaiting-confirmation. This does not mark the entire WI-34/APPROVAL-09 catalogue complete or establish hosted acceptance. The assigned-start and unified-pager items above have now passed the combined frontend gate. Planner review and Fred's visual/live acceptance remain pending.

Source: frontend item commits 5386c5d, a02345c, 74e5f92, 44599f0 and 9c24b4a plus the final unified-pager working-tree paths committed with this report. Original requested branch base eb9409a8. The six frontend item commits follow the existing preparation commit 9b81f62. No source edits were made during the full check run. The original Vite process 40695 remained the sole listener on 5173 and served this worktree throughout. All browser requests used synthetic auth/API interception with external traffic blocked.

| Item | Delivered behavior | Commit |
| --- | --- | --- |
| Shared column and scrollbar correction | Study card/reply/dock and Tutor messages/composer share edges. Native scrollbar remains at the page's right edge. U2 full-viewport loading/content widths remain 343px/752px. | 5386c5d |
| Text selection | BCD3F4 background with dark ink text for body/Input/Textarea in light and dark styles. Primary brand values unchanged. | a02345c |
| Tutor read loading | Conversation and history show skeletons with accessible status/busy labels, without visible loading sentences. | 74e5f92 |
| Tutor/Study follow-ups | Explicit last-answer Tutor instructions with existing styles. Study hint/explain/typed actions produce ordered user/Kala pairs with scoped retry. | 44599f0 |
| Assigned Tutor Start | Fresh editable topic draft, focused dock, no auto-resume/send, and lazy create/ask only after Enter/Send. | 9c24b4a |
| Unified evidence pagination | Separate older button removed. Next loads batches, handles partial pages without skipping new events, guards duplicate fetches and preserves error/identity/scope behavior. | This report's item commit, parent 9c24b4a |

Final commands ran in Fred's requested order: web lint, typecheck, build, every frontend unit file, E3, all ten current browser suites sequentially, docs checker, documentation units and diff whitespace check. All 18 command stages passed.

- `pnpm --filter web lint`: pass, zero errors and 18 pre-existing Fast Refresh warnings.
- `pnpm --filter web typecheck`: pass. Existing route-generator circular-dependency warning remains.
- `pnpm --filter web build`: pass. Existing large-bundle warning remains.
- `node --experimental-vm-modules --test` for all seven non-E3 frontend unit files: 49 passed, zero failed/skipped. The external Study renderer fixture was supplied using the documented environment variable.
- `node --test apps/web/src/components/shell/tests/tour-anchors.test.mjs`: 53 passed, including all seven unmodified historical E3 proofs.
- `python3 scripts/docs_check.py`: pass, 188 documentation files, zero machine-path or record-link violations.
- `python3 -m unittest discover -s scripts -p 'test_docs_check.py'`: 18 passed.
- `git diff --check`: pass.

| Browser suite in sequential run order | Assertions passed |
| --- | ---: |
| components/shell/tests/tour.browser.mjs | 646 |
| features/diagnostic/tests/frontend-closeout.browser.mjs | 114 |
| features/flashcards/tests/final-ui-pass.browser.mjs | 216 |
| features/instructor/tests/read-states.browser.mjs | 222 |
| features/instructor/tests/review-feedback.browser.mjs | 63 |
| features/tutor/tests/text-selection.browser.mjs | 40 |
| features/tutor/tests/ui-overhaul.browser.mjs | 339 |
| features/twin/tests/evidence-history-scope.browser.mjs | 16 |
| features/twin/tests/evidence-history.browser.mjs | 118 |
| features/twin/tests/presentation.browser.mjs | 148 |
| Total | 1922 |

Browser paths are relative to apps/web/src. Both 375px and 1440px and the suites' existing reduced-motion/keyboard cases are retained. The ledger adaptation replaces obsolete separate-load-button interactions with Next under TWIN-REQ-011. The initial own-history error assertion expected ten visible rows on page one, while the new fetch occurs on the five-row terminal page. It now compares the exact pre-failure visible rows, strengthening retention proof. Staff hiding, denials, scope/cursor, deduplication and request-limit assertions remain intact. Empty and duplicate-only batches do not advance or loop. The evidence-history hook and API are unchanged.

Logs, result manifest and synthetic screenshots: `/tmp/kala-approval09-final`, local only, not retained. No real provider response quality, live LMS flow or hosted migration/deployment is inferred from these local checks. No merge, push, API/backend/migration/configuration/hosted-data change or deployment was performed. Secrets printed: none.

### Cumulative files changed

30 paths across the six frontend items, relative to the existing preparation commit 9b81f62:

```text
apps/web/src/components/ai-elements/dock-layout.ts
apps/web/src/components/kala/evidence-ledger.tsx
apps/web/src/components/shell/TutorSidebar.tsx
apps/web/src/components/study/ComposeDock.tsx
apps/web/src/components/study/StudyColumn.tsx
apps/web/src/components/study/StudyStream.tsx
apps/web/src/components/study/StudySurface.tsx
apps/web/src/components/ui/input.tsx
apps/web/src/features/flashcards/components/FlashcardDeck.tsx
apps/web/src/features/flashcards/tests/final-ui-pass.browser.mjs
apps/web/src/features/lessons/components/LessonChat.tsx
apps/web/src/features/plan/components/InstructorPlan.tsx
apps/web/src/features/tutor/components/TutorChat.test.mjs
apps/web/src/features/tutor/components/TutorChat.tsx
apps/web/src/features/tutor/components/TutorComposer.tsx
apps/web/src/features/tutor/index.ts
apps/web/src/features/tutor/lib/assigned-draft.ts
apps/web/src/features/tutor/tests/assigned-draft.test.mjs
apps/web/src/features/tutor/tests/text-selection.browser.mjs
apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
apps/web/src/features/twin/components/EvidenceHistoryLedger.tsx
apps/web/src/features/twin/tests/evidence-history-scope.browser.mjs
apps/web/src/features/twin/tests/evidence-history.browser.mjs
apps/web/src/styles/DESIGN.md
apps/web/src/styles/globals.css
docs/features/instructor-insights/README.md
docs/features/study/README.md
docs/features/tutor/README.md
docs/features/twin/README.md
docs/work/handover-2026/work-items/WI-34-fred-frontend-polish.md
```
