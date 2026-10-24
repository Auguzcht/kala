---
feature: diagnostic
req_prefix: DIAG
owner_role: product owner
status: active
code:
  web: apps/web/src/features/diagnostic/
  api: services/api/app/routers/diagnostic.py
  worker: []
  db: []
tests: [apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs]
---

# Course diagnostic

## Purpose

Students establish a baseline for course skills through the Diagnostic entry in the course sidebar. This specification defines the APPROVAL-05 presentation change; diagnostic selection, generation, grading and due rules retain their existing contracts.

## Actors and permissions

| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| authenticated student in a course | Open the course diagnostic, select answers and submit the sitting | Supply trusted identity, role or institution through the client |

## Requirements

### DIAG-REQ-001: Explain the Diagnostic's purpose with a compact introduction

- Rule: While answering, show the shared PageHeader pattern used by Skills: Diagnostic eyebrow, "Find your starting point" title, and "Answer a few questions so Kala can understand what you already know and where to begin." explanation. Use exactly the Skills/Twin page-content margins: 24px horizontal padding below the lg breakpoint, 40px at lg and above, 32px top/bottom padding, and the same centered max-screen-2xl container. This supersedes the earlier breadcrumb-gutter alignment. Shell session-layout matching must respect route segments: `/course/skills` is the bounded picker, while `/course/skill/{id}` retains its session layout. Keep the full-width hairline separator. It stays outside the question scroll region and is removed for the submitted-result reveal. Omit the old "Build your baseline" copy and "Topics without course material are not included." note. Keep loading, error, preparing, no-material and caught-up states.
- Acceptance: At desktop and mobile widths the purpose is visible without a separate start screen, timer or progress bar; heading and description use Skills' existing typography and fit the viewport; existing non-ready states and mastery-delta result remain available.
- Status: implemented
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs; synthetic screenshots at 1440px and 375px in docs/work/handover-2026/evidence/ui-overhaul.md.

### DIAG-REQ-002: Put answered count beside submission

- Rule: Diagnostic has no SessionBar back chevron or progress bar. Show "{answered} of {total} answered" beside the submit action. Submission remains disabled until all displayed questions are answered and while submission is pending. Preserve the tour anchors and the submitted-result exit.
- Rule: Question cards, answer count and submit button share one maximum-width column and responsive horizontal padding. Keep the footer's top border full width; its content aligns with the outer left/right card edges. Error copy follows the same column. The footer is present only while answering.
- Acceptance: Selecting an answer updates the adjacent count; the question view has no back chevron or progress bar; the enabled submit action sends the existing answer payload once all questions are answered.
- Status: implemented
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs; authenticated acceptance remains pending.

### DIAG-REQ-003: Keep the last question reachable above submission

- Rule: At desktop and 375px viewport widths, the complete last question and every choice can scroll into view above the submit region. Use a correctly sized scroll region with reserved bottom space, or place submission in normal flow. Do not alter shared ComposeDock behavior.
- Acceptance: At 1440px and 375px widths, scrolling reaches the last choice without clipping or overlap from submission, including a question with long text and wrapped choices.
- Status: implemented
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs; long-question screenshots at both widths in docs/work/handover-2026/evidence/ui-overhaul.md.

### DIAG-REQ-004: Keep one Diagnostic entry route

- Rule: `/course/diagnostic` remains the course Diagnostic route. Audit every Diagnostic link, route and redirect; remove or redirect any stale entry found. Preserve the existing diagnostic API and due logic.
- Acceptance: The sidebar, workspace card, due notice, instructor plan and tour steps target `/course/diagnostic`. Any stale alias discovered is covered by a redirect test. If none is found, record that result without inventing aliases.
- Status: implemented
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs and the route inventory in docs/work/handover-2026/evidence/ui-overhaul.md. No stale alias was found, so no redirect was introduced.

### DIAG-REQ-005: Preserve the Tutor and Study hub component boundary

- Rule: Use the component boundary below. Diagnostic is a baseline sitting, not an open Tutor conversation; this presentation change adds no chat persistence or file attachment behavior to it.
- Acceptance: Diagnostic submits through its existing API. Tutor attachment work does not enable attachments or persistence in the Study hub dock or alter ComposeDock behavior.
- Status: implemented
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs, apps/web/src/features/tutor/components/TutorChat.test.mjs and apps/web/src/features/flashcards/tests/study-deck.test.mjs; shared ComposeDock changes are limited to the directly authorized visual alignment; its action and ask behavior is unchanged.

| | Tutor | Study hub dock (lesson, study, test, review-missed) |
| --- | --- | --- |
| Purpose | Open conversations about the course | Help on the current card or question |
| Persistence | Saved conversations with rename, pin and delete | None; stateless and card-scoped |
| Files and images | Through existing conversation attachments, limited to backend-supported file types and sizes; no new image support | None |
| Dock | PromptInput; pill text-entry container when empty, token-radius rounded rectangle while dragging or holding attachments | ComposeDock; text only, pill text-entry container |
| Shared pieces | Message, MarkdownText, Shimmer thinking state, Suggestion / FollowUpChips, error display and de-identified `/tutor/ask` | Same |
| Not used | Reasoning, Tool, Agent, Plan, Task, Queue, Sandbox, Terminal, Model Selector, Speech, Artifact, Canvas, Web Preview | Same |
| Later, planned | Sources and Inline Citation after the API returns RAG source titles | n/a |

### DIAG-REQ-006: Keep answer selection visible during hover and keyboard use

- Rule: The shared AnswerableCard's selected choice retains its orange selection fill while hovered or focused; the neutral hover shade applies only to unselected, unanswered choices. Expose each button's selected state accessibly. Keep existing pending locks, graded-result presentation, choice-change and submission behavior across Diagnostic and Study hub callers.
- Acceptance: Clicking an answer while leaving the pointer over it does not wash out selection; moving away and returning keeps it selected; selecting another answer moves the selection without increasing the answered count. Keyboard selection exposes the same state. Existing Study/Practice grading and pending protections remain intact.
- Status: implemented
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs; shared Study regressions and synthetic desktop/mobile captures in the Lane U evidence.

### DIAG-REQ-007: Show one persistent completion view with mastery progression

- Rule: On successful submission, replace answering with a Test/Study-style results panel. Show “Diagnostic complete”, “Baseline set” and the returned mastery progression, animated once on entry with existing MasteryDelta rows/tracks. Celebrate once with Kala's existing confetti helper, gated by reduced motion. Never invent a score or mastery movement. Offer one primary “Back to workspace” and one secondary “View your twin” action within the panel. Remove the auto-opening completion dialog and answering footer entirely from results.
- Rule: Successful results take precedence over loading/empty/error question refetches for the mounted sitting. A later genuine visit reads the current backend state, including the caught-up view when nothing is due. Completion does not automatically navigate or restart the sitting. Handle empty mastery rows, long names, mobile widths and reduced motion without clipping or forced waiting before exit actions.
- Acceptance: Submission yields one results panel, no modal and exactly one action per destination. Mastery progression and confetti run once when motion is allowed and stay static/absent when reduced motion is requested. Both destinations work, no repeated submit occurs, a refetch cannot replace the results, and revisiting an empty diagnostic shows caught up.
- Status: implemented
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs; completion, navigation, refetch, mobile, confetti and reduced-motion evidence in docs/work/handover-2026/evidence/ui-overhaul.md.

### DIAG-REQ-008: Use the shared Spinner for actual waiting states across Kala

- Rule: Fred's app-wide visual correction uses the existing Spinner for real loading/submitting/mutating states: one per loading region or waiting label, and in place of action icons while that action is pending. Shared loading panels, skeleton regions, assistant waiting labels, Tutor save/pin/delete/preview, Diagnostic preparation/submission and notification loading use the same primitive. Keep existing indicators where already present. Preserve skeleton layouts, shimmer, request ownership, pending locks and timing; do not infer activity from arbitrary ellipses in placeholders, truncated text or menu icons. Do not add spinners to static empty/error states.
- Acceptance: Representative student/instructor loading regions and pending actions expose the spinner and an accessible waiting label; resolved content removes it; reduced motion leaves the same icon static. No request, auth, grading or navigation behavior changes solely for this visual pass.
- Status: implemented
- Verified by: source inventory and shared loading browser fixtures in apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs; Study/Tutor regressions and checks recorded in docs/work/handover-2026/evidence/ui-overhaul.md.

## Diagnostic availability (Lane G, APPROVAL-06)

### DIAG-REQ-009: Count only actionable unevidenced skills

- Rule: A baseline candidate is an approved skill with no learner evidence of any kind in the validated institution/course and at least one question servable now. Recorded Study/Practice activity, including item reviews, excludes the skill. No-material skills are not due. Availability reads never write evidence, grades, reviews or exposures.
- Acceptance: Mixed ready, no-material, preparing, exhausted and already-practiced skills produce only actionable candidates; empty and completed courses are not due. Tenant/course/learner boundaries are retained and no evidence is fabricated.
- Status: planned
- Verified by: Lane G's focused availability tests, pending implementation.

### DIAG-REQ-010: Filter by availability before the sitting limit

- Rule: Status and question selection use the same eligibility and availability rules. Filter before the ten-question limit, preserving deterministic skill order and one question per skill. An approved, live, untested bank MCQ is sufficient; do not require five. Exhausted pools await replenishment rather than imply failure. Preserve deterministic legacy selection and existing grading/evidence semantics.
- Acceptance: With unchanged source data the sitting has min(dueSkillCount, 10) questions, including when unavailable skills precede available skills. Cover more than ten candidates, one-MCQ availability and exhaustion without recording a false generation failure.
- Status: planned
- Verified by: Lane G's shared-selection and status parity tests, pending implementation.

### DIAG-REQ-011: Explain material and preparation waiting truthfully

- Rule: Status retains courseId and due, adding optional non-negative dueSkillCount and waitingForMaterialCount. due is true exactly when actionable count is positive. waitingForMaterialCount counts approved unevidenced skills missing course material; it excludes preparation and exhaustion.
- Rule: Question responses retain ready/generating/failed and existing fields, adding optional waitingForMaterialCount. pendingSkillIds means awaiting preparation or replenishment, not proof that a worker is active. failedSkillIds contains only actual recorded preparation failures; skippedSkillCount equals its length. No-material skills enter neither list. readyCount equals questions.length.
- Rule: Available questions take precedence (ready). With no questions, pending skills produce generating; otherwise recorded failures produce failed. Material-only waiting produces ready with empty questions and a positive waitingForMaterialCount; empty/all-evidenced courses produce ready, empty questions and zero. Clients missing optional fields keep legacy handling.
- Acceptance: Mixed availability remains playable, exhaustion is pending, no-material is distinct from failure, and empty/completed courses remain compatible. Status and question material counts agree for unchanged data. No migration, grading or evidence-semantic change.
- Status: planned
- Verified by: Lane G's response-contract tests, pending implementation.

## API contract

| Method and path | Purpose | Auth | Notes |
| --- | --- | --- | --- |
| GET /courses/{course_id}/diagnostic/status | Read whether a baseline is due | Validated course session | Optional actionable dueSkillCount and waitingForMaterialCount per DIAG-REQ-009–011 |
| GET /courses/{course_id}/diagnostic | Load baseline questions and preparation state | Validated course session | Availability before sitting limit; optional waitingForMaterialCount; existing status enum retained |
| POST /courses/{course_id}/diagnostic/submit | Submit the sitting and receive mastery deltas | Validated course session | Existing payload and grading unchanged |

## Data

No schema, RLS or persistence change. Existing server authorization and institution resolution remain authoritative. Server data remains in TanStack Query and answer selections remain local UI state.

## AI usage (if any)

No new model calls. Diagnostic generation and the provider path are outside this presentation scope.

## Edge cases and known limits

Preserve partial preparation, pending topics, no-material, failed generation, empty/caught-up states and the submitted-result guard against query invalidation. Preserve keyboard focus, visible focus indicators and reduced motion. The separate Study flip-card fix replaces hidden-face focus exposure with inert faces and deliberate focus handling; it must preserve rating and schedule behavior.

The two APPROVAL-05 visual exceptions are limited to text-entry containers and the Tutor new-chat logo. Fred's direct visual correction on 2026-10-25 additionally restores the existing shared rounded Tutor user-message bubbles, circular send button and shared follow-up controls; other controls retain the existing token rules. Tutor history is resizable on desktop (320px default, 280–440px bounds while preserving space for the content); its shell offset follows the current width. The New chat action is white and borderless at rest with a muted hover fill, and section headings stay visually quiet. The extra Tutor footer line is removed. These corrections do not change Diagnostic or shared ComposeDock behavior. Fred’s further feedback on 2026-10-25 requires a single shared dock styling source for pill radius, textarea line height and circular controls; a leading circular Tutor attachment control; an expanded token-radius container for attachments; equal bottom placement with Study; no horizontal rule below the Tutor title or above its dock; aligned history navigation; local Recents sorting; rounded, padded menus with a separator before destructive actions; and no new-chat starter suggestions. Post-answer follow-ups remain. Shared ComposeDock changes are visual only, preserving its mode, submission and state contracts. Fred’s next refinement makes the Recents sort trigger a plain sort icon, opens both history menus below the trigger toward the right with no animation (viewport collisions may constrain mobile placement), and centers the new-chat composer in the available canvas with its welcome above. The shared dock overlaps the scrolling content instead of adding a blank strip above it; final content and scroll controls retain clearance. Pinned precedes Recents and direct pin sits beside row actions when the list API supports management; unsupported live responses are recorded as an integration dependency. Fred’s finishing request removes the Tutor conversation title entirely, rounds and insets the sort focus ring to prevent clipping, keeps row actions visible while their menu is open, adds icons to sort choices, and uses the published per-icon lucide-animated variants for available Tutor action glyphs, driven from their whole control using Kala’s hover pattern. Do not apply a shared tilt, nudge or pulse preset. Glyphs without a published variant stay static. Overflowing history titles reveal their full text with one gentle hover marquee to the end and back; short titles and reduced-motion mode remain static. Both popup enter and exit remain immediate, including when action icons animate. The logo is static in Diagnostic, Study, Test and Tutor conversations. Lead designer review remains required in Lane U's report. Synthetic screenshots and browser checks are recorded in the Lane U evidence. Authenticated feature acceptance remains pending; opening the course workspace does not establish Diagnostic or Tutor acceptance.

## Tutor local attachment staging amendment — 2026-10-25

Fred selected local staging with file cards and a raw-text preview modal. Selection/drop validates .txt/.md/.pdf up to 5MB per file and stages locally without creating a conversation or uploading. Removing a staged file is local. Send uploads the staged batch through existing routes, then asks only when all files are ready; partial failure preserves the question and failed staged files, and retry does not re-upload successful files. Switching chats cancels the old composer’s continuation. Uploaded attachments remain conversation-scoped and use the existing removal API.

Cards show filename, type, size and explicit staged/uploading/attached/failure state inside the dock. Keep a finite corner radius derived from the existing radius token (twice radius-xl, matching the collapsed 48px pill) as the attachment area expands/collapses. Shared ComposeDock keeps the same empty appearance and behavior. No adjustable preview pane is introduced.

Local .txt/.md files open in a keyboard-accessible dialog showing bounded raw text, with no Markdown/HTML execution or formatting, a subtle blurred overlay and short entry/exit motion disabled under reduced motion. Previews use the local File only, never upload for preview, and are not persisted. All attachment cards support hover shade and click/keyboard activation. Files from older sessions and PDFs open the same dialog with metadata and an explicit content-preview limitation; do not invent or fetch unavailable contents. PDF remains accepted for upload; no PDF content preview. Images remain unsupported by the current API and are not enabled by this UI change.

Fred's follow-up requires equal top and left attachment insets, subtle token-based format accents with visible type labels, and the published lucide-animated Upload variant in the drop overlay. Play that glyph on drag entry, respecting reduced motion; no shared icon motion preset. The shared Sonner bug fix must respect Kala's forced theme over a saved preference and use readable semantic description text for badge, error and other notices. No gamification behavior changes.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-25 | Define Diagnostic presentation, scroll reachability, route audit and component boundary before implementation | APPROVAL-05 rev 2, Lane U | DIAG-REQ-001, DIAG-REQ-002, DIAG-REQ-003, DIAG-REQ-004, DIAG-REQ-005 |
| 2026-10-25 | Record the narrow pill exception: only ComposeDock/PromptInput text-entry containers may be pills when empty; Tutor uses an existing token radius while dragging or holding attachments; every control remains boxy | Fred's APPROVAL-05 clarification relayed by the coordinator; DESIGN.md exception must be committed before implementation | DIAG-REQ-005 |
| 2026-10-25 | Record the narrow motion exception: only Kala's logo in the Tutor new-chat empty state may have a slow subtle idle loop, stopping on typing or sending; never in conversations, Study, Test or Diagnostic; static with reduced motion | Fred's APPROVAL-05 clarification relayed by the coordinator; DESIGN.md exception must be committed before implementation; flag lead designer review | DIAG-REQ-005 |
| 2026-10-25 | Correct the shared component boundary to preserve rounded Tutor messages/send/follow-ups; remove the extra Tutor footer and define wider, adjustable history with a matching shell offset and quiet navigation styling | Fred's direct visual feedback in Lane U, superseding the earlier boxy chat-control interpretation; coordinator-owned Tutor/Design text requires matching integration amendment | DIAG-REQ-005 |
| 2026-10-25 | Define shared dock typography/radius alignment, leading circular attachment, seamless Tutor title/dock, local Recents sorting, padded rounded menus and removal of long new-chat starters before implementation | Fred’s direct follow-up; supersedes initial starter presentation in TUTOR-REQ-008; coordinator-owned Tutor/Design amendments pending integration | DIAG-REQ-005 |
| 2026-10-25 | Define immediate rightward history menus, plain sort control, centered new-chat composer and shared floating dock clearance before implementation | Fred’s latest direct feedback; shared visual changes authorized, API capability gate retained | DIAG-REQ-005 |
| 2026-10-25 | Define final Tutor focus/menu visibility, seamless title removal, overflow-title marquee and control-driven icon feedback before implementation | Fred’s finishing feedback; reduced motion and API capability gating retained | DIAG-REQ-005 |
| 2026-10-25 | Require published lucide-animated per-icon source variants, with shared event forwarding only and static fallback for unavailable glyphs | Fred’s explicit correction and https://lucide-animated.com/ registry inspection | DIAG-REQ-005 |
| 2026-10-25 | Define local file staging, retry-safe upload-before-send, finite dock corners and raw-text preview dialog before implementation | Fred selected file cards plus raw-text preview modal in this chat; coordinator-owned Tutor/Design integration amendment pending | DIAG-REQ-005 |
| 2026-10-25 | Define clickable attachment metadata fallback, equal card insets, format accents and published Upload drop glyph; restore shared toast contrast | Fred's direct attachment and notification feedback; existing backend type limits retained | DIAG-REQ-005 |
| 2026-10-25 | Restore a compact Skills-pattern purpose header with a separator, align submission with the question column, and preserve selected-answer styling on hover | Fred's direct Diagnostic UX feedback supersedes the earlier header-removal direction; no Diagnostic API or due-rule change | DIAG-REQ-001, DIAG-REQ-002, DIAG-REQ-003, DIAG-REQ-006 |
| 2026-10-25 | Align the introduction to the shell's left gutter, replace duplicate completion/modal exits with one celebrated mastery-results view, and unify real waiting indicators across Kala | Fred's direct follow-up explicitly expands visual write scope across the app; retain feature behavior and backend contracts | DIAG-REQ-001, DIAG-REQ-002, DIAG-REQ-007, DIAG-REQ-008 |
| 2026-10-25 | Match Diagnostic introduction margins to Skills/Twin content (24px/40px horizontal, 32px vertical and the shared maximum width), superseding breadcrumb alignment | Fred’s direct margin correction in WI-22 | DIAG-REQ-001 |
| 2026-10-25 | Clarify the singular skill-session versus plural Skills-picker layout boundary so all page headers share the centered maximum width on wide screens | Wide-screen verification of Fred’s margin correction | DIAG-REQ-001 |

| 2026-10-25 | Specify actionable eligibility, availability-first selection and truthful waiting contracts before Lane G implementation | APPROVAL-06 section 4; G proposal and coordinator contract clarification | DIAG-REQ-009–011 |
