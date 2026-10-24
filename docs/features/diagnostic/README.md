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

### DIAG-REQ-001: Remove redundant Diagnostic introduction

- Rule: The Diagnostic page omits the "Build your baseline" page header and subtitle, and the "Topics without course material are not included." note. Keep loading, error, preparing, no-material, caught-up and submitted-result states.
- Acceptance: Neither removed introduction nor note appears in a ready question set; existing non-ready states and the mastery-delta result remain available.
- Status: implemented
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs; synthetic screenshots at 1440px and 375px in docs/work/handover-2026/evidence/ui-overhaul.md.

### DIAG-REQ-002: Put answered count beside submission

- Rule: Diagnostic has no SessionBar back chevron or progress bar. Show "{answered} of {total} answered" beside the submit action. Submission remains disabled until all displayed questions are answered and while submission is pending. Preserve the tour anchors and the submitted-result exit.
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
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs, apps/web/src/features/tutor/components/TutorChat.test.mjs and apps/web/src/features/flashcards/tests/study-deck.test.mjs; source review confirms ComposeDock is unchanged.

| | Tutor | Study hub dock (lesson, study, test, review-missed) |
| --- | --- | --- |
| Purpose | Open conversations about the course | Help on the current card or question |
| Persistence | Saved conversations with rename, pin and delete | None; stateless and card-scoped |
| Files and images | Through existing conversation attachments, limited to backend-supported file types and sizes; no new image support | None |
| Dock | PromptInput; pill text-entry container when empty, token-radius rounded rectangle while dragging or holding attachments | ComposeDock; text only, pill text-entry container |
| Shared pieces | Message, MarkdownText, Shimmer thinking state, Suggestion / FollowUpChips, error display and de-identified `/tutor/ask` | Same |
| Not used | Reasoning, Tool, Agent, Plan, Task, Queue, Sandbox, Terminal, Model Selector, Speech, Artifact, Canvas, Web Preview | Same |
| Later, planned | Sources and Inline Citation after the API returns RAG source titles | n/a |

## API contract

| Method and path | Purpose | Auth | Notes |
| --- | --- | --- | --- |
| GET /courses/{course_id}/diagnostic/status | Read whether a baseline is due | Validated course session | No due-rule change |
| GET /courses/{course_id}/diagnostic | Load baseline questions and preparation state | Validated course session | No selection or generation change |
| POST /courses/{course_id}/diagnostic/submit | Submit the sitting and receive mastery deltas | Validated course session | Existing payload and grading unchanged |

## Data

No schema, RLS or persistence change. Existing server authorization and institution resolution remain authoritative. Server data remains in TanStack Query and answer selections remain local UI state.

## AI usage (if any)

No new model calls. Diagnostic generation and the provider path are outside this presentation scope.

## Edge cases and known limits

Preserve partial preparation, pending topics, no-material, failed generation, empty/caught-up states and the submitted-result guard against query invalidation. Preserve keyboard focus, visible focus indicators and reduced motion. The separate Study flip-card fix replaces hidden-face focus exposure with inert faces and deliberate focus handling; it must preserve rating and schedule behavior.

The two APPROVAL-05 visual exceptions are limited to text-entry containers and the Tutor new-chat logo. Fred's direct visual correction on 2026-10-25 additionally restores the existing shared rounded Tutor user-message bubbles, circular send button and shared follow-up controls; other controls retain the existing token rules. Tutor history is resizable on desktop (320px default, 280–440px bounds while preserving space for the content); its shell offset follows the current width. The New chat action is white and borderless at rest with a muted hover fill, and section headings stay visually quiet. The extra Tutor footer line is removed. These Tutor-only corrections do not change Diagnostic or shared ComposeDock behavior. The logo is static in Diagnostic, Study, Test and Tutor conversations. Lead designer review remains required in Lane U's report. Synthetic screenshots and browser checks are recorded in the Lane U evidence. Authenticated feature acceptance remains pending; opening the course workspace does not establish Diagnostic or Tutor acceptance.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-25 | Define Diagnostic presentation, scroll reachability, route audit and component boundary before implementation | APPROVAL-05 rev 2, Lane U | DIAG-REQ-001, DIAG-REQ-002, DIAG-REQ-003, DIAG-REQ-004, DIAG-REQ-005 |
| 2026-10-25 | Record the narrow pill exception: only ComposeDock/PromptInput text-entry containers may be pills when empty; Tutor uses an existing token radius while dragging or holding attachments; every control remains boxy | Fred's APPROVAL-05 clarification relayed by the coordinator; DESIGN.md exception must be committed before implementation | DIAG-REQ-005 |
| 2026-10-25 | Record the narrow motion exception: only Kala's logo in the Tutor new-chat empty state may have a slow subtle idle loop, stopping on typing or sending; never in conversations, Study, Test or Diagnostic; static with reduced motion | Fred's APPROVAL-05 clarification relayed by the coordinator; DESIGN.md exception must be committed before implementation; flag lead designer review | DIAG-REQ-005 |
| 2026-10-25 | Correct the shared component boundary to preserve rounded Tutor messages/send/follow-ups; remove the extra Tutor footer and define wider, adjustable history with a matching shell offset and quiet navigation styling | Fred's direct visual feedback in Lane U, superseding the earlier boxy chat-control interpretation; coordinator-owned Tutor/Design text requires matching integration amendment | DIAG-REQ-005 |
