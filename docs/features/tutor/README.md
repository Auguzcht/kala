---
feature: tutor
req_prefix: TUTOR
owner_role: OAICI
status: active
code:
  web: apps/web/src/features/tutor/
  api: services/api/app/routers/tutor.py
  worker: []
  db: []
tests: [services/api/tests/test_tutor.py, services/api/tests/test_request_budget.py, apps/web/src/features/tutor/components/TutorChat.test.mjs, apps/web/src/lib/api-error.test.ts, apps/web/src/features/tutor/schema/tutor.schema.test.ts]
---

# Tutor help and conversation management

## Purpose
Learners get course-grounded help and a usable retry message within the inline request budget. An answer remains usable even if saving its conversation fails.

## Actors and permissions
| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| authenticated learner | Ask for course-grounded help, using an owned conversation or stateless mode | Access another user's conversation |

## Requirements

### TUTOR-REQ-001: One 26-second budget per ask request
- Rule: Start one monotonic 26s budget at handler entry. Each outbound call uses min(current timeout, remaining minus 3s reserve), with a separate elapsed-time guard. Skip fallback below 6s remaining. Before an answer, deadline exhaustion returns 503 tutor_timeout with a plain retry message. After an answer, persistence failure or insufficient budget returns the answer and warns with stage and conversation ID prefix. Emit one privacy-safe tutor_timing line with stage milliseconds, mode, provider role, fallback use, and outcome.
- Acceptance: Slow mocked chat returns 503 within budget; late fallback is skipped; failed or slow persistence returns 200 with the answer. Frontend reads flat detail, detail plus optional/nullable code, and safely handles non-JSON errors. TutorChat shows the retry detail and preserves returned answers when persistence refetch fails or lacks them; saved responses retain the normal handoff.
- Status: implemented
- Verified by: services/api/tests/test_tutor.py, services/api/tests/test_request_budget.py, apps/web/src/features/tutor/components/TutorChat.test.mjs, apps/web/src/lib/api-error.test.ts, apps/web/src/features/tutor/schema/tutor.schema.test.ts

## Conversation management (Lane B)

### TUTOR-REQ-002: Rename an owned conversation
- Rule: PATCH /tutor/conversations/{conversation_id} accepts optional title, a string of 1–80 characters. Omitted fields remain unchanged. The mutation filters by conversation ID and the validated session's user ID and institution ID. Missing, malformed, other-user and cross-institution conversations return 404. An empty body, explicit null, invalid field type or unsupported field returns 422. Success returns the updated conversation. Rename changes title only and preserves pinned_at and updated_at.
- Acceptance: Owner rename persists and returns 200. Other-user and cross-institution requests return 404 without a write. Titles of 1 and 80 characters succeed; empty and over-80-character titles return 422. Empty and invalid bodies produce no write.
- Status: planned
- Verified by: services/api/tests/test_tutor_conversation_management.py (planned)

### TUTOR-REQ-003: Pin owned conversations and list pins first
- Rule: The same PATCH route accepts optional pinned: boolean. true sets pinned_at to the database's current transaction time; false clears it. Repeating true refreshes the pin time. Omitting pinned preserves its value. title and pinned may be updated together in one scoped mutation. Pinning preserves updated_at. GET /tutor/conversations retains its course, owner and institution filters and existing response fields, and adds pinnedAt to each conversation: a timestamp when pinned, otherwise null. Frontend consumers accept pinnedAt as optional and nullable for compatibility with older APIs. Order is pinned_at descending with nulls last, then updated_at descending.
- Acceptance: Pin and unpin persist and return the resulting pinnedAt. Unauthorized mutations return 404 without a write. Combined rename/pin succeeds atomically. Pinned conversations precede unpinned conversations; newer pins precede older pins; unpinned conversations retain updated_at descending order.
- Status: planned
- Verified by: services/api/tests/test_tutor_conversation_management.py (planned)

## Tutor presentation (Lane U)

### TUTOR-REQ-004: Responsive conversation sidebar

- Rule: At lg and larger widths, the Tutor chats sidebar is always open, with no collapse control or persisted collapsed state. Below lg, a header button opens chat history in the existing Sheet primitive. Selecting a conversation closes the mobile Sheet. Sidebar layout must reserve the correct content width.
- Acceptance: At 1440px the sidebar remains visible without a collapse control. At 375px it occupies no content width while closed; its header button opens an accessible Sheet, and selecting a conversation closes it and displays that conversation.
- Status: planned
- Verified by: planned sidebar interaction tests and manual screenshots at 1440px and 375px.

### TUTOR-REQ-005: Conversation groups and management controls

- Rule: Replace Today / Yesterday / Older with Collapsible groups named Pinned and Recents. Show Pinned only when at least one conversation is pinned. Preserve the API ordering within each group. Rows expose a pin button and a DropdownMenu on hover or keyboard focus. The menu contains Rename, Pin or Unpin, and Delete. Rename edits the title inline and uses Lane B's PATCH contract; pin and unpin use the same contract. Delete requires confirmation before calling the existing DELETE route. Cancelling confirmation sends no delete request. Deleting the active conversation returns to a new-chat view. Do not add Share, Archive or Move to project.
- Rule: Preserve optional and nullable pinnedAt in the frontend schema. Show pin and rename controls only when pinnedAt is present in the corresponding list-response row; null means supported but unpinned. Older responses that omit the property retain working conversation selection and confirmed deletion without PATCH controls.
- Acceptance: Pinned appears only with pinned rows; Recents contains unpinned rows. Both groups collapse and expand. Keyboard focus reveals row actions. Responses omitting pinnedAt show no pin or rename controls and cause no PATCH calls. Supported responses allow inline rename and pin/unpin. Delete sends no request before confirmation, sends none after cancellation, and clears the active conversation after successful confirmed deletion.
- Status: planned
- Verified by: planned sidebar grouping, keyboard-action, capability-gating, rename/pin and delete-confirmation tests.

### TUTOR-REQ-006: Center the empty-chat composer and select a local greeting

- Rule: An empty conversation shows a greeting above a vertically centered composer. After the first message, use the bottom composer layout. Choose greetings from client-side morning, afternoon, evening and late-night pools, including course-aware variants when course information is available. Choose deterministically for the day and course within the applicable time-of-day pool, and keep the selected greeting stable across ordinary re-renders. Do not include the student's name or make a model call for greetings.
- Acceptance: Empty-chat screenshots show the centered greeting and composer at both viewport widths. Sending the first message moves the composer to the bottom. Repeated renders with the same date, course and time-of-day inputs produce the same greeting; representative times select the appropriate pool. Missing course information uses a generic greeting.
- Status: planned
- Verified by: planned greeting-selection and empty-to-conversation tests, plus manual screenshots.

### TUTOR-REQ-007: Limit the mascot idle loop to the new-chat empty state

- Rule: Only Kala's own logo mark in the Tutor new-chat empty state may show a slow, subtle SVG or CSS idle loop. Stop it when typing starts or a message is sent. It is absent mid-conversation and from Study, Test and Diagnostic. Use existing tokens and render a static mark under prefers-reduced-motion. A supplied lead-designer animation asset replaces this implementation.
- Acceptance: A fresh empty chat can show the subtle idle loop; typing or sending stops it. Conversation views do not show the animated empty-state mark. Reduced-motion users receive a static mark.
- Status: planned
- Verified by: planned mascot-state tests and manual normal/reduced-motion checks.

### TUTOR-REQ-008: Offer course-skill starter suggestions

- Rule: Below the empty-chat composer, show three or four Suggestion controls built from available course skills using local templates such as "Explain {skill}" and "Quiz me on {skill}". Suggestions use the existing grounded Tutor ask path. Do not generate suggestions with a model or invent skill names when skills are unavailable.
- Acceptance: A course with skills shows three or four relevant template suggestions; selecting one starts the corresponding grounded conversation turn. A course without loaded skills shows no invented course-skill suggestions. Greeting and suggestion selection cause no model calls.
- Status: planned
- Verified by: planned starter-generation and selection tests.

### TUTOR-REQ-009: Reuse PromptInput for Tutor files and composer shape

- Rule: Tutor uses PromptInput with its existing drag-and-drop handling. Dragging files anywhere over the Tutor view shows "Drop files to attach". The text-entry container is a pill when empty of attachments; while dragging or holding attachments it becomes a rounded rectangle using an existing radius token. Attachment chips appear inside the container above the text field. Animate the shape change only when reduced motion is not requested.
- Rule: The first attachment in a new chat creates the conversation lazily, then uploads through the existing conversation attachment route. Coordinate overlapping attachment and send operations so they reuse the same created conversation. Respect the backend's .txt, .md and .pdf support and 5MB limit, and display its safe error detail. Attachment failure must not report a successful upload.
- Rule: This shape exception applies only to ComposeDock/PromptInput text-entry containers. Buttons, including send buttons, chips, cards, inputs and all other controls remain boxy and use existing tokens. Shared primitive changes are opt-in and preserve other callers. ComposeDock behavior is unchanged.
- Acceptance: Drag-over displays the overlay and rounded-rectangle container; leaving clears the drag state. Uploaded attachments remain inside the container above the field. A new-chat attachment creates one conversation before upload. Unsupported/oversized files show an error. Reduced-motion users get an immediate shape change. Other PromptInput callers retain their existing behavior.
- Status: planned
- Verified by: planned dock-state, drag/drop, upload-error and lazy-creation tests, plus screenshots at both widths.

### TUTOR-REQ-010: Show an honest waiting state and retain deadline recovery

- Rule: While waiting for an answer, show the existing Shimmer with "Thinking", changing after about eight seconds to "Still working on it". Reset the timer for each ask and clean it up on completion, failure or conversation change. Do not show invented step traces or a Reasoning component. On tutor_timeout, show the server's safe retry message. Preserve TUTOR-REQ-001's returned-answer and persistence-recovery behavior.
- Acceptance: Controlled time shows Thinking initially and Still working on it after approximately eight seconds; completion/failure stops the waiting state. Retrying starts a fresh timer. Timeout detail remains visible with Retry, and existing saved/unsaved-answer recovery tests continue to pass.
- Status: planned
- Verified by: planned waiting-state timer tests and existing TUTOR-REQ-001 frontend regressions.

### TUTOR-REQ-011: Preserve the Tutor and Study hub component boundary

- Rule: Apply the boundary below without introducing additional AI Elements or changing ComposeDock behavior.

| | Tutor | Study hub dock (lesson, study, test, review-missed) |
| --- | --- | --- |
| Purpose | Open conversations about the course | Help on the current card or question |
| Persistence | Saved conversations with rename, pin and delete | None; stateless and card-scoped |
| Files and images | Through existing conversation attachments and backend type/size limits; no new image support | None |
| Dock | PromptInput; pill text-entry container when empty, token-radius rounded rectangle while dragging or holding attachments | ComposeDock; text only, pill text-entry container |
| Shared pieces | Message, MarkdownText, Shimmer thinking state, Suggestion / FollowUpChips, error display and de-identified /tutor/ask | Same |
| Not used | Reasoning, Tool, Agent, Plan, Task, Queue, Sandbox, Terminal, Model Selector, Speech, Artifact, Canvas, Web Preview | Same |
| Later, planned | Sources and Inline Citation after the API returns RAG source titles | n/a |

- Acceptance: Tutor uses conversation attachments; Study hub asks remain stateless and text-only. No prohibited component is introduced. Sources and Inline Citation remain planned.
- Status: planned
- Verified by: planned component-boundary review and existing Tutor/Study regressions.

## API contract
| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| POST /tutor/ask | Course-grounded help | validated current user; owned conversation when supplied | 503 {detail: string, code: tutor_timeout}; successful answer contract unchanged |
| PATCH /tutor/conversations/{conversation_id} | Rename, pin or unpin an owned conversation | validated current user and institution | Body {title?: string 1..80, pinned?: boolean}; at least one field required; 200 updated conversation including nullable pinnedAt; 404 unavailable conversation; 422 invalid body |
| GET /tutor/conversations?course_id={course_id} | List owned course conversations | validated current user and institution | Existing conversations envelope and fields retained; adds nullable pinnedAt; order pinned_at.desc.nullslast,updated_at.desc |

## Data
Reads course-scoped RAG and owned tutor conversations/messages/attachments. Service-role writes preserve original user question and answer; sanitization affects model-bound copies only. Planned migration 0037_tutor_conversation_pin.sql adds nullable pinned_at timestamptz to tutor_conversations without a default or backfill. Existing RLS policies and grants remain unchanged. Conversation-management mutations explicitly filter by conversation ID, validated session user ID and institution ID because the API service role bypasses RLS. Existing create/detail response contracts remain unchanged; the pin projection is added to list and PATCH only.

## AI usage (if any)
Tutor selects the existing chat role and its fallback. Embedding, prompt, context, and prior messages pass the existing sanitizer before reaching a provider. Timeout settings are opt-in; other callers keep their existing defaults.

## Edge cases and known limits
TutorChat retains an unconfirmed answer locally when its refetch fails or lacks the returned turn, and removes the duplicate display if that turn later arrives from storage. This local copy lasts only while the conversation remains open and does not retry saving automatically. The budget begins after authentication, at handler entry. It reserves 3s for response work. Synchronous provider operations may continue in a worker after the handler stops waiting; they cannot start later tutor stages. On Lambda, an abandoned synchronous call can resume when the warm execution environment serves the next request; returning a response does not terminate that call or guarantee cancellation of its remote side effects. An in-flight persistence write can commit after timeout, so persistence completion is uncertain. No live Lambda/Blackboard recovery claim.

## Change log
| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-24 | Minimal freeze spec created before implementation | APPROVAL-01, section 2 Lane T and confirmed amendment A1 | TUTOR-REQ-001 |
| 2026-10-24 | Complete timeout detail and unconfirmed-answer display in TutorChat | APPROVAL-01 standing rule; coordinating planner grant for TutorChat.tsx and dedicated UI tests | TUTOR-REQ-001 |
| 2026-10-24 | Explicitly document that an abandoned synchronous call can resume during the next request in a warm Lambda environment | APPROVAL-02 from Fred | TUTOR-REQ-001 |
| 2026-10-25 | Define owner-scoped conversation rename and pin, additive pinnedAt responses and pinned-first listing | APPROVAL-05 rev 2, section 2 and confirmed coordinator amendments | TUTOR-REQ-002, TUTOR-REQ-003 |
| 2026-10-25 | Define responsive conversation management, centered empty chat, local greetings and starters, PromptInput attachments, waiting state and component boundary before implementation | APPROVAL-05 rev 2, Lane U and confirmed coordinator amendments | TUTOR-REQ-004–011 |
| 2026-10-25 | Permit pills only for ComposeDock/PromptInput text-entry containers; Tutor uses an existing token radius while dragging or holding attachments; every control remains boxy | Approved APPROVAL-05, 2026-10-25; DESIGN.md scoped chat-entry exception; lead designer review remains a handover follow-up | TUTOR-REQ-009, TUTOR-REQ-011 |
| 2026-10-25 | Permit a slow subtle idle loop only for Kala's logo in Tutor's new-chat empty state; stop on typing or sending, use a static reduced-motion mark, and exclude conversations, Study, Test and Diagnostic | Approved APPROVAL-05, 2026-10-25; DESIGN.md scoped mascot exception; lead designer review remains a handover follow-up | TUTOR-REQ-007 |
