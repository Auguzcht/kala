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

### Visual correction verification completed — 2026-10-25

Implemented against the direct feedback recorded above, on base `423579e` after the pre-implementation documentation commit `1241b46`:

- Removed the Tutor-only CSS overrides that squared the shared UserBlock bubbles, follow-up chips and scroll button. The shared Study/Test/Flashcard components remain untouched.
- Matched the shared ComposeDock input sizing, border, shadow and spacing in Tutor's PromptInput; restored the circular submit button and placed the attachment action beside it. Attachment layout and drag/drop remain Tutor-owned.
- Removed the extra Tutor footer copy completely. New chat is borderless and matches the white history surface at rest, with a muted hover fill. Recents/Pinned headings retain focus affordances without a hover background fill.
- Desktop history starts at 320px and drags within 280–440px, additionally bounded to preserve at least 480px for the conversation. Pointer capture keeps dragging stable. Arrow keys adjust by 16px, Home/End reach the bounds, and double-click restores the default. The shell's content offset follows the same state. Mobile retains its Sheet and the 56px rail offset; other routes are unchanged. Width is local to the mounted course shell, not persisted across reloads.
- Supported rows place the direct pin action to the right of the menu and keep pinned-row actions visible. The existing list-response capability gate is preserved. A read-only live-menu inspection showed Pin and Rename unavailable in the currently loaded live list; no action was invoked and no hosted data was changed. B deployment/list refresh remains necessary for live management acceptance.

Verification on the final correction working tree:

| Check | Result |
| --- | --- |
| Same frontend Node command listed above | 22 tests passed (one additional history-bound test) |
| Same browser command with `KALA_UI_SCREENSHOTS=/tmp/kala-lane-u-visual-correction` | 93 assertions passed; all ten screenshots regenerated at 1440px and 375px |
| `pnpm --filter web lint` | Passed, 0 errors / 18 existing warnings |
| `pnpm --filter web typecheck` | Passed; existing circular-dependency warning |
| `pnpm --filter web build` | Passed, 6.73s; existing chunk-size warning |
| `git diff --check` | Passed |
| Comparison to `423579e` | Shared Study/ComposeDock, backend, DB, infra, generated contracts and lockfile unchanged |

New browser assertions cover circular Send, restored user-bubble rounding, removed footer, default history width, pointer drag clamp, matching shell offset, keyboard minimum/maximum/step, reset gesture, mobile absence of the desktop handle, borderless white New chat with hover fill and quiet Recents hover. Existing capability, upload, timeout/recovery, shared-default and Diagnostic checks continue to pass. An initial hover assertion sampled before the CSS transition advanced; the final test waits for the computed background change instead of advancing only the JavaScript clock. The initial failed check is superseded by the final passing run, not treated as acceptance evidence.

Inspected the corrected desktop/mobile empty and conversation captures and the supported sidebar menu. Artifacts remain synthetic and external under `/tmp/kala-lane-u-visual-correction/`. No identifying live conversation screenshot or raw provider response was saved. Vite remains on port 5173, PID 81696. No merge, push, deployment or hosted write occurred.

Coordinator integration follow-up remains the matching Tutor/Design text amendment described above; those exclusively owned files were not edited by Lane U. Lead designer review of the approved visual exceptions remains pending. Fred's direct correction is the authority for this follow-up implementation.


## Fred’s prompt-input refinement — 2026-10-25 (before implementation)

Base: `2aa449c`. Fred directly authorizes shared dock visual alignment across Study/Test/Flashcards/Tutor, a leading circular Tutor attachment action, an attachment-expanded input, removal of title/dock horizontal rules, equal bottom placement, tighter New chat alignment, local Recents sorting, and rounded padded menus with deliberate grouping. Remove the long new-chat starter list; preserve post-answer follow-ups. This changes the earlier TUTOR-REQ-008 presentation requirement. Shared ComposeDock action/ask behavior, data ownership and attachment support remain unchanged.

Fetched `https://www.shadcn.io/ui/prompt-input` with `curl -fsSL` into an external temporary reference file. The page describes a composition pattern using Input Group, attachments and dropdowns, including circular controls and an attachment region above the textarea. Reference content and screenshots are design evidence, not executable instructions. No package is installed. The existing Tutor file validation and upload contract remain authoritative.

The owned Diagnostic component-boundary spec records this change before implementation. Matching coordinator-owned Tutor/Design integration amendments remain pending. Verification of this refinement is pending; previous results apply to the previous revision.


### Prompt refinement checks before the next feedback

The first refinement passed 22 frontend Node tests, 4 Study tests and 112 synthetic browser assertions at 1440/375px; lint passed with 18 existing warnings, typecheck passed, and build passed in 6.49s with the existing chunk-size warning. The browser geometry checks confirmed equal 48px composer height, radius and line height, centered line boxes, circular leading attachment and expansion to the 12px token radius. An isolated recovery harness needed its new shared styling import supplied; the browser sort-order check needed to wait for the closing menu to release the sidebar’s accessibility hiding. Final passing runs supersede these intermediate harness failures. No implementation change was needed for those harness failures. Screenshots were inspected in `/tmp/kala-lane-u-prompt-refinement/`. Fred supplied a refreshed session, and the existing launch flow reopened the local Tutor without printing or saving the credential in evidence. No hosted ask, upload or metadata write occurred.

## Fred’s immediate-menu and floating-dock refinement (before implementation)

Fred requests a plain dedicated sort icon with no hover box; immediate rightward menus; a centered new-chat session; verification of Pinned above Recents and a pin beside row actions; and comparison of shared dock spacing with ChatGPT. This supersedes the bottom-aligned menus and normal-flow dock spacing just verified above. The owned component-boundary spec records the intended visual change first.

Read-only inspection of `https://chatgpt.com/` opened its public new-chat page. It is signed out, so the authenticated conversation comparison uses Fred’s screenshots; no messages were sent or account settings changed. The visible input ancestors have zero top/bottom padding. Kala’s DESIGN rule says motion must report a real change; history-menu fade/zoom/slide effects are removed locally. Source inspection found both a 24px stream bottom inset and 24px dock top inset, producing the visible gap. The proposed shared visual correction overlaps the dock with the stream, raises its bottom inset to 16px, and reserves scroll clearance so final controls remain reachable. Shared action/submission behavior remains unchanged.

Pinned and direct pin remain API-capability gated. The current live list previously omitted `pinnedAt`, so no unsupported PATCH is attempted. The supporting API/list deployment belongs to the other worktree; this dependency must remain in the final report. Synthetic capable/legacy fixtures verify both branches. Latest refinement checks: pending.


### Immediate-menu and floating-dock verification before finishing feedback

All 125 synthetic browser assertions passed; 22 frontend Node tests and 4 Study tests passed. Lint passed with 18 existing warnings, typecheck passed, build passed in 7.16s with the existing chunk warning, and diff whitespace validation passed. Captures in `/tmp/kala-lane-u-floating-dock/` were inspected. Tests confirm normal-motion menus have no animation, rightward desktop placement/mobile containment, centered empty-chat composer, 16px bottom inset, floating stream overlap, and reachable final Study action. Pinned precedes Recents and direct pin follows the row menu in the capable fixture; the legacy gate still passes. A new trigger-geometry assertion initially queried an aria-hidden sidebar after opening the modal menu; collecting its position before opening fixed the test. No product fix was needed for that test timing.

## Fred’s Tutor finishing request (before implementation)

Remove the conversation title header completely. Match the sort trigger’s rounded focus shape to row actions and inset its focus ring so it cannot clip in the history scroll region. Keep row controls visible while their menu is open. Add recognizable sort-choice icons, an overflow-only title reveal that gently travels to the end and returns once on hover, and whole-control-driven Lucide icon feedback using the existing Kala imperative hover convention. Respect reduced motion; popup container entry/exit remains immediate. The supported Rename implementation remains gated with pinning by the list contract; the other worktree’s API integration remains a live acceptance dependency.

The public ChatGPT inspection and Fred’s supplied authenticated screenshots are the reference; no claim is made that an authenticated ChatGPT title-marquee timing was measured. UI implementation follows Fred’s requested end-and-return behavior using measured text overflow. Latest finishing checks: pending.


## Fred’s lucide-animated source correction (before implementation)

Fred explicitly rejects shared motion presets. The interim tilt/nudge/pulse wrapper is superseded and will be removed. Fetched the official site, icon index, registry JSON and MIT license with curl/read-only HTTPS. Available published variants used here: square-pen (New chat/Rename), attach-file, corner-down-left, clock and arrow-down-a-z; Remove reuses Kala’s existing lucide-animated X. The current published index/registry has no ellipsis, list-filter, pin, pin-off, pencil, trash-2 or clock-arrow-up/down variants. Unsupported glyphs stay static; date sorting uses the published clock glyph. No generic fallback animation is introduced.

Vendor only the five published icon source components, with their source URLs, SHA-256 evidence and full MIT notice. Keep their animation definitions unchanged. The shared hook forwards control-level hover/focus to each icon’s existing imperative handle and suppresses animation for reduced motion; it defines no animation. No packages or lockfile changes are needed because Motion is already installed.

Before this correction, the finishing suite passed 141 browser assertions. Its added exit assertion found that conditional CSS animation overrides still allowed the inherited exit animation. A direct Tutor-menu container animation/transition override fixed it; both states then passed. This fix remains in the final implementation. Latest icon-source verification: pending.


## Final Tutor refinement verification — 2026-10-25

Final implementation removes the interim generic animation wrapper. Five source components are vendored from the published lucide-animated registry with unchanged animation definitions and a full MIT notice in `apps/web/src/features/tutor/components/icons/LICENSE`. Kala’s existing X variant is reused. Event forwarding uses `useIconHover` and a reduced-motion guard; no shared motion preset remains. Glyphs missing from the current registry (More, Pin/Unpin, Delete and ListFilter) remain static. New chat/Rename use SquarePen, Attach uses AttachFile, Enter uses CornerDownLeft, date sorts use Clock and alphabetical sorting uses ArrowDownAZ.

Source verification removes only the two added attribution comment lines and hashes the remaining bytes; all five matched the downloaded registry source exactly. No package, lockfile, backend, generated contract or infrastructure change was made.

| Icon | Published source | SHA-256 of source content |
| --- | --- | --- |
| square-pen | https://lucide-animated.com/r/square-pen.json | `016578564470e51acae32e1d04c92b36d3cda6eb0e3e74bf6d44e34e38639622` |
| attach-file | https://lucide-animated.com/r/attach-file.json | `00998dec0fb492ffc89e404e9e64242a292be7225bc7874c357c5ddddb11e079` |
| corner-down-left | https://lucide-animated.com/r/corner-down-left.json | `47b6751892f2781e8cd335ff7db73ed412b20e421411e97de26502b87284fcfe` |
| clock | https://lucide-animated.com/r/clock.json | `d8d7b89a0cafd66027baab8f84af7d7fd0c4bcfb5d20ff4e842b28429f2fad86` |
| arrow-down-a-z | https://lucide-animated.com/r/arrow-down-a-z.json | `4ce5bec8d2319335cd74f16f3075d42272186753b7a821eccba4df496d728f37` |

Final checks:

| Check | Result |
| --- | --- |
| Frontend Node command recorded above (Tutor recovery, schema, safe errors, presentation) | 22 passed |
| Study deck external-renderer command recorded above | 4 passed; rating/replay behavior preserved |
| Browser command recorded above with `KALA_UI_SCREENSHOTS=/tmp/kala-lane-u-tutor-final` | 141 assertions passed |
| `pnpm --filter web lint` | Passed, 0 errors / 18 existing Fast Refresh warnings |
| `pnpm --filter web typecheck` | Passed; existing route-generator circular-dependency warning |
| `pnpm --filter web build` | Passed; existing chunk-size warning |
| `git diff --check` | Passed |
| Published icon byte comparison | Five matches; MIT notice retained |

Browser coverage includes 1440px/375px layouts; unchanged Diagnostic reachability and payload; shared 48px geometry/typography/radius; circular leading attachment and expanded state; centered new-chat composer; no conversation title/header rule; floating dock overlap and final Study-action clearance; rightward desktop menus/mobile containment; both menu entry and exit without animation; rounded inset sort focus ring; choice icons; visible row actions while menu is open; capable Rename/Pin and legacy gating; overflow marquee to the end and back; actual icon path animation from whole-button hover; reduced-motion static behavior; upload/draft/recovery and flip focus. All 14 captures (including sort focus and sort menu at both widths) are synthetic and external under `/tmp/kala-lane-u-tutor-final/`. No identifying live screenshot, raw provider response or credential was added.

The icon-source test adaptation initially still targeted the removed generic wrapper’s span; it now inspects each published icon’s internal SVG animation. This was a harness update, superseded by the final 141 passing assertions. The live local Tutor remains open with a valid session. No hosted ask, upload, rename, pin, deletion or submission was performed.

Frontend comparison: the requested seamless header, centered new-chat input, floating dock, rightward padded menus, deliberate separators, title reveal and persistent open-menu affordance now match the requested interaction pattern. Authenticated ChatGPT timing was not measurable in the signed-out browser; Fred’s screenshots supply that visual reference. No exact parity claim is made for every ChatGPT feature or animation timing.

Live acceptance dependency: the other worktree must integrate/deploy the list capability (`pinnedAt`, including explicit null) and PATCH contract before Rename, direct Pin/Unpin and the Pinned category can be accepted against live data. The UI is complete for both capable and legacy responses, verified with synthetic fixtures. Lead designer review and coordinator-owned Tutor/Design amendments remain integration follow-ups. Tutor’s frontend pass is ready to hand over before proceeding to Diagnostic.

AUDIT REPORT
Task / brief ID: WI-22 / APPROVAL-05 Lane U, Fred’s direct Tutor refinements
Branch and worktree: codex/ui-overhaul; /Users/fred/.codex/worktrees/2e93/kala
Base revision: 2aa449c985b14b8ea6d1d890ddaa2b308a9411d3
Files changed:
- apps/web/src/components/ai-elements/dock-layout.ts
- apps/web/src/components/shell/TutorSidebar.tsx
- apps/web/src/components/study/ComposeDock.tsx
- apps/web/src/components/study/StudyStream.tsx
- apps/web/src/features/tutor/components/TutorChat.test.mjs
- apps/web/src/features/tutor/components/TutorChat.tsx
- apps/web/src/features/tutor/components/TutorComposer.tsx
- apps/web/src/features/tutor/components/TutorConversationRow.tsx
- apps/web/src/features/tutor/components/TutorHistoryMenu.tsx
- apps/web/src/features/tutor/components/TutorTitle.tsx
- apps/web/src/features/tutor/components/TutorWelcome.tsx
- apps/web/src/features/tutor/components/icons/LICENSE
- apps/web/src/features/tutor/components/icons/arrow-down-a-z.tsx
- apps/web/src/features/tutor/components/icons/attach-file.tsx
- apps/web/src/features/tutor/components/icons/clock.tsx
- apps/web/src/features/tutor/components/icons/corner-down-left.tsx
- apps/web/src/features/tutor/components/icons/square-pen.tsx
- apps/web/src/features/tutor/hooks/use-tutor-icon.ts
- apps/web/src/features/tutor/index.ts
- apps/web/src/features/tutor/lib/presentation.ts
- apps/web/src/features/tutor/tests/presentation.test.mjs
- apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
- docs/features/diagnostic/README.md
- docs/work/handover-2026/evidence/ui-overhaul.md
REQ / WI IDs touched: DIAG-REQ-005; TUTOR-REQ-004, 005, 008, 009, 011; WI-22
Commands run and results (tests, lint, typecheck, build): 22 frontend + 4 Study tests, 141 browser assertions; lint/typecheck/build/diff check passed; five icon source hashes matched. Exact invocations are recorded above.
Spec changes made: owned Diagnostic component-boundary rules and change log recorded before each refinement; coordinator-owned Tutor/Design integration amendments remain pending.
Evidence added: this append-only report; 14 synthetic desktop/mobile captures in /tmp/kala-lane-u-tutor-final; icon URLs, checksums and MIT notice.
Anything not done, and why: live Rename/Pin acceptance requires the other worktree’s API/list deployment; no merge/push/deploy/hosted-data mutation authorized or performed.
Risks or questions for the planner: integrate matching Tutor/Design text, retain capability gating, complete lead designer review and Fred’s authenticated acceptance. Icon glyphs without a published variant intentionally stay static.
Secrets printed: none (confirmed); environment contents were not read.


## Local attachment staging and preview — before implementation, 2026-10-25

Base `75ff72a`. Fred selected “File cards + raw-text preview modal” after asking about immediate uploads and unstable corners. Current source selects -> lazy conversation creation -> upload immediately, and server detail supplies only filename/type/size/status. It has neither local staging nor downloadable contents. The old transition interpolates from rounded-full’s unbounded radius to radius-xl, which produces the late corner snap.

The owned component-boundary spec records local staging, validation, partial retry without duplicate uploads, explicit send ordering, per-chat cancellation, file cards, and bounded local raw-text modal preview before code. Keep accepted types (.txt/.md/.pdf, 5MB) and current API routes. Images and restored-file/PDF content preview require separate contracts and remain out of scope. The finite 24px-equivalent corner is derived from existing radius-xl; no new design token, parser, preview pane or backend endpoint is introduced. Coordinator-owned Tutor and DESIGN amendments remain pending integration.


### Local staging and preview verification completed — 2026-10-25

Implemented against base `75ff72a` after Fred selected the file-card/raw-preview approach:

- Selecting/dropping validates and stages local File objects; it creates no conversation and sends no upload request. Local removal sends no DELETE. Files have compact filename/type/size/state cards. TXT/MD can open a raw-text dialog; PDF is a metadata card. Existing/restored files have metadata only unless a local File is still available in this mounted chat.
- Send lazily creates/reuses one conversation, uploads the staged batch, then asks only when all attachments are ready. Successful uploads are removed from staging and reused when a failed file is retried. Partial failure preserves the question and failed files; editing the question during upload is not discarded when the captured question is sent. Server failed/processing attachments block asking until resolved or removed.
- Conversation switching stops the old batch’s remaining uploads/ask and resets its busy state without altering the new chat’s draft. An already dispatched upload may finish in its original conversation; it is not reassigned to the new chat.
- The shared 48px input retains its empty appearance with a finite corner equal to twice radius-xl. The attachment area animates height, preserving that same corner throughout; there is no interpolation from an effectively infinite radius. Reduced motion makes the expansion immediate. No shared Study action/ask behavior changed.
- Preview uses at most 128 KiB from the local File, rendered as literal text in a scrollable pre element, with a truncation notice for larger files. No Markdown parser, HTML execution, network preview request, adjustable pane or server-content endpoint is added. The modal traps focus, closes by button/Escape, restores the opener, fits 375px screens, subtly blurs the background, and suppresses entry/exit motion for reduced motion. Its close glyph animates only on hover, keeping its initial auto-focused state fully legible.

The existing entry-resume effect was found to leave its “handled” flag unset when entering an already selected chat. A later delete could resume an unrelated remaining chat. Marking the initial decision handled also for selected chats restores its documented once-on-entry behavior; the existing confirmed-delete navigation assertion now passes alongside the staging cancellation test.

Final verification:

| Check | Result |
| --- | --- |
| Frontend Node command recorded earlier (same four files) | 21 passed; obsolete radius-class unit test retired, replaced by browser geometry checks |
| Study deck external-renderer command recorded earlier | 4 passed |
| Browser command recorded earlier, with `KALA_UI_SCREENSHOTS=/tmp/kala-lane-u-attachments` | 155 assertions passed |
| `pnpm --filter web lint` | Passed; 0 errors / 18 existing warnings |
| `pnpm --filter web typecheck` | Passed; existing route-generator circular dependency warning |
| `pnpm --filter web build` | Passed; existing chunk-size warning |
| `git diff --check` | Passed |

Added browser coverage proves no upload/create on selection or preview, local-only removal, raw Markdown/HTML display without execution, dialog focus restoration, reduced-motion/mobile containment, upload-before-ask ordering, partial retry without duplicate successful uploads, draft retention and cross-chat cancellation. Earlier Diagnostic, sidebar, provider-recovery, actual icon-variant, shared dock and flip-focus checks remain passing. All 17 captures under `/tmp/kala-lane-u-attachments/` are synthetic, including staged file cards and desktop/mobile preview. Screenshots wait for expansion/modal opacity to settle; captures of an intermediate animation frame are not final acceptance evidence.

Intermediate fixes: removed an unused drag-state binding after corner state became constant; waited for the intentional exit/collapse before asserting a card was removed; waited for the expanded geometry rather than its first animation frame; narrowed a synthetic New chat selector to distinguish the action from a chat named “New chat.” The entry-resume defect above was a real behavior fix, not a selector adjustment. Final passing runs supersede these intermediate failures.

Fred’s newest session was opened through the existing launch flow, and the local Tutor input was verified visible with no expiry page. No credential was printed or added to source/evidence, and no identifying live screenshot was captured. No live ask/upload/delete/rename/pin was performed.

AUDIT REPORT
Task / brief ID: WI-22 / Tutor local attachment staging and raw-text preview
Branch and worktree: codex/ui-overhaul; /Users/fred/.codex/worktrees/2e93/kala
Base revision: 75ff72a
Files changed:
- apps/web/src/components/ai-elements/dock-layout.ts
- apps/web/src/features/tutor/components/TutorChat.tsx
- apps/web/src/features/tutor/components/TutorComposer.tsx
- apps/web/src/features/tutor/components/TutorFileCard.tsx
- apps/web/src/features/tutor/components/TutorFilePreview.tsx
- apps/web/src/features/tutor/lib/attachments.ts
- apps/web/src/features/tutor/lib/presentation.ts
- apps/web/src/features/tutor/tests/presentation.test.mjs
- apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
- docs/features/diagnostic/README.md
- docs/work/handover-2026/evidence/ui-overhaul.md
REQ / WI IDs touched: DIAG-REQ-005; TUTOR-REQ-004, 009, 011; WI-22
Commands run and results (tests, lint, typecheck, build): 21 frontend + 4 Study tests, 155 browser assertions; lint/typecheck/build/diff check passed with existing warnings.
Spec changes made: owned component-boundary amendment and change-log entry before implementation; coordinator-owned Tutor/Design text remains pending integration.
Evidence added: this append-only verification, synthetic file-card/raw-preview screenshots in /tmp/kala-lane-u-attachments.
Anything not done, and why: image uploads, PDF content preview and restored-file contents need separate contracts; they were not part of the selected local TXT/MD preview scope. No backend, migration, generated type, dependency, infrastructure, push or deployment change.
Risks or questions for the planner: integrate revised Tutor attachment lifecycle/shape wording; retain existing backend type/size limits and human live acceptance.
Secrets printed: none (confirmed); environment contents were not read.

## Attachment interaction polish and toast contrast — 2026-10-25

Base `f87bbf0`. Fred directly requested an animated drop glyph, attachment hover/preview behavior, equal top/left card insets, subtle format accents, investigation of image support, and readable badge/notification toast text. The owned component-boundary amendment was updated before implementation. The direct request authorizes the narrow shared Sonner correction; no gamification logic changes.

Findings and changes:

- The previous card rendered a noninteractive div when the local File was absent, explaining the missing hover/click for restored attachments. Every card now has a keyboard-accessible preview button and muted hover shade. TXT/MD still show raw local text when available. Restored attachments and PDFs open metadata with an explicit content-preview limitation; no unavailable content is invented or fetched. Preview stays available while removal is disabled during pending work.
- The dock's input group already contributes horizontal padding. Removed the redundant left inset from the card row, making the visible top and left card margins equal (browser geometry checked). MD, TXT and PDF glyph tiles use different subtle existing-token fills and retain text type labels; color is not the only indication of format.
- The drop overlay uses the actual published Upload variant from `https://lucide-animated.com/r/upload.json`, played on drag entry with reduced-motion gating, plus supported-type/size copy. The source body is byte-for-byte identical apart from the two attribution comments; SHA256 `bd897b41a23e7238e63b7d62070a64a7268db3dfcbfcf18f70568ee376139593`. Existing MIT license applies. No generic motion preset or dependency was added.
- Sonner previously read `theme` from next-themes, which can remain the saved dark preference even while AppProviders forces light mode. Token overrides kept the toast white, but Sonner's dark-theme description selector made the description near-white. Toaster now prioritizes `forcedTheme`, then `resolvedTheme`, and explicitly uses the readable muted-foreground token for descriptions. Synthetic success/badge, error, info and warning notices with a saved dark preference all satisfy at least 4.5:1 description contrast on their rendered background.
- Images are an existing backend limitation: `services/api/app/routers/tutor.py` accepts only text/plain, text/markdown and application/pdf, capped at 5 MiB; the upload/extraction path is text based and mirrors the storage MIME restrictions. Accepting PNG/JPG only in the picker would still fail upload. Image upload/processing/model-context support is a separate API/storage contract change. Restored-file content retrieval and PDF content previews also remain separate work. No backend, storage, generated schema or auth changes were made.

Verification:

| Command | Result |
| --- | --- |
| `pnpm --filter web exec node --test src/features/tutor/components/TutorChat.test.mjs src/features/tutor/schema/tutor.schema.test.ts src/lib/api-error.test.ts src/features/tutor/tests/presentation.test.mjs` | 21 passed |
| `KALA_BROWSER_TEST_DEPS=/Users/fred/.cache/codex-runtimes/codex-primary-runtime/dependencies/node KALA_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' KALA_UI_SCREENSHOTS=/tmp/kala-lane-u-file-polish node apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs` | 168 assertions passed |
| `pnpm --filter web lint` | Passed; 0 errors / 18 existing Fast Refresh warnings; `/tmp/kala-file-polish-lint.log` |
| `pnpm --filter web typecheck` | Passed; existing route-generator circular warning |
| `pnpm --filter web build` | Passed; existing chunk-size warning; `/tmp/kala-file-polish-build.log` |
| `git diff --check` | Passed |

The 20 synthetic captures in `/tmp/kala-lane-u-file-polish/` include drag overlay, staged cards, restored-file metadata, raw previews and toast contrast, as well as the retained Diagnostic/sidebar/dock checks. Staged desktop cards, mobile metadata and toast captures were visually inspected. Browser tests intercept all auth/API traffic and block non-localhost requests; no live upload, ask or mutation occurred. Intermediate test-harness corrections used Vite's canonical module URLs to share Sonner/theme singletons, waited for all four notifications to render, and waited for Radix's deferred focus restoration. Final passing verification supersedes those timing/module-isolation failures.

AUDIT REPORT
Task / brief ID: WI-22 / Tutor attachment polish and shared toast contrast
Branch and worktree: codex/ui-overhaul; /Users/fred/.codex/worktrees/2e93/kala
Base revision: f87bbf0
Files changed:
- apps/web/src/components/ui/sonner.tsx
- apps/web/src/features/tutor/components/TutorChat.test.mjs
- apps/web/src/features/tutor/components/TutorChat.tsx
- apps/web/src/features/tutor/components/TutorComposer.tsx
- apps/web/src/features/tutor/components/TutorDropOverlay.tsx
- apps/web/src/features/tutor/components/TutorFileCard.tsx
- apps/web/src/features/tutor/components/TutorFilePreview.tsx
- apps/web/src/features/tutor/components/icons/upload.tsx
- apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
- docs/features/diagnostic/README.md
- docs/work/handover-2026/evidence/ui-overhaul.md
REQ / WI IDs touched: DIAG-REQ-005; TUTOR-REQ-009, 011; WI-22
Commands run and results (tests, lint, typecheck, build): 21 unit tests and 168 browser assertions passed; lint/typecheck/build/diff check passed with existing warnings.
Spec changes made: owned component-boundary amendment and change-log entry before implementation; coordinator-owned Tutor/Design matching wording remains pending integration.
Evidence added: this report, source hash, rendered contrast checks and 20 synthetic screenshots.
Anything not done, and why: image uploads, restored-file contents and PDF content preview require separate backend contracts. No push, deploy, migration, hosted write or infrastructure change.
Risks or questions for the planner: integrate matching Tutor/Design wording and complete human live acceptance; keep current upload type/size constraints until the backend supports more.
Secrets printed: none (confirmed); environment contents were not read.
