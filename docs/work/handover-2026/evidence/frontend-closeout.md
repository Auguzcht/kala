# APPROVAL-06 Lane U close-out

Base: e1b0250. Branch: codex/ui-closeout, existing /Users/fred/.codex/worktrees/2e93/kala. codex/ui-overhaul is preserved at the approved e1b0250. Authority: Fred's APPROVAL-06 rev 2 attachment (section 5), relayed by coordinator. No hosted writes, deployment, migration, push, key rotation or identity repair. (local only, not retained)

## Early scope and spec release request

Coordinator owns docs/features/diagnostic/README.md exclusively for this approval. U will not edit it. The following is exact proposed spec text for the coordinator to commit separately from G's DIAG-REQ-009–011. Implementation of these parts is held until rebased onto the named spec commit. A draft H05/H07 implementation was made before the ownership clarification; it has been removed from working source and preserved only as /tmp/kala-ui-closeout-held-recovery.patch pending release. No tests or implementation acceptance are claimed for that draft. (local only, not retained)

### Proposed DIAG-REQ-012: Recover Diagnostic and skill-picker loading failures

- Rule: Diagnostic's load-error Retry refetches the existing question query without submitting answers or reloading the document. Skills and retained Lessons/Flashcards pickers distinguish a failed skills fetch from an empty successful response, show a connection error with a working Retry, and reserve the empty state for a genuinely empty course. Empty copy addresses learners without ingest/proposal implementation terminology. The course-wide Flashcards deck remains available and exposes its existing error/retry states.
- Acceptance: At 375px and 1440px, a rejected request presents an error rather than No skills mapped yet; pointer and keyboard Retry can recover after the API becomes available. Empty data remains a separate state. Submission/results, course-wide review and grading remain unchanged.
- Status: planned
- Verification: Lane U's uniquely named frontend-closeout browser suite and existing suites; evidence/frontend-closeout.md.

### Proposed DIAG-REQ-013: Present optional actionable and waiting counts compatibly

- Rule: The frontend status schema accepts optional dueSkillCount and waitingForMaterialCount. When dueSkillCount is present, the Diagnostic badge and workspace action follow that actionable count (including zero), taking precedence over the legacy due boolean. When absent, preserve the legacy due signal and use a count-free action label. Show a quiet singular/plural “N topics are waiting for course material” line only for a positive waitingForMaterialCount; it has no action button and is absent when the field is omitted. Never synthesize evidence or make generation calls to clear a badge.
- Acceptance: Omitted legacy fields, actionable zero with legacy due=true, positive actionable count and material-only waiting all render correctly; zero/absent waiting shows no line. Workspace and rail agree on whether a Diagnostic action is due.
- Status: planned
- Verification: Lane U's synthetic legacy/new response fixtures, schema checks and existing suites; evidence/frontend-closeout.md.

### Proposed cross-surface presentation amendment (no G requirement collision)

- Rule: Existing roster, skill-proposal and Twin skill pagination uses Tab-reachable links or buttons, explicit endpoint disabled semantics and the existing 40px sizing. Twin's Practice this opens the shown skill's canonical Test browse pane, never starts automatically. Root error/not-found returns authenticated staff to /class and students to /course; without a session it gives the Blackboard session-ended instruction with no dead relaunch button. The public root says “Open Kala from your course in Blackboard.” Session-expired says “Your session ended. Go back to your Blackboard course and open Kala again.” No password sign-in is introduced.
- Rule: /course/practice without skillId redirects to /course/skills with replace; existing skillId/setId bridges remain canonical Test browse links. Keep /course/lessons and the course-wide /course/flashcards deck. Remove only stale SessionBar source commentary, not routes. Evidence labels state Last 20 events for Twin and Last 25 events for learner-record ledger; statistics based on bounded samples are labelled Based on recent activity and do not imply lifetime evidence totals. No full-history paging/API change.
- Acceptance: Keyboard pager boundaries and page changes work without a hash jump; contextual Practice this retains skillId and tab=test with no start; each role/no-session error destination is correct; direct root/expiry have the approved copy; legacy links preserve set context and no-skill entry redirects. Count windows remain explicit with empty/partial/full data. Reduced motion and existing layout remain.

The coordinator can incorporate the cross-surface amendment in the appropriate exclusively owned integration specification. U will not create a new feature or edit P-owned specs. Focused existing Twin/Instructor presentation specs are the potential U amendment paths if separately requested; Tutor/AI/DESIGN stay coordinator-owned.

## Server handoff

PID 81696 was Vite from this worktree, command:

```sh
pnpm --filter web exec vite --port 5173 --strictPort
```

On the coordinator's request U sent SIGTERM to PID 81696 and confirmed no listener on 5173 before yielding the port. U will not start another server or run browser suites until the coordinator releases the port. Source work continues. Resume with the exact strict-port command above, from this worktree, after release. Never shift ports silently.

## Verification commands for coordinator

Dependencies already used by WI-22: pnpm workspace installation; Node; bundled Playwright under /Users/fred/.cache/codex-runtimes/codex-primary-runtime/dependencies/node; Chrome at /Applications/Google Chrome.app/Contents/MacOS/Google Chrome. Study's existing external renderer fixture is /private/tmp/kala-lane-f-renderer. No new package dependency. (local only, not retained)

```sh
pnpm --filter web exec node --test src/features/tutor/components/TutorChat.test.mjs src/features/tutor/schema/tutor.schema.test.ts src/lib/api-error.test.ts src/features/tutor/tests/presentation.test.mjs
KALA_STUDY_TEST_DEPS=/private/tmp/kala-lane-f-renderer node --experimental-vm-modules --test apps/web/src/features/flashcards/tests/study-deck.test.mjs # local only, not retained
pnpm --filter web lint
pnpm --filter web typecheck
pnpm --filter web build
```

For each browser command below, set KALA_BROWSER_TEST_DEPS to the bundled Node package root above and KALA_BROWSER_EXECUTABLE to the Chrome path above; use the one already-running strict-port 5173 Vite server from the tested checkout. APIs/auth are synthetic and external traffic is blocked.

```sh
node apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
node apps/web/src/features/instructor/tests/review-feedback.browser.mjs
node apps/web/src/features/twin/tests/presentation.browser.mjs
```

## Current boundaries

H05/H07/H02-copy spec-dependent implementation is held as described above. Other pre-approved fixes are being prepared; final verification must occur after rebasing onto the integrated main/spec SHA supplied by the coordinator. FG-1/2/3/4/5 are not performed by U; none blocks unrelated source work. No external chat message has been sent by U.

## Preliminary source checks before integration/spec release

The ungated source draft covers H06 keyboard links/disabled endpoints, H08 canonical skill context, H09 role-aware recovery, H10/H11 entry/expiry copy, H12 window labels, retained legacy route bridges and the stale Tutor comment. The dedicated test draft is apps/web/src/features/diagnostic/tests/frontend-closeout.browser.mjs. H05/H07 source is held separately as above; H02 optional fields have not been implemented pending the coordinated contract.

- `pnpm --filter web lint`: passed, 0 errors / 18 existing warnings; /tmp/kala-ui-closeout-lint.log. (local only, not retained)
- `pnpm --filter web typecheck`: passed with the existing route-generator circular warning; /tmp/kala-ui-closeout-typecheck.log. (local only, not retained)
- Frontend Node command above: 21 passed; /tmp/kala-ui-closeout-unit.log. (local only, not retained)
- Study renderer command above: 4 passed; /tmp/kala-ui-closeout-study.log. (local only, not retained)
- `node --check apps/web/src/features/diagnostic/tests/frontend-closeout.browser.mjs`: passed syntax check only, not browser acceptance.
- Final source whitespace check passed after removing a trailing blank line. No build/browser claim is made before the held pieces are restored and the required rebase occurs. A subsequent small pager clamp/copy correction still requires the final complete checks.

AUDIT REPORT
Task / brief ID: APPROVAL-06 Lane U / early scope, spec proposal and server handoff
Branch and worktree: codex/ui-closeout; .
Base revision: e1b0250; codex/ui-overhaul preserved unchanged
Files changed: this evidence file committed; frontend source/test drafts held pending the integration/spec SHA and browser-port release
REQ / WI IDs touched: proposed DIAG-REQ-012/013; existing Twin/Instructor presentation and WI-22; no coordinator-owned spec edited
Commands run and results (tests, lint, typecheck, build): preliminary lint/typecheck, 21 frontend and 4 Study tests passed; new browser script syntax passed; build/browser final runs pending
Spec changes made: none in feature specs; exact proposed coordinator text above
Evidence added: proposal, owned scope, command/dependency list, PID/port yield and preliminary checks
Anything not done, and why: H05/H07/H02 held until named spec commit; final verification held until integrated rebase and 5173 release; no hosted writes, deployment, push, migration or identity repair
Risks or questions for the planner: please commit the exact proposed U contract separately from G's 009–011 and release its SHA; preserve optional legacy fields and coordinate any new question waiting fields before UI implementation
Secrets printed: none (confirmed)

## Final implementation and verification after spec release

The coordinator released main `3128e2c`, with G's DIAG-REQ-009–011 in separate commit `1af50f1` and U's DIAG-REQ-012/013 plus the cross-surface amendment in `3128e2c`. U rebased onto that exact revision before restoring the held H05/H07 patch or implementing H02 compatibility. The earlier holds above are historical and are now resolved. U never edited the Diagnostic, Tutor, AI or DESIGN specs. G's backend availability implementation and I's identity convergence remain separate integration lanes; this branch supplies the compatible frontend.

Implemented:

- H05: Diagnostic Retry refetches the existing query; pointer and keyboard recovery tested, without submission.
- H06: roster, proposal and Twin skill pagers have real hrefs, keyboard activation, explicit aria-disabled/tab-order endpoints, unchanged 40px controls and prevent hash navigation. Navigation uses the clamped page after data shrink.
- H07: Skills/retained Lessons/Flashcards pickers distinguish a failed fetch with Retry from an empty successful response. Learner-facing empty copy replaces ingest/proposal jargon. Existing course-wide deck error/Retry remains and its no-material copy is learner-facing.
- H08: Focus area's Practice this retains the shown skill ID in the canonical Test browse route; no start parameter.
- H09: not-found/root-error links use /course for students and /class for staff; no-session fallback uses the approved Blackboard session-ended instruction without a dead link. AppProviders is above the router, so the root error fallback retains session access without an auth architecture change.
- H10/H11: root scaffold replaced by the approved Blackboard entry instruction; expiry gives the exact approved instruction and no Re-launch button or standalone login copy.
- H12 copy: Twin ledger labels Last 20 events; learner record labels Last 25 events and earlier rows omitted; learner standing identifies up-to-200 recent evidence and Based on recent activity; cohort accuracy labels recent graded events and explains its 2,000-course-event window in the existing tooltip. No arithmetic/query/history contract changed.
- Legacy: unscoped Practice replaces itself with Skills; existing skillId/setId links still replace into Test browse, with no automatic sitting. Lessons and the course-wide Flashcards deck remain. Stale Tutor SessionBar commentary corrected.
- H02 copy: Zod accepts optional actionable/material counts on status and optional material count on questions. Shared isDiagnosticDue applies supplied count precedence in both rail/workspace, including explicit zero over due=true. Legacy responses keep the boolean and count-free copy. Positive material count shows quiet singular/plural copy without an action; omitted/zero is hidden. Available question rows win, empty preparation/failure keeps its status, material-only waiting is distinct, and legacy empty remains caught up. Waiting text does not claim a worker is actively generating for exhausted pools.

| Command / evidence | Result |
| --- | --- |
| `node apps/web/src/features/diagnostic/tests/frontend-closeout.browser.mjs`, with the bundled browser env variables documented above | **110 assertions passed**, /tmp/kala-ui-closeout-browser.log | (local only, not retained)
| Existing Tutor/Diagnostic browser suite, KALA_UI_SCREENSHOTS=/tmp/kala-ui-closeout-retained | **219 assertions passed**, /tmp/kala-ui-closeout-retained.log | (local only, not retained)
| Existing instructor feedback browser suite, KALA_UI_SCREENSHOTS=/tmp/kala-ui-closeout-instructor | **63 assertions passed**, /tmp/kala-ui-closeout-instructor.log | (local only, not retained)
| Existing Twin presentation browser suite, KALA_UI_SCREENSHOTS=/tmp/kala-ui-closeout-twin | **148 assertions passed**, /tmp/kala-ui-closeout-twin.log | (local only, not retained)
| Frontend Node command above | **21 passed**, /tmp/kala-ui-closeout-unit.log | (local only, not retained)
| Study renderer command above, rerun after rebase | **4 passed**, /tmp/kala-ui-closeout-study.log; existing experimental VM/renderer notices | (local only, not retained)
| `pnpm --filter web lint` | Passed, 0 errors / 18 existing Fast Refresh warnings; /tmp/kala-ui-closeout-lint.log | (local only, not retained)
| `pnpm --filter web typecheck` | Passed, existing route-generator circular warning; /tmp/kala-ui-closeout-typecheck.log | (local only, not retained)
| `pnpm --filter web build` | Passed, existing chunk-size warning; /tmp/kala-ui-closeout-build.log | (local only, not retained)
| `git diff --check` and new browser script syntax check | Passed |

New synthetic captures are /tmp/kala-frontend-closeout/{diagnostic-error,skills-error,lessons-error,flashcards-error,not-found-student,not-found-instructor,not-found-no-session,root-error-student,root-error-instructor,public-root,session-expired}-{375,1440}.png. The ten requested Diagnostic error, Skills error, instructor not-found, root and expiry captures at both sizes were visually inspected. All contexts mock session/API and block non-localhost traffic, including mutation attempts. No live ask, submission, upload, teacher decision or hosted data access occurred. (local only, not retained)

The new test's initial synthetic session response omitted parentheses around an arrow-function object expression; this caused a fixture-only syntax error and was corrected. Another initial fixture selector used the module name where Twin groups by Bloom level; it was corrected to the real group. Final passing runs supersede these harness failures. No application change was made to satisfy either incorrect fixture.

Port 5173 was restarted only after the coordinator's release. Current Vite PID is **34528**, started from this worktree with `pnpm --filter web exec vite --port 5173 --strictPort` (exec session 77582), output /tmp/kala-ui-closeout-vite.log. Keep it running for Fred unless the coordinator needs it for final combined checks. No second listener or alternate port was used. (local only, not retained)

No feature-spec status is changed by U: coordinator can mark DIAG-REQ-012/013 implemented after reviewing this evidence. Full-history paging stays deferred. G's optional-field backend and I's code convergence still need final combined integration; existing split dev-hosted Alfred/Hanna data is explicitly deferred by APPROVAL-06 and was not repaired. FG-1 provider config, FG-3 migration, FG-4 deploy and FG-5 real click-through remain Fred/coordinator gates; these synthetic UI checks do not close them.

AUDIT REPORT
Task / brief ID: APPROVAL-06 rev 2 Lane U / H05–H11, H12 copy, legacy routes and H02 compatible copy
Branch and worktree: codex/ui-closeout; /Users/fred/.codex/worktrees/2e93/kala; approved codex/ui-overhaul remains e1b0250 (local only, not retained)
Base revision: integrated/spec release 3128e2c, rebased before held H05/H07/H02 implementation
Files changed: frontend shell/shared picker; Diagnostic schema/public surface/helper/panel and dedicated tests; selected student routes; instructor pager/count-copy components; TwinBody; FlashcardDeck copy; this dedicated evidence file. Exact manifest is the final commit diff.
REQ / WI IDs touched: DIAG-REQ-012/013 and APPROVAL-06 cross-surface amendment; DIAG-REQ-009–011 compatibility; existing TWIN-REQ-002/003 and INSTR presentation compatibility; WI-22
Commands run and results (tests, lint, typecheck, build): 110 close-out + 219 retained + 148 Twin + 63 instructor browser assertions; 21 frontend + 4 Study tests; lint/typecheck/build/diff check passed with existing warnings
Spec changes made: none by U; exact proposed text was committed by the coordinator at 3128e2c before the held implementation resumed
Evidence added: final implementation mapping, synthetic browser suite/captures, exact logs and port handoff
Anything not done, and why: no merge/push/deploy, migration, hosted writes or identity repair; backend I/G and real acceptance remain coordinator/Fred work
Risks or questions for the planner: integrate I then G then this lane with full combined checks; retain optional legacy compatibility; mark spec statuses after review; H12 remains bounded history, not full-history paging
Secrets printed: none (confirmed)

## Release-state correction — 2026-10-25

Fred confirms API alias `live` v7 was deployed at **00:04 UTC (08:04 Asia/Manila)**, after the paid-fallback secret change at **00:01 UTC (08:01 Asia/Manila)**. The backend runtime refresh is complete. This is Fred's deployment confirmation, not a new AWS image inspection by the documentation lane. It supersedes earlier pending-runtime statements; the original observation timeline remains above.

The I, G and U close-out backend code is included in v7. Their frontend changes become live only after Fred's authorized Git publication and a Ready Vercel deployment. Saving the fallback and refreshing Lambda do not establish successful model responses: real Study Hint, Explain and dock success remain **FG-5 pending**, along with the other live role/feature acceptance checks. No additional backend deploy is required for the docs/tour changes.

WI-24 (historical identity repair), WI-25 (full-history paging) and WI-26 (instructor course authorization/recommendation visibility) remain open, owner **ITO**, unless Fred changes that assignment. No repair or security completion is claimed.
