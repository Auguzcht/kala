# APPROVAL-06 Lane U close-out

Base: e1b0250. Branch: codex/ui-closeout, existing /Users/fred/.codex/worktrees/2e93/kala. codex/ui-overhaul is preserved at the approved e1b0250. Authority: Fred's APPROVAL-06 rev 2 attachment (section 5), relayed by coordinator. No hosted writes, deployment, migration, push, key rotation or identity repair.

## Early scope and spec release request

Coordinator owns docs/features/diagnostic/README.md exclusively for this approval. U will not edit it. The following is exact proposed spec text for the coordinator to commit separately from G's DIAG-REQ-009–011. Implementation of these parts is held until rebased onto the named spec commit. A draft H05/H07 implementation was made before the ownership clarification; it has been removed from working source and preserved only as /tmp/kala-ui-closeout-held-recovery.patch pending release. No tests or implementation acceptance are claimed for that draft.

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

Dependencies already used by WI-22: pnpm workspace installation; Node; bundled Playwright under /Users/fred/.cache/codex-runtimes/codex-primary-runtime/dependencies/node; Chrome at /Applications/Google Chrome.app/Contents/MacOS/Google Chrome. Study's existing external renderer fixture is /private/tmp/kala-lane-f-renderer. No new package dependency.

```sh
pnpm --filter web exec node --test src/features/tutor/components/TutorChat.test.mjs src/features/tutor/schema/tutor.schema.test.ts src/lib/api-error.test.ts src/features/tutor/tests/presentation.test.mjs
KALA_STUDY_TEST_DEPS=/private/tmp/kala-lane-f-renderer node --experimental-vm-modules --test apps/web/src/features/flashcards/tests/study-deck.test.mjs
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

- `pnpm --filter web lint`: passed, 0 errors / 18 existing warnings; /tmp/kala-ui-closeout-lint.log.
- `pnpm --filter web typecheck`: passed with the existing route-generator circular warning; /tmp/kala-ui-closeout-typecheck.log.
- Frontend Node command above: 21 passed; /tmp/kala-ui-closeout-unit.log.
- Study renderer command above: 4 passed; /tmp/kala-ui-closeout-study.log.
- `node --check apps/web/src/features/diagnostic/tests/frontend-closeout.browser.mjs`: passed syntax check only, not browser acceptance.
- Final source whitespace check passed after removing a trailing blank line. No build/browser claim is made before the held pieces are restored and the required rebase occurs. A subsequent small pager clamp/copy correction still requires the final complete checks.

AUDIT REPORT
Task / brief ID: APPROVAL-06 Lane U / early scope, spec proposal and server handoff
Branch and worktree: codex/ui-closeout; /Users/fred/.codex/worktrees/2e93/kala
Base revision: e1b0250; codex/ui-overhaul preserved unchanged
Files changed: this evidence file committed; frontend source/test drafts held pending the integration/spec SHA and browser-port release
REQ / WI IDs touched: proposed DIAG-REQ-012/013; existing Twin/Instructor presentation and WI-22; no coordinator-owned spec edited
Commands run and results (tests, lint, typecheck, build): preliminary lint/typecheck, 21 frontend and 4 Study tests passed; new browser script syntax passed; build/browser final runs pending
Spec changes made: none in feature specs; exact proposed coordinator text above
Evidence added: proposal, owned scope, command/dependency list, PID/port yield and preliminary checks
Anything not done, and why: H05/H07/H02 held until named spec commit; final verification held until integrated rebase and 5173 release; no hosted writes, deployment, push, migration or identity repair
Risks or questions for the planner: please commit the exact proposed U contract separately from G's 009–011 and release its SHA; preserve optional legacy fields and coordinate any new question waiting fields before UI implementation
Secrets printed: none (confirmed)
