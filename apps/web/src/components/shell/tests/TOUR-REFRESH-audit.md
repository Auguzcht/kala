# TOUR-REFRESH static audit

Base: `3a6a0aab27a8212f77b83e96b26127d830a696ba`. Audited before implementation. Existence means a source anchor, not unconditional rendering. Every conditional anchor requires a runtime skip.

## Student saved

| Step | Route | Target | Exists in base? | Copy/current-state finding |
| --- | --- | --- | --- | --- |
| 1 | `/course/diagnostic` | `#tour-diagnostic-card` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 2 | `/course/diagnostic` | `#tour-diagnostic-choices` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 3 | `/course/diagnostic` | `#tour-diagnostic-submit` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 4 | `/course/skill/prepared` | `#tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 5 | `/course/skill/prepared` | `#tour-lesson-dock-toggle` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 6 | `/course/skill/prepared` | `#tour-lesson-dock-input` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 7 | `/course/skill/prepared` | `#tour-lesson-dock-toggle` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 8 | `/course/skill/prepared` | `#tour-lesson-continue` | Yes, conditional | Current; conditional target must skip when absent. |
| 9 | `/course/skill/prepared` | `#tour-lesson-check, #tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 10 | `/course/skill/prepared` | `#tour-lesson-check-feedback, #tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 11 | `/course/skill/prepared` | `#tour-study-actions` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 12 | `/course/skill/prepared` | `#tour-study-dock` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 13 | `/course/skill/prepared` | `#tour-study-dock-toggle` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 14 | `/course/skill/prepared` | `#tour-study-dock-input` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 15 | `/course/skill/prepared` | `#tour-study-dock-toggle` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 16 | `/course/skill/prepared` | `#tour-study-dock` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 17 | `/course/skill/prepared` | `#tour-test-start` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 18 | `/course/skill/prepared` | `#tour-practice-choices` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 19 | `/course/skill/prepared` | `#tour-practice-feedback` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 20 | `/course/skill/prepared` | `#tour-test-dock-toggle` | Generated dock anchor / inspect runtime | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 21 | `/course/skill/prepared` | `#tour-test-dock-input` | Generated dock anchor / inspect runtime | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 22 | `/course/skill/prepared` | `#tour-test-dock-toggle` | Generated dock anchor / inspect runtime | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 23 | `/course/tutor` | `#tour-tutor-input` | Yes, conditional | Draft-only sample current; missing history groups/rename-pin, new chat, attach/filedrop and thinking explanation. |
| 24 | `/course/tutor` | `#tour-tutor-response, #tour-tutor-input` | Yes, conditional | Draft-only sample current; missing history groups/rename-pin, new chat, attach/filedrop and thinking explanation. |
| 25 | `/course/twin` | `#tour-twin-readiness` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
| 26 | `/course/twin` | `#tour-twin-radar` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
| 27 | `/course/twin` | `#tour-twin-activity` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
## Student without saved set

| Step | Route | Target | Exists in base? | Copy/current-state finding |
| --- | --- | --- | --- | --- |
| 1 | `/course/diagnostic` | `#tour-diagnostic-card` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 2 | `/course/diagnostic` | `#tour-diagnostic-choices` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 3 | `/course/diagnostic` | `#tour-diagnostic-submit` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 4 | `/course/skill/prepared` | `#tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 5 | `/course/skill/prepared` | `#tour-lesson-dock-toggle` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 6 | `/course/skill/prepared` | `#tour-lesson-dock-input` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 7 | `/course/skill/prepared` | `#tour-lesson-dock-toggle` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 8 | `/course/skill/prepared` | `#tour-lesson-continue` | Yes, conditional | Current; conditional target must skip when absent. |
| 9 | `/course/skill/prepared` | `#tour-lesson-check, #tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 10 | `/course/skill/prepared` | `#tour-lesson-check-feedback, #tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 11 | `/course/skill/prepared` | `#tour-study-actions` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 12 | `/course/skill/prepared` | `#tour-study-dock` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 13 | `/course/skill/prepared` | `#tour-study-dock-toggle` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 14 | `/course/skill/prepared` | `#tour-study-dock-input` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 15 | `/course/skill/prepared` | `#tour-study-dock-toggle` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 16 | `/course/skill/prepared` | `#tour-study-dock` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 17 | `/course/skill/prepared` | `#tour-test-new-set` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 18 | `/course/skill/prepared` | `#tour-test-start` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 19 | `/course/skill/prepared` | `#tour-practice-choices` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 20 | `/course/skill/prepared` | `#tour-practice-feedback` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 21 | `/course/skill/prepared` | `#tour-test-dock-toggle` | Generated dock anchor / inspect runtime | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 22 | `/course/skill/prepared` | `#tour-test-dock-input` | Generated dock anchor / inspect runtime | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 23 | `/course/skill/prepared` | `#tour-test-dock-toggle` | Generated dock anchor / inspect runtime | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 24 | `/course/tutor` | `#tour-tutor-input` | Yes, conditional | Draft-only sample current; missing history groups/rename-pin, new chat, attach/filedrop and thinking explanation. |
| 25 | `/course/tutor` | `#tour-tutor-response, #tour-tutor-input` | Yes, conditional | Draft-only sample current; missing history groups/rename-pin, new chat, attach/filedrop and thinking explanation. |
| 26 | `/course/twin` | `#tour-twin-readiness` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
| 27 | `/course/twin` | `#tour-twin-radar` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
| 28 | `/course/twin` | `#tour-twin-activity` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
## Student completed sets

| Step | Route | Target | Exists in base? | Copy/current-state finding |
| --- | --- | --- | --- | --- |
| 1 | `/course/diagnostic` | `#tour-diagnostic-card` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 2 | `/course/diagnostic` | `#tour-diagnostic-choices` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 3 | `/course/diagnostic` | `#tour-diagnostic-submit` | Yes, conditional | Answering only; completed/caught-up screen absent. Submit is observational; no modal. Header/results not covered. |
| 4 | `/course/skill/prepared` | `#tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 5 | `/course/skill/prepared` | `#tour-lesson-dock-toggle` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 6 | `/course/skill/prepared` | `#tour-lesson-dock-input` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 7 | `/course/skill/prepared` | `#tour-lesson-dock-toggle` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 8 | `/course/skill/prepared` | `#tour-lesson-continue` | Yes, conditional | Current; conditional target must skip when absent. |
| 9 | `/course/skill/prepared` | `#tour-lesson-check, #tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 10 | `/course/skill/prepared` | `#tour-lesson-check-feedback, #tour-lesson-explain` | Yes, conditional | Current; conditional target must skip when absent. |
| 11 | `/course/skill/prepared` | `#tour-study-actions` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 12 | `/course/skill/prepared` | `#tour-study-dock` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 13 | `/course/skill/prepared` | `#tour-study-dock-toggle` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 14 | `/course/skill/prepared` | `#tour-study-dock-input` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 15 | `/course/skill/prepared` | `#tour-study-dock-toggle` | Generated dock anchor / inspect runtime | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 16 | `/course/skill/prepared` | `#tour-study-dock` | Yes, conditional | Recall/rating conditional; missing end-of-deck Go through these again / Check for more cards distinction. |
| 17 | `/course/skill/prepared` | `#tour-test-menu` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 18 | `/course/skill/prepared` | `#tour-test-new-set` | Yes, conditional | Conditional preview/questions/feedback; completed result score, review and retake controls not covered. |
| 19 | `/course/tutor` | `#tour-tutor-input` | Yes, conditional | Draft-only sample current; missing history groups/rename-pin, new chat, attach/filedrop and thinking explanation. |
| 20 | `/course/tutor` | `#tour-tutor-response, #tour-tutor-input` | Yes, conditional | Draft-only sample current; missing history groups/rename-pin, new chat, attach/filedrop and thinking explanation. |
| 21 | `/course/twin` | `#tour-twin-readiness` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
| 22 | `/course/twin` | `#tour-twin-radar` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
| 23 | `/course/twin` | `#tour-twin-activity` | Yes, conditional | Instrument exists; activity copy overstates live updates; recent evidence ledger missing. |
## Instructor

| Step | Route | Target | Exists in base? | Copy/current-state finding |
| --- | --- | --- | --- | --- |
| 1 | `/class` | `#tour-cohort-kpis` | Yes, conditional | Current; conditional target must skip when absent. |
| 2 | `/class` | `#roster-panel` | Yes, conditional | Current; conditional target must skip when absent. |
| 3 | `/class` | `#tour-roster-search` | Yes, conditional | Current; conditional target must skip when absent. |
| 4 | `/class` | `#tour-roster-filter` | Yes, conditional | Current; conditional target must skip when absent. |
| 5 | `/class` | `#tour-roster-first-row` | Yes, conditional | Current; conditional target must skip when absent. |
| 6 | `/class` | `#tour-standing` | Yes, conditional | Current; conditional target must skip when absent. |
| 7 | `/class` | `#tour-decide-center` | Yes, conditional | Current; conditional target must skip when absent. |
| 8 | `/class` | `#tour-standing` | Yes, conditional | Current; conditional target must skip when absent. |
| 9 | `/class` | `#at-risk-list` | Yes, conditional | Current; conditional target must skip when absent. |
| 10 | `/class` | `#cohort-analytics` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 11 | `/class` | `#tour-tab-heatmap` | Yes, conditional | Current; conditional target must skip when absent. |
| 12 | `/class` | `#heatmap-panel` | Generated dock anchor / inspect runtime | Current; conditional target must skip when absent. |
| 13 | `/class` | `#tour-skill-review-trigger` | Yes, conditional | Current; conditional target must skip when absent. |
| 14 | `/class` | `#tour-skill-review-panel` | Yes, conditional | Current; conditional target must skip when absent. |
| 15 | `/class` | `#tour-skill-approve` | Yes, conditional | Current; conditional target must skip when absent. |
| 16 | `/class` | `#tour-at-risk-first-flag` | Yes, conditional | Current; conditional target must skip when absent. |
| 17 | `/class/student/$uid` | `#tour-standing` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 18 | `/class/student/$uid` | `#tour-tab-decide` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 19 | `/class/student/$uid` | `#tour-decide-center` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 20 | `/class/student/$uid` | `#tour-run-analysis` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 21 | `/class/student/$uid` | `#tour-rec-card` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 22 | `/class/student/$uid` | `#tour-decision-buttons` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 23 | `/class/student/$uid` | `#tour-tab-mastery` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 24 | `/class/student/$uid` | `#tour-record-radar` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 25 | `/class/student/$uid` | `#tour-record-intervene` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 26 | `/class/student/$uid` | `#tour-tab-activity` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |
| 27 | `/class/student/$uid` | `#tour-record-ledger` | Yes, conditional | Current; conditional target must skip when absent. Runner route matcher currently compares literal $uid and cannot resume. |

## Coverage decisions

No starter-suggestion, sidebar-collapse or Diagnostic-modal step exists in this base; none will be introduced. Tutor thinking is transient and described with the response area rather than waiting for a model request. Attach and conversation management are highlights only. Study end controls and Test/Diagnostic results are optional highlights and never reached by automatic answers, ratings or submission. The tour keeps navigation/UI toggles only. No hosted state or provider claims.

## Refreshed definitions

The frozen pre-change matrices above retain every original step and finding. The tables below enumerate every current step after the refresh. Each target is validated separately at runtime; optional states are never created to make a highlight available. Normal student walks skip the Diagnostic result, running/completed Study deck and Test preview/result targets when those states are absent. Their source anchors exist in the appropriate conditional branch. Desktop and mobile history use the first visible matching target, rather than the hidden desktop copy.

### Student (one prepared topic; saved/completed/no-set variants)

| Step | Route/search | Target | Current copy/interaction | Missing target |
| --- | --- | --- | --- | --- |
| 1 | `/course/diagnostic` | `[data-tour="diagnostic-header"]` | Find your starting point; Highlight only | Bounded optional skip |
| 2 | `/course/diagnostic` | `#tour-diagnostic-choices` | Answer at your pace; Highlight only | Bounded optional skip |
| 3 | `/course/diagnostic` | `[data-diagnostic-results]` | Your baseline results; Highlight only | Bounded optional skip |
| 4 | `/course/skill/prepared {"tab":"lesson"}` | `#tour-lesson-explain` | Learn one topic; Highlight only | Bounded optional skip |
| 5 | `/course/skill/prepared` | `#tour-lesson-dock-toggle` | Ask about this topic; Highlight only | Bounded optional skip |
| 6 | `/course/skill/prepared {"tab":"study"}` | `#tour-study-actions` | Study this topic; Highlight only | Bounded optional skip |
| 7 | `/course/skill/prepared` | `#tour-study-dock` | Recall and review; Highlight only | Bounded optional skip |
| 8 | `/course/skill/prepared` | `[data-tour="study-complete"]` | At the end of a deck; Highlight only | Bounded optional skip |
| 9 | `/course/skill/prepared {"tab":"test","setId":"saved"}` | `#tour-test-menu` | Your saved tests; Highlight only | Bounded optional skip |
| 10 | `/course/skill/prepared` | `#tour-test-start` | Start when you are ready; Highlight only | Bounded optional skip |
| 11 | `/course/skill/prepared` | `[data-tour="test-results"]` | Review your results; Highlight only | Bounded optional skip |
| 12 | `/course/tutor` | `#tour-tutor-input` | Ask Kala; Empty-draft prefill only | Bounded skip |
| 13 | `/course/tutor` | `[data-tour="tutor-history"], [data-tour="tutor-history-mobile"]` | Keep track of your chats; Highlight only | Bounded skip |
| 14 | `/course/tutor` | `[data-tour="tutor-attach"]` | Attach course material; Highlight only | Bounded skip |
| 15 | `/course/twin` | `#tour-twin-readiness` | Your learning, measured; Highlight only | Bounded skip |
| 16 | `/course/twin` | `#tour-twin-radar` | Explore your skill profile; Highlight only | Bounded skip |
| 17 | `/course/twin` | `[data-tour="twin-ledger"]` | Read the evidence; Highlight only | Bounded skip |

### Instructor

| Step | Route/search | Target | Current copy/interaction | Missing target |
| --- | --- | --- | --- | --- |
| 1 | `/class` | `#tour-cohort-kpis` | Your class, measured; Highlight only | Bounded skip |
| 2 | `/class` | `#roster-panel` | Class roster; Highlight only | Bounded skip |
| 3 | `/class` | `#tour-roster-search` | Class roster; Highlight only | Bounded skip |
| 4 | `/class` | `#tour-roster-filter` | Class roster; Highlight only | Bounded skip |
| 5 | `/class` | `#tour-roster-first-row` | Triage a learner; UI-only click: #tour-roster-first-row | Bounded optional skip |
| 6 | `/class` | `#tour-standing` | Triage a learner; Highlight only | Bounded optional skip |
| 7 | `/class` | `#tour-decide-center` | The gate; Highlight only | Bounded optional skip |
| 8 | `/class` | `#tour-standing` | Triage a learner; UI-only click: [data-slot='sheet-close'] | Bounded optional skip |
| 9 | `/class` | `#at-risk-list` | Needs support; Highlight only | Bounded skip |
| 10 | `/class` | `#cohort-analytics` | Is the class moving?; Highlight only | Bounded skip |
| 11 | `/class` | `#tour-tab-heatmap` | Skills × Bloom's; UI-only click: #tour-tab-heatmap | Bounded skip |
| 12 | `/class` | `#heatmap-panel` | Skills × Bloom's; Highlight only | Bounded skip |
| 13 | `/class` | `#tour-skill-review-trigger` | Skill mapping and review; UI-only click: #tour-skill-review-trigger | Bounded skip |
| 14 | `/class` | `#tour-skill-review-panel` | Skill mapping and review; Highlight only | Bounded skip |
| 15 | `/class` | `#tour-skill-approve` | Skill mapping and review; Highlight only | Bounded optional skip |
| 16 | `/class` | `#tour-at-risk-first-flag` | One learner; UI-only click: #tour-at-risk-first-flag | Bounded optional skip |
| 17 | `/class/student/$uid` | `#tour-standing` | One learner; Highlight only | Bounded skip |
| 18 | `/class/student/$uid` | `#tour-tab-decide` | Decide; UI-only click: #tour-tab-decide | Bounded skip |
| 19 | `/class/student/$uid` | `#tour-decide-center` | Decide; Highlight only | Bounded skip |
| 20 | `/class/student/$uid` | `#tour-run-analysis` | Decide; Highlight only | Bounded skip |
| 21 | `/class/student/$uid` | `#tour-rec-card` | Decide; Highlight only | Bounded optional skip |
| 22 | `/class/student/$uid` | `#tour-decision-buttons` | Decide; Highlight only | Bounded optional skip |
| 23 | `/class/student/$uid` | `#tour-tab-mastery` | Mastery; UI-only click: #tour-tab-mastery | Bounded skip |
| 24 | `/class/student/$uid` | `#tour-record-radar` | Mastery; Highlight only | Bounded skip |
| 25 | `/class/student/$uid` | `#tour-record-intervene` | Mastery; Highlight only | Bounded skip |
| 26 | `/class/student/$uid` | `#tour-tab-activity` | Activity; UI-only click: #tour-tab-activity | Bounded skip |
| 27 | `/class/student/$uid` | `#tour-record-ledger` | Activity; Highlight only | Bounded skip |

### Resolved runner findings

- Parameter routes match concrete IDs by segment; literal `$uid` is rejected and never passed to navigation. Previously visited record paths are remembered for Back. No learner record is invented for an empty class.
- Single-step instances revalidate each visible target; a later hidden/missing target cannot inherit the previous group’s validation. Missing states continue instead of aborting the tour.
- Back uses visited route/search history without replaying the old UI click. The first Back control is disabled. Escape also works during target waiting and overlay animation.
- Forward UI navigation records the next step before the Link changes routes, preventing cancellation from returning the user to the previous page. Repeated Next/Back events are guarded.
- An explicit selector allowlist excludes answers, ratings, uploads, Send, pin/rename/delete, test generation/start/retake, analysis, Approve/Reject and decision recording. Ordinary feature GETs may have server-side operational effects; zero mutating HTTP requests is the tested invariant, not a claim of zero database operations by mounted GET endpoints.
- Existing sidebar-collapse, starter-suggestion and Diagnostic-modal steps were absent at base and remain absent. Thinking is explained, never induced by a tour model call.

### Shared-file proof gate

Fred approved DOCS-HYGIENE’s PracticePanel comment at lines 27–28 and TOUR’s single data-tour attribute as a nonoverlapping exception. Initial TypeScript AST normalization proves exactly one additional data-tour attribute and no other executable change in each of the seven anchor-only feature files against 3a6a0aa. Post-docs rebase, explicit comment survival and fresh browser/lint/typecheck/build checks remain pending until the coordinator releases the approved docs merge. Run with KALA_TOUR_REQUIRE_DOCS=1 after that rebase; the test is deliberately skipped before release.

The preceding paragraph records the initial hold. It is superseded by the completed post-rebase proof and verification below.

## Initial implementation verification — 2026-10-25

All results below are local, on `codex/tour-refresh`, based on `3a6a0aa`. Auth/API fixtures are synthetic; external traffic is blocked. They are not Blackboard, hosted Lambda, provider, screen-reader or lead-designer acceptance.

| Command | Result / log |
| --- | --- |
| `node --test apps/web/src/components/shell/tests/tour-route.test.mjs apps/web/src/components/shell/tests/tour-anchors.test.mjs` | 10 passed; 1 explicitly skipped post-docs coexistence gate. `/tmp/kala-tour-refresh-unit.log` |
| `node apps/web/src/components/shell/tests/tour.browser.mjs` | 616 assertions passed on final source, including all normal/conditional cases below. `/tmp/kala-tour-refresh-browser.log` |
| `node apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs` | 219 retained assertions passed. `/tmp/kala-tour-refresh-retained.log` |
| `node apps/web/src/features/diagnostic/tests/frontend-closeout.browser.mjs` | 110 retained assertions passed. `/tmp/kala-tour-refresh-closeout.log` |
| `pnpm --filter web exec node --test src/features/tutor/components/TutorChat.test.mjs src/features/tutor/schema/tutor.schema.test.ts src/lib/api-error.test.ts src/features/tutor/tests/presentation.test.mjs` | 21 passed. `/tmp/kala-tour-refresh-existing-unit.log` |
| `KALA_STUDY_TEST_DEPS=/private/tmp/kala-lane-f-renderer node --experimental-vm-modules --test apps/web/src/features/flashcards/tests/study-deck.test.mjs` | 4 passed; existing renderer/experimental VM notices. `/tmp/kala-tour-refresh-study.log` |
| `pnpm --filter web lint` | Passed, 0 errors / 18 existing Fast Refresh warnings. `/tmp/kala-tour-refresh-lint.log` |
| `pnpm --filter web typecheck` | Passed; existing route-generator circular dependency notice. `/tmp/kala-tour-refresh-typecheck.log` |
| `pnpm --filter web build` | Passed; existing chunk-size warning. `/tmp/kala-tour-refresh-build.log` |
| `git diff --check` | Passed |

Browser environment: `KALA_BROWSER_TEST_DEPS=/Users/fred/.cache/codex-runtimes/codex-primary-runtime/dependencies/node` and `KALA_BROWSER_EXECUTABLE=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`. No dependency added. The single strict-port Vite listener is PID 39396, from this worktree, command `pnpm --filter web exec vite --port 5173 --strictPort`; keep it running for Fred. No second listener or alternate port was used.

Coverage: student/instructor at 1440px/375px; pointer and keyboard Back; visible target and popover bounds; actual learner record path rather than literal `$uid`; completed Diagnostic, no-material entry and direct missing-target recovery; empty roster/recommendations; empty and existing Tutor drafts; normal-motion Skip/Escape and full reduced-motion walks; per-user/role dismissal; overlay cleanup. Every request is observed globally, not just the API fixture prefix: zero mutating HTTP requests. No file chooser, answer/rating, Send, upload, analysis or teacher decision was induced. Normal navigation GET operational effects remain the caveat above.

Screenshots: `/tmp/kala-tour-refresh`. Visually inspected student desktop Diagnostic, mobile Tutor history, and instructor overview at both sizes. Conditional screenshots may replace the same role/width/index filename and use demo data only.

Failures encountered during implementation: route navigation could cancel advancement before the learner Link completed; Next now records the destination index first. Escape during the overlay animation did not reliably reach Driver; a capture handler now ends the tour while waiting or animating. An initial test sampled null before a newly started tour became active; the fixture now waits for the actual active step and atomically samples visible index/popover. An initial anchor-test repository path was one level off; corrected fixture only. Final passing runs supersede these failures. A focused wildcard assertion also prevents a bare skill parent matching a child route.

## AUDIT REPORT

```text
Task / brief ID: TOUR-REFRESH / initial implementation, pending approved docs rebase
Branch and worktree: codex/tour-refresh; /Users/fred/.codex/worktrees/2e93/kala
Base revision: 3a6a0aab27a8212f77b83e96b26127d830a696ba
Files changed: tour runner/config/student wrapper/route matcher; three tour tests;
  this audit and tour spec; one data-tour attribute each in CourseShell,
  TutorSidebar, DiagnosticPanel, FlashcardDeck, PracticePanel, TutorComposer,
  TwinBody. InstructorTour wrapper unchanged. Exact manifest in Git diff.
REQ / WI IDs touched: TOUR-REQ-001/003/004/005; compatibility with TOUR-REQ-002,
  WI-08 and accepted WI-22 surfaces; no new learning or decision semantics.
Commands run and results: 616 tour + 219 retained + 110 closeout browser assertions;
  10 tour/anchor checks passed with 1 intentional post-docs skip; 21 frontend
  and 4 Study tests passed; lint/typecheck/build/diff check passed.
Spec changes made: tour spec amended before runner implementation at 8c0856a;
  current implementation/evidence and remaining acceptance limits recorded.
Evidence added: frozen original/current step matrix, global mutation spy,
  conditional route/Back/draft/exit tests, screenshots, AST scope proof, logs.
Anything not done, and why: approved DOCS-HYGIENE merge not yet released;
  post-rebase comment/attribute coexistence and fresh checks pending.
  No merge, push, deployment, hosted writes, migration or identity repair.
Risks or questions for the planner: release approved docs merge first, then
  rebase TOUR and run KALA_TOUR_REQUIRE_DOCS=1 plus fresh tour/browser/web gates.
  Live LMS/provider, screen-reader and lead-designer acceptance remain separate.
  Original codex/ui-overhaul e1b0250 and temporary handoff worktree preserved;
  keep current sole 5173 server running for Fred.
Secrets printed: none (confirmed).
```

## Post-DOCS-HYGIENE rebase and full fresh verification — 2026-10-25

Fred approved `627ba9b` subject to this gate. Coordinator released local main `1d980e33a848559e01b229bd23408fd81fedc10f`, including DOCS-HYGIENE and the corrected v7 runtime record. The worktree was clean at `627ba9b59ed096fbe75babbdb76e2ba2b89cc6b7` on `codex/tour-refresh`. `git rebase main` completed without conflicts. Rewritten commits: spec-first `d93c8bd`, runtime/tests `abd7b9cb55d94b480fcd0cdf6cc592a29d3d94d9`. No runtime/test changes were made after the rebase; this follow-up changes only tour documentation/evidence.

### PracticePanel shared-file proof

Compared directly with pre-lane main `3a6a0aa`, PracticePanel has only these two nonoverlapping changes:

- Comment lines 27–28 now cite `docs/features/study/README.md#learning-surface-boundaries`, supplied by DOCS-HYGIENE.
- The existing recap root at line 111 adds `data-tour="test-results"`, supplied by TOUR.

The TypeScript AST test removes comments and data-tour attributes, then compares the complete printed executable tree with `3a6a0aa`: identical. The attribute count increases by exactly one. A separate assertion requires both the exact current Study citation and the new test-results anchor. The same executable-tree/count check passes for all seven anchor-only feature files. `git diff 3a6a0aa -- apps/web/src/features/practice/components/PracticePanel.tsx` independently shows only the comment hunk and one added attribute; against the released main, only the attribute hunk remains. With `KALA_TOUR_REQUIRE_DOCS=1`, all **11 tests pass, zero skipped**.

### Fresh command results

Every result in this table was executed after the rebase; none is reused from the initial run. Logs are local files under `/tmp`; the audit source is retained in Git.

| Command | Fresh result | Log |
| --- | --- | --- |
| `KALA_TOUR_REQUIRE_DOCS=1 node --test apps/web/src/components/shell/tests/tour-route.test.mjs apps/web/src/components/shell/tests/tour-anchors.test.mjs` | **11 passed, 0 failed, 0 skipped** | `/tmp/kala-tour-refresh-rebased-unit.log` |
| `node apps/web/src/components/shell/tests/tour.browser.mjs` | **616 assertions passed**; both roles at 1440px/375px; normal/conditional/Back/Skip/Escape/drafts; zero mutating HTTP requests, zero file choosers | `/tmp/kala-tour-refresh-rebased-browser.log` |
| `node apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs` | **219 assertions passed** | `/tmp/kala-tour-refresh-rebased-retained.log` |
| `node apps/web/src/features/diagnostic/tests/frontend-closeout.browser.mjs` | **110 assertions passed** on unchanged standalone rerun; initial failure retained below | `/tmp/kala-tour-refresh-rebased-closeout.log` |
| `pnpm --filter web exec node --test src/features/tutor/components/TutorChat.test.mjs src/features/tutor/schema/tutor.schema.test.ts src/lib/api-error.test.ts src/features/tutor/tests/presentation.test.mjs` | **21 passed** | `/tmp/kala-tour-refresh-rebased-frontend-unit.log` |
| `KALA_STUDY_TEST_DEPS=/private/tmp/kala-lane-f-renderer node --experimental-vm-modules --test apps/web/src/features/flashcards/tests/study-deck.test.mjs` | **4 passed**; existing experimental VM/renderer notices | `/tmp/kala-tour-refresh-rebased-study.log` |
| `pnpm --filter web lint` | Passed; **0 errors / 18 existing Fast Refresh warnings** | `/tmp/kala-tour-refresh-rebased-lint.log` |
| `pnpm --filter web typecheck` | Passed; existing route-generator circular dependency notice | `/tmp/kala-tour-refresh-rebased-typecheck.log` |
| `pnpm --filter web build` | Passed; existing chunk-size warning | `/tmp/kala-tour-refresh-rebased-build.log` |
| `python3 scripts/docs_check.py` | Passed; **zero record-link / machine-path violations** | `/tmp/kala-tour-refresh-rebased-docs.log` |
| `python3 -m unittest discover -s scripts -p 'test_docs_check.py'` | **18 passed** | `/tmp/kala-tour-refresh-rebased-docs-unit.log` |
| `uv run --project services/api python scripts/config_inventory.py --check` | Passed; static names-only inventory, no hosted settings read | `/tmp/kala-tour-refresh-rebased-config.log` |
| `git diff --check` | Passed | Command exit 0 |

Browser commands used `KALA_BROWSER_TEST_DEPS=/Users/fred/.cache/codex-runtimes/codex-primary-runtime/dependencies/node` and `KALA_BROWSER_EXECUTABLE=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`. Retained screenshots used `KALA_UI_SCREENSHOTS=/tmp/kala-tour-refresh-rebased-retained`; the standalone closeout used `/tmp/kala-tour-refresh-rebased-closeout`. Tour captures are `/tmp/kala-tour-refresh`; fresh mobile history capture was visually checked. APIs/auth are synthetic and external traffic blocked; no live accounts, tokens, uploads, learning submissions or teacher decisions were used.

First-run failure: while browser suites ran concurrently, closeout timed out after 20 seconds waiting for Twin accordion pagination page 2 after keyboard activation (`frontend-closeout.browser.mjs:61`, caller line 99). Preserved `/tmp/kala-tour-refresh-rebased-closeout-first-failure.log`. After the other browser processes completed, the exact unchanged suite ran alone and passed all 110 assertions. No application, fixture, timeout or assertion was changed. Root cause is not established; report this as a nonreproducing keyboard-pagination timing failure, not a proven fixed product defect.

Docs checker initially caught one unmarked local screenshot path in the tour feature spec. Added the exact “local only, not retained” marker on that line, then reran successfully. No checker rule or unrelated document was changed.

### Scope, runtime and handoff

- `git diff main --name-only -- services packages/db infra` is empty. No backend, database, infrastructure, auth or learning semantics changed in this lane. Seven feature changes remain attribute-only by executable AST proof.
- Original `codex/ui-overhaul` remains `e1b02508f55bd03412ceb74c75128cb25a5cf0f8`. Temporary handoff worktree remains preserved.
- The same sole Vite listener, PID **39396**, remains on **5173**, from `/Users/fred/.codex/worktrees/2e93/kala`; command `pnpm --filter web exec vite --port 5173 --strictPort`. No restart, alternate port or second listener.
- Per the coordinator's corrected record, Fred confirms live v7 runtime refresh at 00:04 UTC after paid fallback at 00:01 UTC, including I/G/U backend changes. This lane did not inspect hosted state. Frontend release remains dependent on the coordinator's authorized push and Vercel Ready; successful real Hint/Explain/dock clicks remain FG-5 pending.
- WI-24 historical identity repair, WI-25 full-history pagination and WI-26 instructor authorization remain open with ITO. No repair, scope expansion or live acceptance claim.
- Coordinator reviews and merges; this lane did not merge, push, deploy, write hosted data or print credentials.

## AUDIT REPORT — post-rebase gate

```text
Task / brief ID: TOUR-REFRESH / Fred-approved post-DOCS-HYGIENE rebase gate
Branch and worktree: codex/tour-refresh;
  /Users/fred/.codex/worktrees/2e93/kala
Base revision: 1d980e33a848559e01b229bd23408fd81fedc10f
Tested runtime revision: abd7b9cb55d94b480fcd0cdf6cc592a29d3d94d9;
  final evidence commit follows without runtime/test changes.
Files changed: same approved 17-path tour scope; follow-up only tour feature
  spec and this audit. PracticePanel contains current Study citation plus
  exactly one added data-tour attribute; executable AST otherwise identical
  to pre-lane main 3a6a0aa. No backend/db/infra changes.
REQ / WI IDs touched: TOUR-REQ-001/003/004/005; TOUR-REQ-002 compatibility;
  WI-08/WI-22 compatibility. WI-24/25/26 remain open owner ITO.
Commands run and results: all fresh after rebase: 616 tour + 219 retained +
  110 closeout browser assertions; 11 route/anchor tests, zero skipped;
  21 frontend + 4 Study tests; lint/typecheck/build passed; docs_check zero
  violations + 18 tests; config_inventory --check and diff check passed.
Spec changes made: verification updated for released docs merge, 11/0-skip
  coexistence gate and fresh checks; local artifact marker added.
Evidence added: full command/log table, shared-file AST/diff proof, failure
  and unchanged passing rerun, scope/server/runtime boundary above.
Anything not done, and why: coordinator review/merge/push and frontend release
  remain coordinator actions; FG-5 live feature acceptance remains pending.
  No hosted writes, repair, deployment, push or migrations by this lane.
Risks or questions for the planner: initial concurrent closeout keyboard-page
  timeout did not reproduce standalone; cause not established. Existing web
  warnings remain. WI-24/25/26 and live acceptance are not closed by this run.
  Sole 5173 Vite PID39396 remains running; preserve it for Fred.
Secrets printed: none (confirmed).
```
