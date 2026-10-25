# WI-22: Diagnostic and Tutor UI evidence

Date: 2026-10-25 (Asia/Manila). Lane U, branch `codex/ui-overhaul`, worktree `.`.

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
| `KALA_STUDY_TEST_DEPS=/private/tmp/kala-lane-f-renderer node --experimental-vm-modules --test apps/web/src/features/flashcards/tests/study-deck.test.mjs` | 4 passed; existing external renderer fixture and deprecation warning remain | (local only, not retained)
| `KALA_BROWSER_TEST_DEPS=/Users/fred/.cache/codex-runtimes/codex-primary-runtime/dependencies/node KALA_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' node apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs` | 71 browser assertions passed; all ten requested screenshots captured | (local only, not retained)
| `pnpm --filter web lint` | Passed, 0 errors / 18 pre-existing Fast Refresh warnings |
| `pnpm --filter web typecheck` | Passed; existing TanStack circular-dependency warning |
| `pnpm --filter web build` | Passed; existing circular-dependency and chunk-size warnings; final build 6.56s |
| `git diff --check` | Passed |
| Scope comparison against `c961b83` | ComposeDock, generated OpenAPI/types, manifests/lock, backend, DB and infrastructure unchanged |

The browser test uses a separate headless Chrome context with synthetic auth/API module interception and blocks non-local network destinations. It never uses Fred's session, tokens or hosted API. Assertions exercise real components/layouts: long last-question reachability, answered count/payload, responsive sidebar, unchanged non-Tutor header/56px offset, rename despite detail omission, pin/unpin, collapsed groups, delete cancel/confirm, legacy capability gating, Thinking/elapsed state, attachments, upload errors, draft preservation, inert/focus keyboard behavior and default/opt-in PromptInput behavior. The mascot is checked under reduced and ordinary motion settings. These are synthetic UI checks, not live provider, database or LMS feature acceptance.

Historical setup corrections, not accepted feature failures: the bundled Playwright browser binary was unavailable, so the script used installed Chrome explicitly; the initial result locator assumed a heading where CardTitle is a div; the separate primitive fixture needed Vite's React Refresh preamble and the optimized module's default export. A timer check installed its clock after the timer began and was unstable; installing it before page load made the final elapsed-state check deterministic. Earlier partial runs do not replace the final passing suite.

## Screenshots and visual review

Synthetic captures are external local artifacts under `/tmp/kala-lane-u-visuals/`, deliberately separate from authenticated student data: (local only, not retained)

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
| Same browser command with `KALA_UI_SCREENSHOTS=/tmp/kala-lane-u-visual-correction` | 93 assertions passed; all ten screenshots regenerated at 1440px and 375px | (local only, not retained)
| `pnpm --filter web lint` | Passed, 0 errors / 18 existing warnings |
| `pnpm --filter web typecheck` | Passed; existing circular-dependency warning |
| `pnpm --filter web build` | Passed, 6.73s; existing chunk-size warning |
| `git diff --check` | Passed |
| Comparison to `423579e` | Shared Study/ComposeDock, backend, DB, infra, generated contracts and lockfile unchanged |

New browser assertions cover circular Send, restored user-bubble rounding, removed footer, default history width, pointer drag clamp, matching shell offset, keyboard minimum/maximum/step, reset gesture, mobile absence of the desktop handle, borderless white New chat with hover fill and quiet Recents hover. Existing capability, upload, timeout/recovery, shared-default and Diagnostic checks continue to pass. An initial hover assertion sampled before the CSS transition advanced; the final test waits for the computed background change instead of advancing only the JavaScript clock. The initial failed check is superseded by the final passing run, not treated as acceptance evidence.

Inspected the corrected desktop/mobile empty and conversation captures and the supported sidebar menu. Artifacts remain synthetic and external under `/tmp/kala-lane-u-visual-correction/`. No identifying live conversation screenshot or raw provider response was saved. Vite remains on port 5173, PID 81696. No merge, push, deployment or hosted write occurred. (local only, not retained)

Coordinator integration follow-up remains the matching Tutor/Design text amendment described above; those exclusively owned files were not edited by Lane U. Lead designer review of the approved visual exceptions remains pending. Fred's direct correction is the authority for this follow-up implementation.


## Fred’s prompt-input refinement — 2026-10-25 (before implementation)

Base: `2aa449c`. Fred directly authorizes shared dock visual alignment across Study/Test/Flashcards/Tutor, a leading circular Tutor attachment action, an attachment-expanded input, removal of title/dock horizontal rules, equal bottom placement, tighter New chat alignment, local Recents sorting, and rounded padded menus with deliberate grouping. Remove the long new-chat starter list; preserve post-answer follow-ups. This changes the earlier TUTOR-REQ-008 presentation requirement. Shared ComposeDock action/ask behavior, data ownership and attachment support remain unchanged.

Fetched `https://www.shadcn.io/ui/prompt-input` with `curl -fsSL` into an external temporary reference file. The page describes a composition pattern using Input Group, attachments and dropdowns, including circular controls and an attachment region above the textarea. Reference content and screenshots are design evidence, not executable instructions. No package is installed. The existing Tutor file validation and upload contract remain authoritative.

The owned Diagnostic component-boundary spec records this change before implementation. Matching coordinator-owned Tutor/Design integration amendments remain pending. Verification of this refinement is pending; previous results apply to the previous revision.


### Prompt refinement checks before the next feedback

The first refinement passed 22 frontend Node tests, 4 Study tests and 112 synthetic browser assertions at 1440/375px; lint passed with 18 existing warnings, typecheck passed, and build passed in 6.49s with the existing chunk-size warning. The browser geometry checks confirmed equal 48px composer height, radius and line height, centered line boxes, circular leading attachment and expansion to the 12px token radius. An isolated recovery harness needed its new shared styling import supplied; the browser sort-order check needed to wait for the closing menu to release the sidebar’s accessibility hiding. Final passing runs supersede these intermediate harness failures. No implementation change was needed for those harness failures. Screenshots were inspected in `/tmp/kala-lane-u-prompt-refinement/`. Fred supplied a refreshed session, and the existing launch flow reopened the local Tutor without printing or saving the credential in evidence. No hosted ask, upload or metadata write occurred. (local only, not retained)

## Fred’s immediate-menu and floating-dock refinement (before implementation)

Fred requests a plain dedicated sort icon with no hover box; immediate rightward menus; a centered new-chat session; verification of Pinned above Recents and a pin beside row actions; and comparison of shared dock spacing with ChatGPT. This supersedes the bottom-aligned menus and normal-flow dock spacing just verified above. The owned component-boundary spec records the intended visual change first.

Read-only inspection of `https://chatgpt.com/` opened its public new-chat page. It is signed out, so the authenticated conversation comparison uses Fred’s screenshots; no messages were sent or account settings changed. The visible input ancestors have zero top/bottom padding. Kala’s DESIGN rule says motion must report a real change; history-menu fade/zoom/slide effects are removed locally. Source inspection found both a 24px stream bottom inset and 24px dock top inset, producing the visible gap. The proposed shared visual correction overlaps the dock with the stream, raises its bottom inset to 16px, and reserves scroll clearance so final controls remain reachable. Shared action/submission behavior remains unchanged.

Pinned and direct pin remain API-capability gated. The current live list previously omitted `pinnedAt`, so no unsupported PATCH is attempted. The supporting API/list deployment belongs to the other worktree; this dependency must remain in the final report. Synthetic capable/legacy fixtures verify both branches. Latest refinement checks: pending.


### Immediate-menu and floating-dock verification before finishing feedback

All 125 synthetic browser assertions passed; 22 frontend Node tests and 4 Study tests passed. Lint passed with 18 existing warnings, typecheck passed, build passed in 7.16s with the existing chunk warning, and diff whitespace validation passed. Captures in `/tmp/kala-lane-u-floating-dock/` were inspected. Tests confirm normal-motion menus have no animation, rightward desktop placement/mobile containment, centered empty-chat composer, 16px bottom inset, floating stream overlap, and reachable final Study action. Pinned precedes Recents and direct pin follows the row menu in the capable fixture; the legacy gate still passes. A new trigger-geometry assertion initially queried an aria-hidden sidebar after opening the modal menu; collecting its position before opening fixed the test. No product fix was needed for that test timing. (local only, not retained)

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
| Browser command recorded above with `KALA_UI_SCREENSHOTS=/tmp/kala-lane-u-tutor-final` | 141 assertions passed | (local only, not retained)
| `pnpm --filter web lint` | Passed, 0 errors / 18 existing Fast Refresh warnings |
| `pnpm --filter web typecheck` | Passed; existing route-generator circular-dependency warning |
| `pnpm --filter web build` | Passed; existing chunk-size warning |
| `git diff --check` | Passed |
| Published icon byte comparison | Five matches; MIT notice retained |

Browser coverage includes 1440px/375px layouts; unchanged Diagnostic reachability and payload; shared 48px geometry/typography/radius; circular leading attachment and expanded state; centered new-chat composer; no conversation title/header rule; floating dock overlap and final Study-action clearance; rightward desktop menus/mobile containment; both menu entry and exit without animation; rounded inset sort focus ring; choice icons; visible row actions while menu is open; capable Rename/Pin and legacy gating; overflow marquee to the end and back; actual icon path animation from whole-button hover; reduced-motion static behavior; upload/draft/recovery and flip focus. All 14 captures (including sort focus and sort menu at both widths) are synthetic and external under `/tmp/kala-lane-u-tutor-final/`. No identifying live screenshot, raw provider response or credential was added. (local only, not retained)

The icon-source test adaptation initially still targeted the removed generic wrapper’s span; it now inspects each published icon’s internal SVG animation. This was a harness update, superseded by the final 141 passing assertions. The live local Tutor remains open with a valid session. No hosted ask, upload, rename, pin, deletion or submission was performed.

Frontend comparison: the requested seamless header, centered new-chat input, floating dock, rightward padded menus, deliberate separators, title reveal and persistent open-menu affordance now match the requested interaction pattern. Authenticated ChatGPT timing was not measurable in the signed-out browser; Fred’s screenshots supply that visual reference. No exact parity claim is made for every ChatGPT feature or animation timing.

Live acceptance dependency: the other worktree must integrate/deploy the list capability (`pinnedAt`, including explicit null) and PATCH contract before Rename, direct Pin/Unpin and the Pinned category can be accepted against live data. The UI is complete for both capable and legacy responses, verified with synthetic fixtures. Lead designer review and coordinator-owned Tutor/Design amendments remain integration follow-ups. Tutor’s frontend pass is ready to hand over before proceeding to Diagnostic.

AUDIT REPORT
Task / brief ID: WI-22 / APPROVAL-05 Lane U, Fred’s direct Tutor refinements
Branch and worktree: codex/ui-overhaul; .
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
Evidence added: this append-only report; 14 synthetic desktop/mobile captures in /tmp/kala-lane-u-tutor-final; icon URLs, checksums and MIT notice. (local only, not retained)
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
| Browser command recorded earlier, with `KALA_UI_SCREENSHOTS=/tmp/kala-lane-u-attachments` | 155 assertions passed | (local only, not retained)
| `pnpm --filter web lint` | Passed; 0 errors / 18 existing warnings |
| `pnpm --filter web typecheck` | Passed; existing route-generator circular dependency warning |
| `pnpm --filter web build` | Passed; existing chunk-size warning |
| `git diff --check` | Passed |

Added browser coverage proves no upload/create on selection or preview, local-only removal, raw Markdown/HTML display without execution, dialog focus restoration, reduced-motion/mobile containment, upload-before-ask ordering, partial retry without duplicate successful uploads, draft retention and cross-chat cancellation. Earlier Diagnostic, sidebar, provider-recovery, actual icon-variant, shared dock and flip-focus checks remain passing. All 17 captures under `/tmp/kala-lane-u-attachments/` are synthetic, including staged file cards and desktop/mobile preview. Screenshots wait for expansion/modal opacity to settle; captures of an intermediate animation frame are not final acceptance evidence. (local only, not retained)

Intermediate fixes: removed an unused drag-state binding after corner state became constant; waited for the intentional exit/collapse before asserting a card was removed; waited for the expanded geometry rather than its first animation frame; narrowed a synthetic New chat selector to distinguish the action from a chat named “New chat.” The entry-resume defect above was a real behavior fix, not a selector adjustment. Final passing runs supersede these intermediate failures.

Fred’s newest session was opened through the existing launch flow, and the local Tutor input was verified visible with no expiry page. No credential was printed or added to source/evidence, and no identifying live screenshot was captured. No live ask/upload/delete/rename/pin was performed.

AUDIT REPORT
Task / brief ID: WI-22 / Tutor local attachment staging and raw-text preview
Branch and worktree: codex/ui-overhaul; .
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
Evidence added: this append-only verification, synthetic file-card/raw-preview screenshots in /tmp/kala-lane-u-attachments. (local only, not retained)
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
| `KALA_BROWSER_TEST_DEPS=/Users/fred/.cache/codex-runtimes/codex-primary-runtime/dependencies/node KALA_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' KALA_UI_SCREENSHOTS=/tmp/kala-lane-u-file-polish node apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs` | 168 assertions passed | (local only, not retained)
| `pnpm --filter web lint` | Passed; 0 errors / 18 existing Fast Refresh warnings; `/tmp/kala-file-polish-lint.log` | (local only, not retained)
| `pnpm --filter web typecheck` | Passed; existing route-generator circular warning |
| `pnpm --filter web build` | Passed; existing chunk-size warning; `/tmp/kala-file-polish-build.log` | (local only, not retained)
| `git diff --check` | Passed |

The 20 synthetic captures in `/tmp/kala-lane-u-file-polish/` include drag overlay, staged cards, restored-file metadata, raw previews and toast contrast, as well as the retained Diagnostic/sidebar/dock checks. Staged desktop cards, mobile metadata and toast captures were visually inspected. Browser tests intercept all auth/API traffic and block non-localhost requests; no live upload, ask or mutation occurred. Intermediate test-harness corrections used Vite's canonical module URLs to share Sonner/theme singletons, waited for all four notifications to render, and waited for Radix's deferred focus restoration. Final passing verification supersedes those timing/module-isolation failures. (local only, not retained)

AUDIT REPORT
Task / brief ID: WI-22 / Tutor attachment polish and shared toast contrast
Branch and worktree: codex/ui-overhaul; .
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

## Diagnostic introduction, alignment and selected hover — 2026-10-25

Base `bd5cff0`. Fred asked for a Skills-like explanation of the Diagnostic, a top separator, advice on footer alignment, and correction of the selected answer's lingering pale hover. His latest direction supersedes the initial request to remove all introduction. The Diagnostic spec was updated before implementation (DIAG-REQ-001/002/003/006).

Design and implementation:

- Reuse the actual Skills `PageHeader`, with Diagnostic eyebrow, “Find your starting point” and one sentence: “Answer a few questions so Kala can understand what you already know and where to begin.” It explains the task without an extra start screen, timer, progress bar, grade claim or separate hero treatment. The compact introduction sits above a full-width hairline, outside the question scroll region, and disappears for the submitted mastery reveal. Existing early-return states retain their own explanations.
- Give header, card column, footer count, submit action and error copy the same 800px maximum column and 16px/24px responsive side padding. The footer separator remains full width. Submit stays at the card's right edge even when the mobile footer wraps; the count stays at its left edge. The last long question remains completely reachable above the footer.
- The shared AnswerableCard applied its neutral hover shade unconditionally, including to an orange selected answer, so a clicked choice looked pale until the cursor left. Apply that neutral hover only to unselected unanswered choices. Selected buttons keep the normal orange Button variant hover. Add aria-pressed for the selected state; choice changes, pending/result locks, grading and submission payloads are unchanged. This is a narrow shared visual fix directly requested by Fred, not a Study behavior change.

Verification:

| Command | Result |
| --- | --- |
| Browser command recorded above with `KALA_UI_SCREENSHOTS=/tmp/kala-lane-u-diagnostic-polish` | 186 assertions passed | (local only, not retained)
| `KALA_STUDY_TEST_DEPS=/private/tmp/kala-lane-f-renderer node --experimental-vm-modules --test apps/web/src/features/flashcards/tests/study-deck.test.mjs` | 4 passed; existing renderer deprecation/VM-module notices | (local only, not retained)
| `pnpm --filter web lint` | Passed, 0 errors / 18 existing Fast Refresh warnings; `/tmp/kala-diagnostic-polish-lint.log` | (local only, not retained)
| `pnpm --filter web typecheck` | Passed; existing route-generator circular warning; `/tmp/kala-diagnostic-polish-typecheck.log` | (local only, not retained)
| `pnpm --filter web build` | Passed; existing chunk-size warning; `/tmp/kala-diagnostic-polish-build.log` | (local only, not retained)
| `git diff --check` | Passed |

New assertions cover purpose copy, header/card/footer edge alignment, top separator, click while leaving the pointer stationary, pointer leave/re-entry, selection changes without double counting, keyboard state, persistent introduction while scrolling, last-question clearance and removal of the introduction on results. Existing synthetic submission assertions still prove the original six-answer payload. CSS hover comparisons wait for the browser's real color transition to finish; an initial fake-JavaScript-clock sample measured intermediate CSS colors and was corrected without changing the implementation.

Desktop introduction, mobile introduction and the long final mobile question were visually inspected. Synthetic screenshots are in `/tmp/kala-lane-u-diagnostic-polish/`, including `diagnostic-introduction-1440.png`, `diagnostic-introduction-375.png` and `diagnostic-375.png`. Browser auth/API are intercepted and non-localhost requests blocked. No live Diagnostic submission, generation, grade write or due-rule change occurred. (local only, not retained)

AUDIT REPORT
Task / brief ID: WI-22 / Diagnostic purpose, aligned submission and selected-answer hover
Branch and worktree: codex/ui-overhaul; .
Base revision: bd5cff0
Files changed:
- apps/web/src/components/study/AnswerableCard.tsx
- apps/web/src/features/diagnostic/components/DiagnosticPanel.tsx
- apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
- docs/features/diagnostic/README.md
- docs/work/handover-2026/evidence/ui-overhaul.md
REQ / WI IDs touched: DIAG-REQ-001, 002, 003, 006; WI-22
Commands run and results (tests, lint, typecheck, build): 186 browser assertions and 4 Study tests passed; lint/typecheck/build/diff check passed with existing warnings.
Spec changes made: replace the old introduction-removal rule with compact purpose copy; align footer contents; add selected-hover/accessible-state acceptance before implementation.
Evidence added: this report and synthetic desktop/mobile screenshots.
Anything not done, and why: no Diagnostic API, due logic, grade flow or infrastructure change; no push, merge or deployment.
Risks or questions for the planner: Fred's live visual acceptance remains; mobile footer intentionally wraps to retain readable controls and aligned outer edges.
Secrets printed: none (confirmed); environment contents were not read.


## Diagnostic completion and app-wide waiting indicators — 2026-10-25

Base `6e368ae`. Fred directly requested left alignment to the shell header, one Test/Study-style completion view with confetti and animated mastery progression, a primary workspace exit and secondary twin exit, and the shared animated Spinner throughout actual waiting states. This direct request expands the visual write scope beyond the earlier Lane U paths. The owned Diagnostic spec was amended before implementation; coordinator-owned Tutor/Design specs were not edited.

Implementation and findings:

- The Diagnostic introduction now uses the shell breadcrumb's 20px left gutter. Question cards and submission keep their shared 800px maximum column and responsive padding; the answering footer is removed from results.
- A focused, persistent results panel replaces the old completion card/dialog/footer combination. It presents the returned answer count and mastery rows, one “Back to workspace” action and one “View your twin” action. Successful submission takes precedence over question-query refetch states until the sitting unmounts. A fresh visit uses the existing backend due state. Empty mastery rows retain saved-answer copy and both exits. No score, answer key or mastery movement is invented.
- The existing MasteryDelta reveal and prior-to-posterior marker animation run from stable response rows. Kala's existing celebrateOnce helper runs once per submitted sitting when motion is allowed. Reduced motion shows final progression without confetti. The exit icons use existing published lucide-animated components driven from whole-button hover/focus, with reduced-motion gating; no shared wiggle preset.
- Visual review found mastery labels overlapping at 375px. Mobile rows now stack skill name, track and labels; desktop rows stay inline. Long mobile names wrap and desktop names retain a full-name title. Browser checks assert internal track/label separation, not only absence of viewport overflow.
- Shared LoadingRegion preserves skeleton layouts and adds one accessible Spinner per region. LoadingPanel, assistant thinking labels and loading toasts now reuse the same primitive. Student coverage includes workspace, Skills/topic pickers, Study/Test browsers, Twin, gamification, lesson checks, Tutor conversation/preview/save/pin/delete, Diagnostic preparation/submission and Study continuation. Instructor coverage includes plan, roster, stats/charts, heatmap, at-risk/triage/record/drill-down, recommendations, matching and proposal review/refresh. Building notices receive indicators only for actual building states. Existing Spinner coverage in launch, ComposeDock, PromptInput and Study/Test actions remains.
- The waiting inventory distinguishes actual request flags from placeholder ellipses, truncated names, menu dots, static errors, unavailable content and no-data fallbacks. No request, auth, grading, state ownership or pending-lock behavior was changed for the spinner pass. Source inventory: `/tmp/kala-waiting-inventory.txt`. (local only, not retained)

Verification:

| Command | Result |
| --- | --- |
| Browser command recorded above, with `KALA_UI_SCREENSHOTS=/tmp/kala-lane-u-completion` | 211 assertions passed against final source | (local only, not retained)
| `pnpm --filter web exec node --test src/features/tutor/components/TutorChat.test.mjs src/features/tutor/schema/tutor.schema.test.ts src/lib/api-error.test.ts src/features/tutor/tests/presentation.test.mjs` | 21 passed |
| `KALA_STUDY_TEST_DEPS=/private/tmp/kala-lane-f-renderer node --experimental-vm-modules --test apps/web/src/features/flashcards/tests/study-deck.test.mjs` | 4 passed after Study continuation changes; existing renderer/VM notices | (local only, not retained)
| `pnpm --filter web lint` | Passed; 0 errors / 18 existing Fast Refresh warnings; `/tmp/kala-completion-lint.log` | (local only, not retained)
| `pnpm --filter web typecheck` | Passed; existing route-generator warning; `/tmp/kala-completion-typecheck.log` | (local only, not retained)
| `pnpm --filter web build` | Passed, including project-reference TypeScript build; existing chunk-size warning; `/tmp/kala-completion-build.log` | (local only, not retained)
| `git diff --check` | Passed |

Browser coverage includes left-header geometry, shared card/footer alignment, pending submission lock and Spinner, exactly one exit per destination, no dialog/footer on results, real marker movement, once-only real confetti, reduced motion, refetch retention, empty mastery rows, fresh caught-up visit, both navigation destinations, mobile long names and shared loading region resolution. Synthetic auth/API interception and non-localhost blocking prevent live submissions or uploads. Desktop introduction, desktop results/confetti and mobile results captures were visually inspected in `/tmp/kala-lane-u-completion/`, notably `diagnostic-introduction-1440.png`, `diagnostic-results-1440.png`, `diagnostic-results-motion-1440.png` and `diagnostic-results-375.png`. (local only, not retained)

An intermediate invalid animated-icon import was caught by the actual project-reference build and corrected to the existing ChevronLeft component. The final build and browser run pass. The user's supplied session was refreshed through the existing local launch route and course navigation was verified; that is session restoration only, not authenticated Diagnostic feature acceptance. No credential was printed or persisted in source, evidence or screenshots.

AUDIT REPORT
Task / brief ID: WI-22 / Diagnostic completion and app-wide Spinner visual correction
Branch and worktree: codex/ui-overhaul; .
Base revision: 6e368ae
Files changed:
- apps/web/src/components/kala/mastery-delta.tsx
- apps/web/src/components/shared/LoadingPanel.tsx
- apps/web/src/components/shared/LoadingRegion.tsx
- apps/web/src/components/shell/CourseShell.tsx
- apps/web/src/components/shell/TutorSidebar.tsx
- apps/web/src/components/study/AssistantBlock.tsx
- apps/web/src/components/study/TopicLanding.tsx
- apps/web/src/components/ui/sonner.tsx
- apps/web/src/features/diagnostic/components/DiagnosticPanel.tsx
- apps/web/src/features/diagnostic/components/DiagnosticResults.tsx
- apps/web/src/features/flashcards/components/FlashcardDeck.tsx
- apps/web/src/features/gamification/components/GamificationSummary.tsx
- apps/web/src/features/instructor/components/AtRiskList.tsx
- apps/web/src/features/instructor/components/AutoMatchedSection.tsx
- apps/web/src/features/instructor/components/CohortCharts.tsx
- apps/web/src/features/instructor/components/CohortStats.tsx
- apps/web/src/features/instructor/components/DecisionCenter.tsx
- apps/web/src/features/instructor/components/Heatmap.tsx
- apps/web/src/features/instructor/components/LearnerRecord.tsx
- apps/web/src/features/instructor/components/LearnerTriage.tsx
- apps/web/src/features/instructor/components/RosterTable.tsx
- apps/web/src/features/instructor/components/SkillReviewPanel.tsx
- apps/web/src/features/instructor/components/StudentDrillDown.tsx
- apps/web/src/features/lessons/components/LessonChat.tsx
- apps/web/src/features/plan/components/InstructorPlan.tsx
- apps/web/src/features/skill-hub/components/SkillHub.tsx
- apps/web/src/features/skill-hub/components/StudyBrowser.tsx
- apps/web/src/features/skill-hub/components/TestBrowser.tsx
- apps/web/src/features/tutor/components/TutorChat.tsx
- apps/web/src/features/tutor/components/TutorConversationRow.tsx
- apps/web/src/features/tutor/components/TutorFilePreview.tsx
- apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
- apps/web/src/features/twin/components/TwinView.tsx
- apps/web/src/routes/course/index.tsx
- docs/features/diagnostic/README.md
- docs/work/handover-2026/evidence/ui-overhaul.md
REQ / WI IDs touched: DIAG-REQ-001, 002, 003, 007, 008; WI-22
Commands run and results (tests, lint, typecheck, build): 211 browser assertions, 21 frontend unit tests and 4 Study tests passed; lint/typecheck/build/diff check passed with existing warnings.
Spec changes made: left shell-gutter introduction; single persistent completion with returned mastery animation, once-only confetti and two exits; real shared waiting indicators across Kala, defined before implementation and marked implemented with evidence.
Evidence added: this report, waiting-state inventory, synthetic desktop/mobile results and motion screenshots, browser completion/loading/navigation regressions.
Anything not done, and why: human live feature acceptance remains; no backend/due-rule/schema/grading change, push, merge, deploy, migration, hosted write or infrastructure change.
Risks or questions for the planner: direct user scope spans shared student/instructor presentation; review integration with other worktrees and obtain lead designer/live acceptance. Returned empty mastery rows are supported; no synthetic mastery data is shown in production.
Secrets printed: none (confirmed); environment contents were not read.


## Dashboard baseline count trace — 2026-10-25

Base `fdef8d4`. Fred requested investigation of a workspace notice reporting five skills still needing a baseline after a completed sitting. This is a read-only trace; no behavior/spec change or student-evidence repair was requested or performed.

Observed and verified:

- Reloaded the existing workspace and waited for the notice: the count remains five after a fresh load. Submission already invalidates the `diagnostic-status` query in `use-diagnostic.ts`; this is not explained by its 60-second cache alone.
- Tenant/course/user-scoped read-only database queries confirm 14 approved skills, nine distinct approved skills with Diagnostic evidence, and five without it. The latest sitting saved six distinct skills, all six newly diagnosed. Reconstructing the pre-sitting set from older evidence gives 11 due skills. No answer content or credentials are included here.
- The first ten due skills contained the six answered skills and four skills whose bank states are `no_material`. The eleventh skill was outside `MAX_DIAGNOSTIC_QUESTIONS`, because the route caps candidates before checking availability. This reconstructs the six-question sitting without implying that submission lost answers.
- Four remaining skills are `no_material`: the two service/deployment-model skills, EC2 troubleshooting, and cloud architecture design. The fifth, cloud computing essentials, is bank `ready` with 12 live approved MCQs. All 12 have a non-null last-tested exposure for this learner. A read-only call to the current `pick_diagnostic_item` selector returns no item, confirming the exhausted-pool case. Bank readiness alone is not learner-specific Diagnostic availability.
- Therefore all five legitimately lack Diagnostic evidence under the existing due definition, but zero currently have a selectable Diagnostic question. The dashboard labels the total as “new skills” and offers an action without distinguishing missing material or an exhausted unseen-item pool.

Source trace:

- `apps/web/src/routes/course/index.tsx`: renders `dueSkillCount` directly with “new skills need a baseline”.
- `apps/web/src/features/diagnostic/hooks/use-diagnostic.ts`: submission invalidates the status query; the question query is invalidated without immediate refetch to preserve completion.
- `services/api/app/routers/diagnostic.py`, `_skills_needing_diagnostic` and `get_diagnostic_status`: count approved skills without this learner's `type=diagnostic` evidence, independently of content/readiness/exposure.
- The same route's `get_diagnostic`: slices to ten before filtering `no_material`, readiness and available items; skipped/exhausted skills enter `failedSkillIds`.
- `services/api/app/bank/serving.py`, `pick_diagnostic_item`: only returns an approved live bank MCQ without a previous tested exposure; no fallback for a fully tested pool.

Recommended follow-up, requiring a deliberate API/spec decision rather than hiding the notice locally: distinguish never-diagnosed totals from actionable Diagnostic availability and unavailable/preparing reasons; make the workspace action reflect actionable availability; select available candidates before applying the sitting limit; define the baseline policy for a learner who has already tested every item. Preserve existing evidence and never mark skipped skills diagnosed just to clear a badge. Backend Diagnostic/bank ownership and matching contracts must be coordinated before implementation. This trace does not change those contracts.

AUDIT REPORT
Task / brief ID: WI-22 / dashboard baseline-count investigation
Branch and worktree: codex/ui-overhaul; .
Base revision: fdef8d4
Files changed: docs/work/handover-2026/evidence/ui-overhaul.md only
REQ / WI IDs touched: DIAG-REQ-004/007 investigation; WI-22
Commands run and results (tests, lint, typecheck, build): source trace, fresh workspace reload, scoped SELECT queries and read-only bank-selector query confirmed counts and zero selectable remaining questions; diff check passed. Build/unit tests not rerun for evidence-only change.
Spec changes made: none; existing due semantics verified, availability/product mismatch recorded for a deliberate follow-up.
Evidence added: this aggregated trace and root causes; no learner identifier, raw answer, token or secret saved.
Anything not done, and why: no backend/frontend behavior change; user requested a trace. No live generation, submission, data repair, hosted write, migration, push or deploy.
Risks or questions for the planner: status availability must handle no-material and exhausted unseen-question pools; broad due-rule change belongs to the backend/bank owner with spec and regression coverage.
Secrets printed: none (confirmed); existing settings loaded programmatically for scoped read-only access, no environment values printed.


## Header comparison, instructor identity trace and review feedback — 2026-10-25

Base `fe6a70b`. Fred asked to compare Diagnostic typography with Skills/Twin, trace two active student accounts that appear unrecorded in the hosted instructor roster, and make Approve/Reject waiting feedback perceptible. The direct request authorizes the focused instructor UI changes below. The instructor spec was absent in this checkout (the registry already tracks broader instructor completeness under WI-08); a focused `instructor-insights/README.md` amendment was written from the feature template before implementation. It defines only this feedback correction, not a complete instructor/backend specification.

Typography verification:

- Diagnostic, Skills and Twin already render the same PageHeader component. Computed browser styles at 1440px and 375px confirm identical title/eyebrow/description font family, font size, font weight, line height and tracking: 24px page titles and 14px descriptions. No speculative font change was made. The existing Diagnostic left-shell-gutter placement remains. Question prompts retain AnswerableCard's separate 18px reading style; they are not PageHeader titles.
- Added six cross-route typography assertions to the retained browser suite. Synthetic Skills and Diagnostic header captures were visually compared at the same viewport/zoom. Files include `/tmp/kala-lane-u-review-polish/skills-header-1440.png` and `diagnostic-introduction-1440.png`. (local only, not retained)

Read-only identity investigation:

- Tenant-scoped users and their profiles show two identity records for each of the two named learners. Within each pair, normalized email matches (raw emails and user/LMS identifiers are not stored here). The enrolled account uses Blackboard's internal REST identifier; the actively used account uses a different LTI identifier. Each account already has its own alias mapping.
- The first pair's enrolled record has zero course evidence/mastery, while the active non-enrolled record has 384 evidence events and 12 mastery rows. The second pair's enrolled record has 40 older practice events and two mastery rows, while the active non-enrolled record has 13 recent events and seven mastery rows. Both active records have zero enrollments in this course.
- A read-only call to the actual `cohort.roster` function returns 25 enrolled learners and reproduces the screenshot's named rows: zero attempts/not-started and 40 attempts/needs-support. The active identities are excluded by the enrollment filter; the activity has not disappeared.
- Source chain: `cohort.student_ids` requires course enrollment and student role; `_mastery`/`_evidence` join by the resulting user IDs. `db.resolve_user` returns an existing alias hit before attempting same-email discovery. Consequently the pre-existing split aliases continue to resolve to different accounts despite matching email. `_sync_roster` retains the REST-resolved enrolled IDs and removes unmatched student enrollments, so a student launch alone is not a durable reconciliation of the pair.
- This is an identity/enrollment split, not a missing spinner, display-name issue or frontend roster-cache correction. No account merge, alias reassignment, evidence/mastery/SRS update or enrollment write was performed. Existing `scripts/merge_duplicate_user.py` documents the historical failure mode, but a maintainer must review its current table/collision coverage before any repair. Both sides of the second pair carry real history; a safe repair must preserve both, reconcile aliases/enrollments and verify/recompute dependent state as appropriate. Never join progress by display name in the client. No claim is made about when the historical duplication first occurred.

Feedback implementation (INSTR-REQ-001/002):

- The real API call begins immediately. `withDecisionFeedback` retains its result/error for a minimum 350ms presentation interval; slower requests retain their full pending duration. Skill review controls remain disabled through proposal-list refresh, with the existing shared Spinner only on the selected action and an explicit failure/retry message.
- Recommendation decisions previously changed cached status optimistically in `onMutate`, immediately unmounting the card that contained its Recording Spinner. They now keep the card mounted until confirmation and the minimum interval, then update from the validated server response and refresh the existing query keys. Choice buttons and editable notes lock during recording. Failure preserves the selected choice/notes and the existing error toast for retry; it never moves the decision to history. The server's instructor gate and API payloads are unchanged.
- No generic icon motion or new dependency was introduced. Shared Spinner is static under reduced motion. Scope is local source; the separate hosted instructor site has not been deployed by this task.

Verification:

| Command | Result |
| --- | --- |
| Retained browser command with `KALA_UI_SCREENSHOTS=/tmp/kala-lane-u-review-polish` | 217 assertions passed, including six typography checks | (local only, not retained)
| Same browser runtime/executable variables, running `node apps/web/src/features/instructor/tests/review-feedback.browser.mjs` | 63 assertions passed for fast approve/reject, slow responses, failures, retries, confirmed recommendation approve/modify/decline, keyboard and reduced motion |
| `pnpm --filter web lint` | Passed, 0 errors / 18 existing Fast Refresh warnings; `/tmp/kala-instructor-polish-lint.log` | (local only, not retained)
| `pnpm --filter web typecheck` | Passed; existing route-generator warning; `/tmp/kala-instructor-polish-typecheck.log` | (local only, not retained)
| `pnpm --filter web build` | Passed including project-reference TypeScript check; existing chunk-size warning; `/tmp/kala-instructor-polish-build.log` | (local only, not retained)
| Scoped SELECTs and read-only `cohort.roster` | Confirmed identity split and reproduced enrolled-record metrics |
| `git diff --check` | Passed |

Synthetic pending-state screenshots in `/tmp/kala-instructor-feedback/` were visually inspected: `skill-approved-pending.png`, `skill-rejected-pending.png` and `recommendation-recording.png`. Browser tests block non-localhost requests and intercept all review APIs; no actual approval, rejection, assignment or model call occurred. Initial fixture-only failures were corrected by installing Vite's refresh preamble, using its default ReactDOM export and canonical TanStack Query module URL, and flushing paused-clock notification timers; final passing tests use real components/hooks. (local only, not retained)

AUDIT REPORT
Task / brief ID: WI-22 / header comparison, instructor identity trace and visible review feedback
Branch and worktree: codex/ui-overhaul; .
Base revision: fe6a70b
Files changed:
- apps/web/src/features/instructor/components/DecisionCenter.tsx
- apps/web/src/features/instructor/components/SkillReviewPanel.tsx
- apps/web/src/features/instructor/hooks/use-instructor.ts
- apps/web/src/features/instructor/lib/decision-feedback.ts
- apps/web/src/features/instructor/tests/review-feedback.browser.mjs
- apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
- docs/features/instructor-insights/README.md
- docs/work/handover-2026/evidence/ui-overhaul.md
REQ / WI IDs touched: DIAG-REQ-001/008; INSTR-REQ-001/002; WI-22
Commands run and results (tests, lint, typecheck, build): 217 retained browser assertions and 63 instructor feedback assertions passed; lint/typecheck/build/diff check passed with existing warnings; scoped read-only identity/roster queries reproduced the report.
Spec changes made: focused instructor feedback amendment before implementation, superseding optimistic recommendation removal and defining minimum visible waiting; broader WI-08 specification remains incomplete.
Evidence added: this report, cross-route typography comparisons, synthetic feedback tests/screenshots and aggregated identity trace.
Anything not done, and why: no font change because computed header typography already matches; no hosted identity repair, deployment, real decision, migration, backend edit or push. Human live acceptance remains.
Risks or questions for the planner: prepare a reviewed human-run canonical identity repair that preserves both histories, reconciles aliases and enrollment and checks dependent tables; integrate the focused instructor spec with WI-08. Separate hosted instructor site needs normal release integration before it shows local UI changes.
Secrets printed: none (confirmed); existing settings loaded for scoped read-only queries without printing credentials or environment values.


## Diagnostic margins, readiness values and paged evidence — 2026-10-25

Base `fc75b6c`. Fred clarified that Diagnostic should match the Skills/Twin content margins, requested larger readiness numbers in both student and instructor donuts, removal of the Focus area heading icon, and instructor-sized evidence pagination in both views. The Diagnostic margin rule was amended before implementation, explicitly superseding the earlier breadcrumb-gutter direction. The broader Twin spec was absent in this checkout under WI-08; a focused Twin presentation amendment was created from the feature template before implementation. This task owns only these directly requested presentation paths, not a full Twin/backend contract.

Implementation and findings:

- Diagnostic PageHeader now has the same 24px horizontal padding below lg, 40px at lg, 32px vertical padding and centered max-screen-2xl width as the Skills/Twin page content. Its full-width separator and independent question scroll region remain; question/footer alignment is unchanged. Typography remains shared.
- A 1920px browser comparison caught a second margin cause: `CourseShell` used raw prefix matching, so `/course/skills` incorrectly matched the singular `/course/skill` session prefix and lost the normal maximum width. Matching now respects exact route/segment boundaries. The plural Skills picker matches Twin and Diagnostic at wide widths; `/course/skill/{id}` still retains its full-width session shell. This changes layout classification only, not route registration, auth or navigation.
- MasteryRing's center was unconditionally text-xs (12px), including 176px and 144px readiness rings. Rings at least 128px now use the same text-5xl (48px), monospaced, semibold value; 56px skill rings keep the compact 12px value. Null, zero and 100 fit, and the existing fill and rolling-number motion remain reduced-motion aware. The accessible label now includes readiness context, band and value instead of replacing the value with the context label.
- Removed only the decorative Zap icon and its layout gap from the shared TwinBody Focus area heading. Skill data, mastery, practice action and owner-specific behavior remain.
- Shared EvidenceLedger now shows ten events per page in returned order, with a range labelled “recent events”, previous/next, active page and the existing pageWindow helper. It uses the same Pagination primitives/default 40px control sizing as the instructor roster. Endpoints expose aria-disabled and are removed from tab order; links have actual hrefs and prevent hash navigation. Mobile retains full-size previous/current/next controls, with stacked rows and unbroken outcome labels. Long names wrap on mobile and retain full-name titles on desktop.
- Page replacement is immediate instead of replaying an entry animation for an entire page. New arrivals in the current page retain the existing reveal. Empty/one-page lists hide the pager, a shrinking list clamps the page, and learner changes remount the ledger/twin presentation so another learner cannot inherit a previous page. LearnerRecord and instructor twin drill-down share these components.
- Scope is the existing returned history window: student Twin supplies at most 20 recent events and instructor learner record at most 200. No full-history API, cursor, query limit, mastery arithmetic, evidence mutation or schema was added. The total is explicitly a recent-window count, not lifetime evidence. Full-history server pagination remains separate work.

Verification:

| Command | Result |
| --- | --- |
| Retained browser command with `KALA_UI_SCREENSHOTS=/tmp/kala-lane-u-twin-polish` | 219 assertions passed, including desktop/mobile header geometry and retained Diagnostic/Tutor/Study checks | (local only, not retained)
| Same browser runtime/executable variables, running `node apps/web/src/features/twin/tests/presentation.browser.mjs` | 148 assertions passed |
| `pnpm --filter web lint` | Passed, 0 errors / 18 existing Fast Refresh warnings; `/tmp/kala-twin-polish-lint.log` | (local only, not retained)
| `pnpm --filter web typecheck` | Passed; existing route-generator warning; `/tmp/kala-twin-polish-typecheck.log` | (local only, not retained)
| `pnpm --filter web build` | Passed including project-reference TypeScript check; existing chunk-size warning; `/tmp/kala-twin-polish-build.log` | (local only, not retained)
| `git diff --check` | Passed |

New checks exercise both motion preferences at 1440px/375px, null/0/100 ring bounds, preserved small-ring density, accessible readiness labels, ten-row boundaries, partial final page, keyboard and numbered navigation, no hash jump, disabled endpoints, 200-event windowing, shrinking/empty/one-page data, no page-entry replay, 40px control heights and horizontal overflow. Integrated real student Twin and instructor LearnerRecord routes verify larger readiness values and the shared ledger. A 1920px comparison verifies the centered margin match and preservation of the singular skill-session layout. An initial synthetic Diagnostic fixture lacked required bloomLevel and was corrected to the actual response schema; the wide-screen failure then exposed and led to the real shell-prefix correction.

Synthetic screenshots were visually inspected in `/tmp/kala-twin-presentation/`: `student-twin-1440.png`, `instructor-readiness-1440.png`, `instructor-ledger-1440.png`, `ledger-1440.png`, `ledger-375.png` and `diagnostic-1920.png`. Retained introduction captures are in `/tmp/kala-lane-u-twin-polish/`. All browser fixtures intercept auth/API and block non-localhost requests. No live Diagnostic submission, teacher decision, upload, model call or hosted data read/write was performed in this task. (local only, not retained)

AUDIT REPORT
Task / brief ID: WI-22 / matching margins, readable readiness and bounded evidence browsing
Branch and worktree: codex/ui-overhaul; .
Base revision: fc75b6c
Files changed:
- apps/web/src/components/kala/evidence-ledger.tsx
- apps/web/src/components/kala/mastery-ring.tsx
- apps/web/src/components/shell/CourseShell.tsx
- apps/web/src/features/diagnostic/components/DiagnosticPanel.tsx
- apps/web/src/features/instructor/components/LearnerRecord.tsx
- apps/web/src/features/instructor/components/StudentDrillDown.tsx
- apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
- apps/web/src/features/twin/components/TwinBody.tsx
- apps/web/src/features/twin/tests/presentation.browser.mjs
- docs/features/diagnostic/README.md
- docs/features/twin/README.md
- docs/work/handover-2026/evidence/ui-overhaul.md
REQ / WI IDs touched: DIAG-REQ-001; TWIN-REQ-001/002/003; WI-22
Commands run and results (tests, lint, typecheck, build): 219 retained and 148 Twin presentation browser assertions passed; lint/typecheck/build/diff check passed with existing warnings.
Spec changes made: replace breadcrumb alignment with Skills/Twin page-content margins and segment-aware layout; focused Twin presentation requirements written before implementation and marked implemented with evidence.
Evidence added: this report, desktop/mobile/wide-screen screenshots, ring/ledger integration and geometry regressions.
Anything not done, and why: no full-history backend pagination (existing recent-window contracts retained), deployment, push, hosted mutation, migration, dependency or infrastructure change. Human visual acceptance remains.
Risks or questions for the planner: integrate focused Twin spec with WI-08; student/instructor response caps remain 20/200; shared rings and ledger intentionally apply to both student and instructor callers.
Secrets printed: none (confirmed); no environment values or credentials read for this task.


## Final frontend audit and handoff — 2026-10-25

Application base `47b9700`. Fred requested a comprehensive student/instructor UI/UX handoff, remaining flows/stale paths and detailed high-priority bug traces. The [frontend finalization handoff](frontend-finalization-handoff.md) consolidates the implemented work, fixed-bug register, Alfred/Hanna identity split, Diagnostic availability mismatch, shared provider dependency, API-capability integration, route inventory and remaining acceptance matrix. It is an audit, not a claim of production acceptance or permission for hosted repair.

Current-source findings not fixed by this documentation task: inert Diagnostic load-error Retry; older roster/proposal/Twin-skill pagers without keyboard-focusable anchors; Skills/legacy picker fetch failures conflated with empty courses; Twin Focus area's Practice this losing its skill context; role-insensitive root-error/not-found destinations; public scaffold and stale session-expiry copy; bounded evidence/count semantics requiring explicit contracts. Exact file/line locations and proposed acceptance are in the handoff. Data-dependent tour branches and full live student/instructor flows remain to be rehearsed rather than claimed tested.

Correction to the previous section's instructor window statement: `cohort.learner_record` reads up to 200 events for statistics but serializes only `events[:25]` into the response evidence array. Student Twin returns up to 20. The shared ledger's synthetic 200-event test proves component capacity, not a 200-event live response. The focused Twin spec's observed API description is corrected; historical verification records remain intact.

Verification for this documentation-only task: source/route/spec/evidence inspection and read-only inspection of the separate provider lane's evidence. Relative-link checks and `git diff --check` passed. Application tests/lint/typecheck/build were not rerun without application changes; the handoff names their recorded revisions and limits. No new hosted reads, model calls, mutations, decisions, migration, push or deployment occurred. No message was sent to another task or external recipient.

AUDIT REPORT
Task / brief ID: WI-22 / final student and instructor frontend UI/UX handoff
Branch and worktree: codex/ui-overhaul; .
Base revision: 47b9700
Files changed: docs/work/handover-2026/evidence/frontend-finalization-handoff.md; docs/work/handover-2026/evidence/ui-overhaul.md; docs/features/twin/README.md
REQ / WI IDs touched: DIAG-REQ-001–008, TUTOR-REQ-001–011, INSTR-REQ-001/002, TWIN-REQ-001/002/003 referenced; WI-22; related integration dependencies recorded, no new IDs allocated.
Commands run and results (tests, lint, typecheck, build): source/route/evidence review; relative-link and diff-whitespace checks passed. Existing revision-specific tests/build reported; not rerun for documentation-only changes.
Spec changes made: correct observed instructor ledger response from 200 to 25 rows, distinguishing the internal read; no behavior change.
Evidence added: comprehensive linked handoff and explicit correction above.
Anything not done, and why: no application fixes in this audit; live acceptance, identity repair, availability contract and provider recovery remain separate approved work. No hosted writes, merge, push, deploy, migrations or external messages.
Risks or questions for the planner: identity and availability correctness, provider recovery, keyboard/recovery/navigation findings and bounded data semantics must be resolved before unconditional sign-off; coordinator specification/API integration remains.
Secrets printed: none (confirmed).
