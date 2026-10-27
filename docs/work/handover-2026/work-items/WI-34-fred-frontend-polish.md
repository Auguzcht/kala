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

## Load older activity: Documentation/source answer

Fred asks whether the extra button has value. Current EvidenceLedger pagination slices only the loaded rows into groups of ten. EvidenceHistoryLedger's separate button fetches another server batch through useEvidenceHistory, normally 25 rows under TWIN-REQ-010. Thus three local pages of 25 loaded events do not include all server history. TWIN-REQ-011 already specifies removing the separate button and fetching the next batch through Next on the final loaded page, preserving keysets, permissions, errors and scope. This behavior remains planned and is not implemented by the three fixes above. This request was a documentation/source check, with no ledger edit made.

Preparation: frontend specs223aa36 committed before edits; web5173/PID40695/HTTP200 verified. Separate prompt candidate65e539a passes API1016, enrollment116, E1 and19-guard proof; it remains unmerged until Fred's UI checks pass. No frontend application edits were made by Codex.
