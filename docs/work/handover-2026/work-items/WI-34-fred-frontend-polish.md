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

## Instructor tour: Step 15 and the all-27 read-only audit

2026-10-27. Fred adds this before integration and will revisit the live flow after the change. Base: unified-pager commit 5f17777. TOUR-REQ-009 and its change log are specified first. Scope: instructor definitions, tour shell/runner, matching tests, TOUR spec and this report only. No feature decision controls, API, student definitions or Amendment7a flag change. Status: in-progress, owner Codex. No merge is authorized.

Read-only finding before edits: displayed step 15 is array index 14, the skill Approve/Reject explanation at `#tour-skill-approve`. It has optional=true, no click, no explicit waitFor, no studentAction and no completion condition. The runner implicitly polls its selector for 1.2 seconds, then automatically skips and shows a toast instead of a fallback. Step 22 is the separate recommendation decision-button explanation. No current instructor definition requires an Approve/Reject click. The decision controls can be absent when the skill/recommendation list is empty, loading or differently rendered. Synthetic populated fixtures always supply a pending skill proposal and an expanded recommendation, so those anchors exist. Live DOM and deployed source were not inspected, so this is a source-supported conditional-target explanation, not proven live causation.

The audit found zero click-on-write configurations, zero studentAction conditions and zero waitState conditions across all 27 entries. Existing automatic clicks are eight allow-listed local UI/navigation operations. Explicit waitFor entries below observe UI containers rather than a recorded decision. Step 21's conditional recommendation wait is removed from the corrected definitions so analysis is never needed to reach it.

| Step | Target | Existing click/wait | Write action required |
| --- | --- | --- | --- |
| 1 | #tour-cohort-kpis | none | no |
| 2 | #roster-panel | none | no |
| 3 | #tour-roster-search | none | no |
| 4 | #tour-roster-filter | none | no |
| 5 | #tour-roster-first-row | click opens sheet | no |
| 6 | #tour-standing | wait for standing UI | no |
| 7 | #tour-decide-center | none | no |
| 8 | #tour-standing | click sheet-close | no |
| 9 | #at-risk-list | none | no |
| 10 | #cohort-analytics | none | no |
| 11 | #tour-tab-heatmap | click tab | no |
| 12 | #heatmap-panel | wait for heatmap UI | no |
| 13 | #tour-skill-review-trigger | click only if closed | no |
| 14 | #tour-skill-review-panel | wait for review panel | no |
| 15 | #tour-skill-approve | implicit optional target wait only | no |
| 16 | #tour-at-risk-first-flag | click opens record | no |
| 17 | #tour-standing | none | no |
| 18 | #tour-tab-decide | click tab | no |
| 19 | #tour-decide-center | wait for decide UI | no |
| 20 | #tour-run-analysis | implicit target wait only | no |
| 21 | #tour-rec-card | wait for optional recommendation card | no |
| 22 | #tour-decision-buttons | implicit optional target wait only | no |
| 23 | #tour-tab-mastery | click tab | no |
| 24 | #tour-record-radar | wait for radar UI | no |
| 25 | #tour-record-intervene | implicit target wait only | no |
| 26 | #tour-tab-activity | click tab | no |
| 27 | #tour-record-ledger | wait for ledger UI | no |

WI-34-T10 will cover every step with Next in populated/empty and live-like absent/alternate step-15 layouts at both widths, constant 27-step progress, visible highlight/fallback, zero mutating requests, no write/model wait, Back/Skip/Escape and unchanged hidden student entry. E3 remains unedited.

Implementation and verification: the 27-step order and selectors remain. Steps 15, 20, 21, 22 and 25 are immediate informational explanations, with specific fallback copy. Step 21 no longer waits for a recommendation to be created. Instructor Next may activate only the unchanged UI-only allowlist, and active targets cannot be clicked directly through the overlay. Missing targets, including unresolved learner routes in an empty class, show centered same-step fallbacks without invented learners or silent skips. Student behavior/flag is unchanged.

The current tour suite passes 1982 assertions, versus historical TOUR-REFRESH 616 and the earlier retained 646. All 27 steps complete through Next/Done in populated, empty, absent-step-15 and alternate-rendered-step-15 fixtures at both widths. Every step checks progress, highlight/fallback and zero mutations/write-control clicks. Back, dismissal, restart, Skip/Escape and the hidden student entry remain covered. No other click-on-write or write-completion condition was found.

The full sequential regression run after this tour refactor passed all ten browser suites (3258 assertions total), frontend units (50), E3 (53), lint and documentation checks, but production tsc -b found five nullable captured tourStep errors that the separate typecheck command had not reported. Explicit null guards were then added at the two hoisted presentation/action functions. Lint/typecheck/build, E3 plus tour-route units (57 total) and tour.browser (1982) were rerun successfully. No unrelated browser behavior changed in that correction. The earlier build failure is retained at the local result manifest and is resolved, not counted as an original all-green run.

Exploratory tour fixture corrections: after empty-class completion the test now waits for the shell dismissal effect before asserting the first-use banner is gone. A test-local page reference was corrected. Existing dismissal, permission and mutation assertions remain. CourseShell.tsx, student-tour.ts and tour-anchors.test.mjs were compared to parent 5f17777 and are byte-identical. Amendment7a's STUDENT_TOUR_ENABLED=false is untouched.

Evidence logs/screenshots: `/tmp/kala-approval09-final-tour` for the complete sequential pass and its initial build failure, and `/tmp/kala-approval09-tour-final` plus the tour build/unit logs for the corrected checks, local only, not retained. The user will revisit live flow. No live DOM cause was proved, no hosted action was run, and there is no merge/push/deployment. Status: done-awaiting-confirmation for this tour item.

## Instructor tour follow-up: Populated roster without support flags

Fred's live revisit shows steps 17–27 falling back on the class overview after step 16 fails to enter a record. Source cause: step 16 navigates through #tour-at-risk-first-flag. The earlier populated fixture always supplied that flag, and the empty fixture removed both flags and roster rows, so a populated/no-flags class was missing from the matrix. No write is required, but no concrete record route was available to the runner.

TOUR-REQ-009 is amended first. The shell records a visible same-origin Open full record link from the actual roster drawer visited at steps 5–8. Only when step 16 has no flag, Next uses that observed link. It is cleared between runs and never overrides a present flag's existing navigation. No feature files, learner IDs, API fields, student definitions, CourseShell flag or E3 verifier change. WI-34-T11 asserts all 27 steps and actual configured record targets for every step 17–27 with a populated roster and zero flags at both widths, with zero writes. Status: done-awaiting-confirmation.

Verification: build, lint, typecheck, tour-route plus unchanged E3 (57 total tests), tour.browser (2406 assertions), docs checker (188 files, zero violations), documentation units (18) and diff whitespace check pass. No-support-flag record steps 17–27 each have their actual configured target at 375px and 1440px, rather than merely passing fallback. CourseShell.tsx, student-tour.ts and tour-anchors.test.mjs remain byte-identical to 5f17777. Browser artifacts are at `/tmp/kala-approval09-tour-noflags`, local only, not retained. Fred’s live walkthrough remains pending.


## Final integration audit after Fred's tour and drawer follow-ups

2026-10-27. Status for the frontend work in this chat: done-awaiting-confirmation. The user will restart the instructor tour from step 1 and review all 27 steps. The no-support-flag fixture reaches actual learner targets for steps 17–27 at both widths. Student tour remains hidden. The all-27 audit above still applies, with write-adjacent steps 15, 20, 21, 22 and 25 informational and Next driven.

Fred subsequently authorized hosted Supabase CLI counts and explicitly requested that method. Only read-only aggregate queries were run. The current-record results, source windows, resolved presentation fixes, the 14-to-15 approval metadata, closed model-source item and unresolved historical identity limits are recorded in the [INSTR specification](../../../features/instructor-insights/README.md#counts-review-before-implementation). No API, migration, config, hosted application/identity write or merge/push/deploy was performed. This report does not mark WI-24 repaired.

Latest product verification: lint has zero errors and 18 pre-existing warnings. Typecheck and production build pass. Frontend units pass 54, E3 passes 53 with its seven historical proofs unchanged. All ten browser scripts run sequentially, one at a time on the original server PID 40695 at 5173 from this worktree. Corrected final results:

| Browser suite | Assertions |
| --- | --- |
| tour | 2406 |
| frontend-closeout | 114 |
| final-ui-pass | 216 |
| read-states | 314 |
| review-feedback | 63 |
| text-selection | 40 |
| ui-overhaul | 339 |
| evidence-history-scope | 16 |
| evidence-history | 118 |
| presentation | 148 |
| Total | 3774 |

The initial expanded drawer fixture selected the first triage row rather than its intended measured learner, so the truthful unavailable rank caused a fixture timeout. The fixture now searches for its intended learner and the complete 314-assertion read-states suite passes, also proving class rank ignores the displayed roster filter. No product-source correction was needed. This resolved fixture failure is preserved in the original manifest, not overwritten as an original all-green run. The nine other browser results already pass on the same product source.

Local artifacts: `/tmp/kala-approval09-final-instructor` contains the complete sequential run and original fixture failure. `/tmp/kala-approval09-standing-final.log` contains the corrected complete read-states run. `/tmp/kala-approval09-completed-checks.json` combines final counts with the retained original result. All are local only, not retained.

The existing literal data-tour and tour ID anchors are preserved in changed frontend files. CourseShell.tsx, student-tour.ts and tour-anchors.test.mjs remain byte-identical to 9b81f62. Services, packages, infrastructure and configuration have no diff from that frontend preparation revision. Source base remains eb9409a8. The frontend commit sequence is local on codex/fred-polish. Spec/design changes precede implementation, with separate commits for each implementation item and the later tour regression.

Files changed by this frontend round since preparation 9b81f62 (44 paths):

```text
apps/web/src/components/ai-elements/dock-layout.ts
apps/web/src/components/kala/evidence-ledger.tsx
apps/web/src/components/shell/TourRunner.tsx
apps/web/src/components/shell/TutorSidebar.tsx
apps/web/src/components/shell/instructor-tour.ts
apps/web/src/components/shell/tests/tour-route.test.mjs
apps/web/src/components/shell/tests/tour.browser.mjs
apps/web/src/components/study/ComposeDock.tsx
apps/web/src/components/study/StudyColumn.tsx
apps/web/src/components/study/StudyStream.tsx
apps/web/src/components/study/StudySurface.tsx
apps/web/src/components/ui/input.tsx
apps/web/src/features/flashcards/components/FlashcardDeck.tsx
apps/web/src/features/flashcards/tests/final-ui-pass.browser.mjs
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
docs/features/tour/README.md
docs/features/tutor/README.md
docs/features/twin/README.md
docs/work/handover-2026/work-items/WI-34-fred-frontend-polish.md
```

Planner limits: Fred's live flow review remains pending. Invalid upstream percentile arithmetic and configured-primary fallback provenance remain backend findings. Historical legacy anchors were not merged or certified. The separate backend greeting lane and sent-message editing deferral are unchanged. No secrets printed.


## Follow-up: Progress learner selection and open-item review

2026-10-28. Fred finds that empty learners, sorted first in the triage roster, produce empty recommendation and record explanations. The previous single-learner fixture and no-support-flag fix proved navigation but did not cover 23 unstarted learners before two measured learners. TOUR-REQ-009 is amended before code. WI-34-T12 covers selection from the complete cached roster, a progress learner beyond page one, existing filters/search, de-identification, a no-progress roster, both widths, all 27 steps, stable identity and zero writes/model generation. Names are never hard-coded into selection. Status: in-progress.


## Follow-up: Coverage caption and incomplete hint telemetry

2026-10-28. Fred reports Skills covered showing 0 hints used after many Skill hub Give hint actions. INSTR-REQ-013 is specified first. Source shows the counter sums stored evidence hints_used, while flashcard stateless hints and review requests do not carry that count. WI-34-T13 changes the coverage caption to describe evidence coverage and names remaining drawer hint numbers recorded hints. It does not fabricate a total. Complete cross-surface hint tracking stays open for an approved backend contract. No backend/config/data write is authorized here. Status: in-progress for frontend presentation.


## Open-item audit: Original message-copy item

2026-10-28. The catalogue check finds TUTOR-REQ-017 still planned and no message Copy control in TutorChat. This is an uncompleted original APPROVAL-09 frontend item, distinct from the explicitly deferred sent-message editing. The existing spec defines its behavior before implementation. WI-34-T14 covers saved, local/unsaved and optimistic user turns, completed Kala replies, exact per-message clipboard content, denied/unavailable access, deferred success, repeated activation, keyboard/touch and both widths. No API/edit action or shared Study default changes. Status: in-progress.


Progress-selection verification: tour-route plus unchanged E3 pass 58 tests, and tour.browser passes 3264 assertions at 375px/1440px. The new 25-row fixtures put 23 unstarted learners before two learners with progress, start with an excluding search/status filter and de-identification, and expose an unrelated support flag. Triage and record both use the same progress learner. No-progress rosters never request a learner record. Escape restores the original search and status filter. No model/write request or write-control click occurs. An initial test used button semantics for Radix’s single-select filter, which renders radio semantics. The test and selected-state check now use the actual button/data-state contract. No E3 edit. One final no-progress explanatory fallback guard follows the passing browser run and will be checked by the final combined gate.


Message copy implementation uses a Tutor-only wrapper, passing the exact stored/local question or reply string to navigator.clipboard.writeText. Shared Study blocks remain unedited. Controls expose busy/disabled while the promise is pending, confirm Copied only on success, and provide manual-copy/retry direction on denied/unavailable access. Pending Kala placeholders expose no copy action. Copy never submits a form, invokes an API or edits a message. Focused verification passes: clipboard 52 assertions, integrated Tutor 359, Tutor/draft units 13 and production build/lint/typecheck. Final combined checks follow all follow-up edits.


## Follow-up final verification and remaining open items

2026-10-28. Frontend follow-ups WI-34-T12/T13/T14 are done-awaiting-confirmation. Current HEAD before this verification record is 038e9db. Product changes use separate commits: 66080bd progress learner selection, f1baed3 truthful coverage/hints wording and 038e9db message copy. No merge, push or deployment.

The full sequential gate uses the original one-server 5173 worktree setup. Lint has zero errors and 18 existing warnings. Typecheck/build pass, frontend units pass 55 and E3 passes 53. All eleven browser suites pass after two recorded reruns, 4716 assertions total:

| Suite | Assertions |
| --- | --- |
| evidence-history-scope | 16 |
| evidence-history | 118 |
| final-ui-pass | 216 |
| frontend-closeout | 114 |
| message-copy | 52 |
| presentation | 148 |
| read-states | 326 |
| review-feedback | 63 |
| text-selection | 40 |
| tour | 3264 |
| ui-overhaul | 359 |

The new coverage assertion initially ran before the card's asynchronous render and failed. It now waits for the actual 11/15 card before checking its unchanged expected value. The full 326-assertion read-states rerun passes. An existing Rename chat Save interaction timed out once during the integrated Tutor run. The entire Tutor suite then passes 359 assertions unchanged at that interaction. Its exact transient cause is not proved, and the original failure remains recorded. No product patch or forced click was used to hide it. The previous 52-assertion clipboard-only suite and 359-assertion focused Tutor run also passed. The final no-progress tour guard passes in the integrated 3264-assertion tour run.

Artifacts: `/tmp/kala-approval09-followups-final` retains the sequential run including its two initial failures. `/tmp/kala-followup-read-states.log`, `/tmp/kala-followup-tutor.log` and `/tmp/kala-followup-completed-checks.json` retain corrected complete results. All are local only, not retained.

Literal tour/data-tour anchors are preserved. CourseShell.tsx, student-tour.ts, tour-anchors.test.mjs and shared UserBlock/AssistantBlock are byte-identical to 6e09bce. No services, packages, configuration, migration or infrastructure diff from that base. No hosted operation ran in this follow-up.

| Remaining item | State and boundary |
| --- | --- |
| Live 27-step and UI acceptance | Fred restarts from step 1 to verify the progress learner in the actual course. Synthetic success is not live acceptance. |
| Complete Skill hub hint telemetry | Open backend contract/event-semantics work under INSTR-REQ-013. The misleading coverage caption is fixed, but no missing historical count is invented or backfilled. |
| Server percentile arithmetic | Recorded backend finding under INSTR-REQ-012. The frontend class rank is fixed and no longer consumes that invalid percentile. |
| Actual fallback model provenance | Minor ITO finding under INSTR-REQ-006. Stored source still identifies the configured primary when a fallback answered. Fred's paid :floor config confirmation remains closed, with no configuration change. |
| Historical identity repair | WI-24 remains unresolved. No legacy pair/history has been merged or certified by this frontend round. |
| Backend greeting integration and release | Prepared candidate 65e539ab177c632b0b51de6857021a7c1cb42793 exists locally and is not an ancestor of this frontend branch. Combining/releasing it remains the separate planner/Fred gate. No hosted deployment state is inferred. |
| Sent-message editing | Explicitly deferred under TUTOR-REQ-015 / WI-29. Copy is complete and adds no editing. |
| Final integration, push and deploy | Pending separate human authorization and review, not performed here. |

No other unimplemented frontend item from the original APPROVAL-09 catalogue was found in this audit. This does not close the broader project backlog. Follow-up files since 6e09bce (18 paths):

```text
apps/web/src/components/shell/TourRunner.tsx
apps/web/src/components/shell/instructor-tour.ts
apps/web/src/components/shell/tests/tour-route.test.mjs
apps/web/src/components/shell/tests/tour.browser.mjs
apps/web/src/components/shell/tour-learner.ts
apps/web/src/components/shell/tour-route.ts
apps/web/src/features/instructor/components/CohortStats.tsx
apps/web/src/features/instructor/components/LearnerStanding.tsx
apps/web/src/features/instructor/tests/read-states.browser.mjs
apps/web/src/features/tutor/components/TutorChat.test.mjs
apps/web/src/features/tutor/components/TutorChat.tsx
apps/web/src/features/tutor/components/TutorMessage.tsx
apps/web/src/features/tutor/tests/message-copy.browser.mjs
apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
docs/features/instructor-insights/README.md
docs/features/tour/README.md
docs/features/tutor/README.md
docs/work/handover-2026/work-items/WI-34-fred-frontend-polish.md
```
