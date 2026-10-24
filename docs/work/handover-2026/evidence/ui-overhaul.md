# WI-22: Diagnostic and Tutor UI evidence

Date: 2026-10-25 (Asia/Manila). Lane U, branch `codex/ui-overhaul`, worktree `/Users/fred/.codex/worktrees/2e93/kala`.

## Authority and revisions

Initial main base: `4f3ec29d3f827a1db92e90c4f395947d37744479`. Verified that approval base `cab26de` is its ancestor; the intervening change touches deployment-evidence documents only. The Diagnostic spec was committed before implementation, then safely rebased onto coordinator spec commit `c961b83`, which contains APPROVAL-05 authority, DESIGN exceptions `6676b9e`, B's TUTOR-REQ-002/003 and U's TUTOR-REQ-004–011. Diagnostic spec commit after rebase: `f738462`.

Verification below applies to `c961b83` plus the Lane U Diagnostic spec and working-tree implementation in the paths listed below. The containing implementation commit is reported in the final AUDIT REPORT; this file does not embed its own commit SHA.

Requirements: DIAG-REQ-001–005, TUTOR-REQ-004–011; regression protection for TUTOR-REQ-001 and STUDY-REQ-003/005. Work item: [WI-22](../work-items/WI-22-diagnostic-tutor-ui.md). [WI-23](../work-items/WI-23-tutor-grounding-citations.md) remains planned.

## Implemented and inspected

- Diagnostic removes the redundant introduction, excluded-material note, back chevron and progress bar. One scroll region fills the available height above a normal-flow submit footer, which displays the answered count. Existing selection/payload, due hooks, preparation/empty/error states, tour anchors and mastery-delta result remain.
- Study flip faces use `inert`; mouse, Enter and Space flips move focus to the visible face. Rating, schedule and ComposeDock behavior are unchanged.
- Tutor history is always open at lg and larger, with a mobile header-triggered Sheet. Pinned and Recents use Collapsible; row management supports inline rename, pin/unpin and confirmed deletion. Capability comes only from presence of `pinnedAt` in the list row; explicit null is supported/unpinned, omission hides PATCH actions even when detail responses omit the field.
- Empty chat has a centered PromptInput, deterministic local time/course greeting, course-skill template starters and Kala's own subtle logo idle. Typing stops idle; sending moves the dock down. Reduced motion is static.
- Tutor reuses PromptInput drag/drop with opt-in file ownership, enclosing drop target and drag-state props. Default form-scoped staging/submission is preserved. Files upload through the existing endpoint, use one shared lazy-creation promise, preserve an unsent draft across creation, validate backend-supported extensions/5MB limit and show safe server errors. No image support was added.
- Waiting uses Shimmer with Thinking, then Still working on it after about eight seconds, anchored to the original ask across lazy conversation creation. Existing timeout and returned-answer recovery remain.
- Buttons, chips, inputs and menus in the new Tutor UI use boxy token radii. The two narrow DESIGN exceptions apply only to the entry container and empty-state logo.

## Diagnostic route inventory

Every current Diagnostic UI destination is `/course/diagnostic`:

| Source | Entry | Disposition |
| --- | --- | --- |
| `apps/web/src/routes/course/diagnostic.tsx` | Registered page route | Retained; simplified page component |
| `apps/web/src/routes/course/index.tsx` | Quick-link card and due-notice action | Retained; correct destination |
| `apps/web/src/components/shell/CourseShell.tsx` | Sidebar entry, section label and session-route classification | Retained; correct destination and due badge |
| `apps/web/src/features/plan/components/InstructorPlan.tsx` | Diagnostic instructor-plan action | Retained; correct destination |
| `apps/web/src/components/shell/student-tour.ts` | Card, choices and submit tour steps | Retained; destination and anchors preserved |
| `apps/web/src/routes/launch.tsx` | Student launch redirect | `/course`, not an obsolete Diagnostic entry |
| `apps/web/src/routeTree.gen.ts` | Generated registration | Single full route `/course/diagnostic`; unchanged |

Search covered application routes, navigation, auth, source, scripts and service references. No stale Diagnostic UI route, alias or redirect was found. No speculative alias or redirect was introduced. API paths `/courses/{course_id}/diagnostic`, `/status` and `/submit` are API contracts, not obsolete UI entries, and are unchanged.

## Verification

All commands below completed successfully on the final implementation working tree unless marked historical setup correction.

| Command / check | Result |
| --- | --- |
| `pnpm install --frozen-lockfile` | Passed; no manifest or lockfile changes |
| `pnpm --filter web exec node --test src/features/tutor/components/TutorChat.test.mjs src/features/tutor/schema/tutor.schema.test.ts src/lib/api-error.test.ts src/features/tutor/tests/presentation.test.mjs` | 21 passed: 14 existing recovery/error/schema tests plus 7 presentation tests |
| `KALA_STUDY_TEST_DEPS=/private/tmp/kala-lane-f-renderer node --experimental-vm-modules --test apps/web/src/features/flashcards/tests/study-deck.test.mjs` | 4 passed; existing external renderer fixture and deprecation warning remain |
| `KALA_BROWSER_TEST_DEPS=/Users/fred/.cache/codex-runtimes/codex-primary-runtime/dependencies/node KALA_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' node apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs` | 71 browser assertions passed; all ten requested screenshots captured |
| `pnpm --filter web lint` | Passed, 0 errors / 18 pre-existing Fast Refresh warnings |
| `pnpm --filter web typecheck` | Passed; existing TanStack circular-dependency warning |
| `pnpm --filter web build` | Passed; existing circular-dependency and chunk-size warnings; final build 6.56s |
| `git diff --check` | Passed |
| Scope comparison against `c961b83` | ComposeDock, generated OpenAPI/types, manifests/lock, backend, DB and infrastructure unchanged |

The browser test uses a separate headless Chrome context with synthetic auth/API module interception and blocks non-local network destinations. It never uses Fred's session, tokens or hosted API. Assertions exercise real components/layouts: long last-question reachability, answered count/payload, responsive sidebar, unchanged non-Tutor header/56px offset, rename despite detail omission, pin/unpin, collapsed groups, delete cancel/confirm, legacy capability gating, Thinking/elapsed state, attachments, upload errors, draft preservation, inert/focus keyboard behavior and default/opt-in PromptInput behavior. The mascot is checked under reduced and ordinary motion settings. These are synthetic UI checks, not live provider, database or LMS feature acceptance.

Historical setup corrections, not accepted feature failures: the bundled Playwright browser binary was unavailable, so the script used installed Chrome explicitly; the initial result locator assumed a heading where CardTitle is a div; the separate primitive fixture needed Vite's React Refresh preamble and the optimized module's default export. A timer check installed its clock after the timer began and was unstable; installing it before page load made the final elapsed-state check deterministic. Earlier partial runs do not replace the final passing suite.

## Screenshots and visual review

Synthetic captures are external local artifacts under `/tmp/kala-lane-u-visuals/`, deliberately separate from authenticated student data:

| State | Desktop | Mobile |
| --- | --- | --- |
| Diagnostic, scrolled to last question | `diagnostic-1440.png` | `diagnostic-375.png` |
| Tutor empty chat | `tutor-empty-1440.png` | `tutor-empty-375.png` |
| Tutor conversation | `tutor-conversation-1440.png` | `tutor-conversation-375.png` |
| Tutor drag-over | `tutor-drag-1440.png` | `tutor-drag-375.png` |
| Tutor sidebar menu | `tutor-menu-1440.png` | `tutor-menu-375.png` |

Inspected the captures for scroll reachability, layout, text wrapping, boxy controls, mobile Sheet/menu and the drop overlay. Mobile Tutor header spacing is opt-in to the Tutor route; other route chrome is unchanged. No screenshot of identifying live learning data or token was saved.

## Local server and authorized live opening

Initial 5173 inspection found no listener; no Audit server was stopped and its worktree remained untouched. Vite originally ran as PID 70116 from this lane's `apps/web` directory with `pnpm dev --port 5173 --strictPort`. Dependencies and source changes used only this worktree.

The environment file was initially absent. Fred then explicitly instructed this chat to point to the main checkout's file, superseding the earlier instruction that Fred alone copies it. The ignored `apps/web/.env.local` is now a symlink to the main checkout's existing file. The agent checked existence and created the link without reading or copying its contents. Only this lane's Vite PID 70116 was stopped; the replacement strict-port server is PID 81696 at `http://localhost:5173` and remains running.

At Fred's explicit request, the supplied session was used to open the visible local course workspace. Verified the workspace is visible and the launch token fragment was removed from the URL. No course questions, learning records, credentials or provider bodies were copied into this evidence. Opening the workspace does not establish live Diagnostic/Tutor acceptance. No agent ask, upload, rename, pin, deletion, submission or other hosted-data write was performed.

## Ownership and remaining acceptance

CourseShell access was granted by the coordinator in WI-22 only for Tutor state, offsets and mobile-header integration. Browser assertions prove the non-Tutor route retains its header behavior and 56px rail offset. Shared PromptInput changes are optional props with default behavior tested. U did not edit the coordinator-owned Tutor/AI specs, B's generated contract files, the Study spec or ComposeDock.

Remaining: Fred's authenticated click-through of Diagnostic/Tutor; B's deployed PATCH/list contract for live pin/rename acceptance; lead designer review of both approved DESIGN exceptions. The new frontend checks still use the existing custom/external setup; standard runner adoption remains WI-20. This lane does not resolve or verify Lane X's live provider failure.

No merge, push, deployment, hosted migration, key rotation or infrastructure change was performed. No secret value was printed in command output, repository files or reports. The supplied session was used only for Fred's authorized local sign-in.


## Fred's direct visual correction — 2026-10-25 (before follow-up implementation)

Fred rejected the squared Tutor user bubbles and submit button, requested the existing shared Study/Test/Flashcard dock appearance, removal of the added “Course-grounded help · De-identified before model calls” line, and a wider adjustable history panel with a matching shell offset. His reference has a white borderless New chat action that gains a muted fill on hover, and a quiet Recents heading. Direct pin visibility remains constrained by the already approved live API capability gate.

This feedback supersedes the earlier interpretation that the existing Tutor user bubbles and circular send control should become boxy. It is recorded before code changes in the owned Diagnostic component-boundary spec. Coordinator-owned Tutor and DESIGN files remain untouched; their integration amendments are: TUTOR-REQ-004 adds a pointer/keyboard-resizable desktop history panel (320px default; 280–440px bounds, additionally constrained to leave the main content usable), matching shell offset, and existing mobile Sheet; TUTOR-REQ-009 and the shape exception preserve the existing shared circular send control and rounded user/follow-up appearance; remove the added Tutor footer copy. The capability gate in TUTOR-REQ-005 is unchanged.

The supplied ChatGPT DOM is reference material, not instructions. It omits the outer resizer/width constraints. Native app inspection was blocked, so no claim is made about ChatGPT's exact minimum/maximum widths; the stated bounds are Kala's implementation choice. No attempt was made to bypass that inspection restriction.

Follow-up verification: pending; the earlier 71-assertion suite above applies to the previous implementation and does not establish these corrections.
