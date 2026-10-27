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

## Student read admission

Conversation-list and conversation-detail GETs follow [AUTH-REQ-007](../lti-auth/README.md#auth-req-007-require-existing-course-enrollment-on-student-reads). Detail resolves the existing owned conversation before checking its course, then loads messages/attachments. Ask, create, management and attachment mutations are unchanged by this read-route amendment. Admission is implemented locally and verified by the 116-case AUTH-REQ-007 route/import matrix and strict AST scope proof; hosted deployment and live acceptance remain pending.

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
- Status: implemented
- Verified by: services/api/tests/test_tutor_conversation_management.py

### TUTOR-REQ-003: Pin owned conversations and list pins first
- Rule: The same PATCH route accepts optional pinned: boolean. true sets pinned_at to the database's current transaction time; false clears it. Repeating true refreshes the pin time. Omitting pinned preserves its value. title and pinned may be updated together in one scoped mutation. Pinning preserves updated_at. GET /tutor/conversations retains its course, owner and institution filters and existing response fields, and adds pinnedAt to each conversation: a timestamp when pinned, otherwise null. Frontend consumers accept pinnedAt as optional and nullable for compatibility with older APIs. Order is pinned_at descending with nulls last, then updated_at descending.
- Acceptance: Pin and unpin persist and return the resulting pinnedAt. Unauthorized mutations return 404 without a write. Combined rename/pin succeeds atomically. Pinned conversations precede unpinned conversations; newer pins precede older pins; unpinned conversations retain updated_at descending order.
- Status: implemented
- Verified by: services/api/tests/test_tutor_conversation_management.py

## Tutor presentation (Lane U)

### TUTOR-REQ-004: Responsive conversation sidebar

- Rule: At lg and larger widths, the Tutor chats sidebar is always open, with no collapse control or persisted collapsed state. Below lg, a header button opens chat history in the existing Sheet primitive. Selecting a conversation closes the mobile Sheet. Desktop history defaults to 320px, resizes by pointer or keyboard within 280–440px, and updates the content offset. Width is local presentation state. There is no duplicate conversation-title header.
- Acceptance: At 1440px the sidebar remains visible without a collapse control. At 375px it occupies no content width while closed; its header button opens an accessible Sheet, and selecting a conversation closes it and displays that conversation.
- Status: implemented
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs; apps/web/src/features/tutor/tests/presentation.test.mjs; existing TutorChat regressions. Synthetic viewport/reduced-motion coverage is recorded in the accepted handoff; live acceptance is FG-5.

### TUTOR-REQ-005: Conversation groups and management controls

- Rule: Replace Today / Yesterday / Older with Collapsible groups named Pinned and Recents. Show Pinned only when at least one conversation is pinned. Preserve pinned order; Recents has local newest/oldest/title sorting. Rows expose a pin button and a DropdownMenu on hover or keyboard focus; actions remain visible while the menu is open. Menus open toward the right on desktop, respect viewport collisions on mobile, and enter and exit immediately. Long overflowing titles reveal their text with one gentle hover movement to the end and back; short titles and reduced-motion titles remain static. The menu contains Rename, Pin or Unpin, and Delete. Rename opens the existing Dialog primitive and uses TUTOR-REQ-002's existing PATCH contract; pin and unpin use the same contract. Delete requires confirmation before calling the existing DELETE route. Cancelling confirmation sends no delete request. Deleting the active conversation returns to a new-chat view. Do not add Share, Archive or Move to project.
- Rule: Preserve optional and nullable pinnedAt in the frontend schema. Show pin and rename controls only when pinnedAt is present in the corresponding list-response row; null means supported but unpinned. Older responses that omit the property retain working conversation selection and confirmed deletion without PATCH controls.
- Acceptance: Pinned appears only with pinned rows; Recents contains unpinned rows. Both groups collapse and expand. Keyboard focus reveals row actions. Responses omitting pinnedAt show no pin or rename controls and cause no PATCH calls. Supported responses allow dialog rename and pin/unpin under TUTOR-REQ-012. Delete sends no request before confirmation, sends none after cancellation, and clears the active conversation after successful confirmed deletion.
- Status: implemented locally; deployed acceptance remains pending
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs and presentation.test.mjs; dialog/pin/delete/capability and retained TutorChat regressions. Synthetic checks do not establish live FG-9.

### TUTOR-REQ-006: Center the empty-chat composer and select a local greeting

- Rule: An empty conversation shows a greeting above a vertically centered composer. After the first message, use a floating bottom composer with sufficient final-message and scroll-control clearance. Choose greetings from client-side morning, afternoon, evening and late-night pools, including course-aware variants when course information is available. Choose deterministically for the day and course within the applicable time-of-day pool, and keep the selected greeting stable across ordinary re-renders. Do not include the student's name or make a model call for greetings.
- Acceptance: Empty-chat screenshots show the centered greeting and composer at both viewport widths. Sending the first message moves the composer to the bottom. Repeated renders with the same date, course and time-of-day inputs produce the same greeting; representative times select the appropriate pool. Missing course information uses a generic greeting.
- Status: implemented
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs; apps/web/src/features/tutor/tests/presentation.test.mjs; existing TutorChat regressions. Synthetic viewport/reduced-motion coverage is recorded in the accepted handoff; live acceptance is FG-5.

### TUTOR-REQ-007: Limit the mascot idle loop to the new-chat empty state

- Rule: Only Kala's own logo mark in the Tutor new-chat empty state may show a slow, subtle SVG or CSS idle loop. Stop it when typing starts or a message is sent. It is absent mid-conversation and from Study, Test and Diagnostic. Use existing tokens and render a static mark under prefers-reduced-motion. A supplied lead-designer animation asset replaces this implementation.
- Acceptance: A fresh empty chat can show the subtle idle loop; typing or sending stops it. Conversation views do not show the animated empty-state mark. Reduced-motion users receive a static mark.
- Status: implemented
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs; apps/web/src/features/tutor/tests/presentation.test.mjs; existing TutorChat regressions. Synthetic viewport/reduced-motion coverage is recorded in the accepted handoff; live acceptance is FG-5.

### TUTOR-REQ-008: Course-skill starter suggestions (retired)

- Status: retired
- Reason: Fred removed the new-chat starter suggestions during the accepted Lane U handoff. Keep this ID for traceability; do not reintroduce starters. Post-answer follow-ups remain available. APPROVAL-06 section 2 reconciles this accepted change.
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs.

### TUTOR-REQ-009: Stage Tutor files locally until Send

- Rule: Tutor uses PromptInput and its drag/drop handling. Dragging files over the view shows “Drop files to attach”. File cards sit above the field with filename, type, size and explicit staged/uploading/attached/failure state. The shared dock uses finite corners derived from twice radius-xl: a pill at its collapsed 48px height and a rounded rectangle as content expands. Circular attachment/send controls, message bubbles and follow-ups follow the scoped DESIGN.md amendment; other controls retain their existing rules.
- Rule: Selecting/dropping validates TXT/MD/PDF up to 5 MiB per file and stages native File objects in React memory only. It does not create a conversation or upload. Send creates a conversation lazily if necessary, uploads the batch, then asks only when all files are ready. Overlapping operations reuse one conversation. Partial failure retains the question and failed files; retry reuses successful uploads. Switching chats cancels the old composer's continuation. Removing a staged file is local; uploaded-file removal uses the existing owned conversation route.
- Rule: Cards open an accessible preview dialog. Local TXT/MD previews show bounded raw text up to 128 KiB, never execute/render Markdown or HTML and never upload for preview. PDFs and restored files show metadata plus an explicit unavailable-content limitation. No images or new content-retrieval API. Unsent files/previews are lost on refresh/remount, never persisted in browser storage.
- Rule: Preview entry/exit and drag-entry Upload feedback respect reduced motion. Shared ComposeDock visual alignment is authorized; its text-only, stateless behavior is unchanged.
- Acceptance: Selection causes no network mutation; Send uploads once before asking. Partial retries do not re-upload successful files; switching chats prevents stale continuation. Unsupported/oversized files show safe errors. Raw preview is bounded and inert, metadata fallback truthful, keyboard removal/preview and reduced motion work at 375px and 1440px.
- Status: implemented
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs; apps/web/src/features/tutor/tests/presentation.test.mjs; accepted handoff and coordinator first-integration evidence. Live acceptance remains FG-5.

### TUTOR-REQ-010: Show an honest waiting state and retain deadline recovery

- Rule: While waiting for an answer, show exactly one existing Shimmer line with "Thinking", changing after about eight seconds to "Still working on it". Follow DESIGN.md: no spinner beside the line or in the message body; disable the initiating control with a stable label/icon, never a second Thinking indicator. Non-model submit actions may show a spinner only inside the activated, disabled control while its request is pending. Reset the timer for each ask and clean it up on completion, failure or conversation change. Do not show invented step traces or a Reasoning component. On tutor_timeout, show the server's safe retry message. Preserve TUTOR-REQ-001's returned-answer and persistence-recovery behavior.
- Acceptance: Controlled time shows Thinking initially and Still working on it after approximately eight seconds; completion/failure stops the waiting state. Retrying starts a fresh timer. Timeout detail remains visible with Retry, and existing saved/unsaved-answer recovery tests continue to pass.
- Status: implemented locally; deployed acceptance remains pending
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs covers one shimmer, eight-second timer, disabled stable Send, reset and timeout/recovery. Synthetic viewport/reduced-motion checks pass; live FG-9 remains pending.

### TUTOR-REQ-011: Preserve the Tutor and Study hub component boundary

- Rule: Apply the boundary below. Shared dock visual geometry is aligned; ComposeDock behavior stays stateless and text-only. No additional prohibited AI Elements are introduced.

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
- Status: implemented
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs; apps/web/src/features/tutor/tests/presentation.test.mjs; existing TutorChat regressions. Synthetic viewport/reduced-motion coverage is recorded in the accepted handoff; live acceptance is FG-5.

### TUTOR-REQ-012: Rename through an accessible dialog
- Rule: Replace inline editing with the existing Dialog primitive. Title “Rename chat”, helper “Keep it short and recognizable”, input prefilled with the current title and selected on opening. Provide Cancel and Save. Trim the input; Save is disabled for blank or unchanged titles and during the existing PATCH. Enter saves only when valid; Esc cancels. Cancel/Esc makes no request. Return focus to the originating “...” trigger after close, retaining capability gating, ownership, title-length validation and safe failure feedback. A pending Save spinner appears only inside Save.
- Acceptance: Pointer/keyboard opening, selected input, blank/unchanged/trimmed input, Enter exactly once, Escape/Cancel no PATCH, pending lock, success/error and focus return at 375px/1440px. Pin/delete/list compatibility and existing API authorization remain intact.
- Status: implemented locally; deployed acceptance remains pending
- Verified by: apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs covers dialog selection, trim, Enter/Escape, one PATCH, pending/error locks and focus return at375px/1440px. Live FG-9 remains pending.

### TUTOR-REQ-013: Answer small talk briefly without a study roadmap
- Rule: The existing Tutor system prompt tells the model that greetings or messages with no course question receive a short, friendly reply and an offer to help. No roadmap or “course context” wording for that exchange. This is prompt-only: no classifier/model call, model/provider/config/routing change, bypass of grounding or graded-answer protections for actual questions, or evidence/persistence change.
- Acceptance: A mocked-provider test proves the small-talk rule reaches the existing system prompt alongside retained teaching/safety instructions. A real “Hello!” response remains FG-9; local prompt inspection cannot claim model behavior or latency.
- Status: implemented locally; live model behavior remains pending
- Verified by: services/api/tests/test_tutor_small_talk_approval08.py:2 mocked-provider tests; full API1016 and enrollment116 pass. E1 proves only the module-level prompt literal changed. Fred's Hello! observation remains FG-9.

### TUTOR-REQ-014: Defer image attachments until privacy controls are reviewed
- Rule: Image attachment support is planned only. The current sanitizer operates on text and does not de-identify image contents; enabling images presents a PDPA/privacy risk. Continue current TXT/MD/PDF staging, type/size validation and text-based handling. Do not enable image MIME types, previews, uploads, OCR or multimodal provider inputs in this round.
- Acceptance: Existing image rejection remains unchanged. Any later implementation requires a separately approved privacy/sanitization contract and scope.
- Status: planned
- Verified by: existing attachment rejection tests; no image implementation is authorized by APPROVAL-08.

### TUTOR-REQ-015: Edit only the most recent sent prompt after feasibility approval
- Rule: The approved target is the latest user prompt only. Older user messages have no edit control. A pencil appears on hover/focus under that last user message; editing is inline, with Cancel and Send. Esc cancels. Send is disabled for blank or unchanged text. Saving replaces the last exchange (old user prompt and Kala reply), then sends the edited prompt; no older history, evidence or mastery changes.
- Gate: First investigate schema/dependencies, ownership, course/enrollment admission, message ordering, attachments, in-flight asks and failure/transaction behavior. Build only if no migration is needed, evidence/mastery tables are untouched, and last-exchange deletion is owner/institution/course-scoped and respects AUTH-REQ-007 admission. Submit the concrete route contract/feasibility to the coordinator for a spec-first amendment before coding it. The new route must be a new function only; pre-existing functions, imports, guards and signatures stay unchanged, except E1's single system-prompt literal. If those constraints cannot hold, do not build it; mark this requirement planned/deferred to ITO with the exact reason.
- Acceptance if built: Only the last user message offers editing; pointer/keyboard, Cancel/Esc, blank/unchanged text and single pending Send work at 375px/1440px. Correct owner/enrolled course succeeds; other owner, course/institution, non-enrolled student, stale last exchange and denied requests do not remove messages or send a replacement. Older turns, attachments and protected writes remain intact. Specify failure/retry behavior before implementation, rather than silently losing or duplicating a turn.
- Status: planned, deferred to ITO after APPROVAL-08 T2 feasibility review. No implementation is authorized under the current no-migration/new-function-only boundary. Safe concurrent replacement and recoverable/idempotent retry require coordination with existing ask writers and a durable transaction/revision contract that does not currently exist. Equal message timestamps and best-effort/possibly late persistence prevent a new route from safely identifying and replacing the latest exchange across tabs/invocations. Evidence/mastery dependencies are not the blocker.
- Verified by: source audit of tutor_messages in immutable0010, _ask history/persistence, separate PostgREST operations and frontend returned-answer recovery. No endpoint, edit control, migration or destructive test was added; implementation/acceptance remains planned.

### TUTOR-REQ-016: Inspect latency without changing runtime settings
- Rule: FG-L is delegated by Fred, read-only, solely for T2-5. Use only AWS sts get-caller-identity (print Account only), logs describe-log-groups with prefix /aws/lambda/, logs start-query, logs get-query-results and logs filter-log-events. Discover the API group; ambiguous candidates stop. Query only the last 48 hours, descending tutor_timing/provider lines, limit50. Parse in memory; no raw output or files.
- Rule: Report stage median/max for retrieval/embedding, primary, fallback and total, fallback-request count and primary429/other errors by model/status. Distinguish insufficient timing coverage/correlation from measured absence. Recommend keep settings, a Fred-gated primary/fallback swap, or streaming as an ITO follow-up; never apply one. Missing/expired credentials, need for another AWS command, or a body/personal-data field stops this step; report only the offending field name for a privacy finding.
- Acceptance: Output/evidence contains only aggregate numbers, stage/model/status names; account ID is the sole identity output allowed. Raw data is local only, not retained. No raw log lines, user/institution identifiers, bodies, emails, tokens, secrets or provider/config changes. This delegate does not release other Fred gates.
- Status: blocked after delegated read-only FG-L stopped on actual field user_id_prefix; raw data is local only, not retained.
- Verified by: T2 executed the allowed discovery/query and stopped before aggregation under Fred's privacy condition. Metrics and primary/fallback attribution are unavailable, not zero; configuration stays unchanged. WI-31 plans the separate diagnostics follow-up. No raw values retained.

### TUTOR-REQ-019: Never use a material person's name to address the student
- Rule: The Tutor system prompt says never address the student by name. Any names in course material refer to people in that material, not the student. Keep normal discussion of named people in curriculum possible without turning those names into the learner's identity. This is a system-prompt-only instruction, not a new sanitizer, identity lookup, classifier or provider/configuration change.
- Acceptance: The existing mocked-provider small-talk tests assert both instructions reach the actual provider-bound system prompt for default/detail styles, alongside all retained teaching/safety rules. Whole-module AST proof permits only the one _SYSTEM string literal; all19 existing enrollment-guarded functions remain identical. Full API suite and the116-case enrollment matrix pass. Live model behavior remains Fred's deploy/FG-9 check; a mocked assertion does not establish compliance.
- Status: planned; specified before implementation under APPROVAL-09 Amendment1.
- Verified by: pending prompt-only implementation, extended test_tutor_small_talk_approval08.py, AST proof and full API/enrollment checks.

## API contract
| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| POST /tutor/ask | Course-grounded help | validated current user; owned conversation when supplied | 503 {detail: string, code: tutor_timeout}; successful answer contract unchanged |
| PATCH /tutor/conversations/{conversation_id} | Rename, pin or unpin an owned conversation | validated current user and institution | Body {title?: string 1..80, pinned?: boolean}; at least one field required; 200 updated conversation including nullable pinnedAt; 404 unavailable conversation; 422 invalid body |
| GET /tutor/conversations?course_id={course_id} | List owned course conversations | validated current user and institution | Existing conversations envelope and fields retained; adds nullable pinnedAt; order pinned_at.desc.nullslast,updated_at.desc |

## Data
Reads course-scoped RAG and owned tutor conversations/messages/attachments. Service-role writes preserve original user question and answer; sanitization affects model-bound copies only. Locally validated migration 0037_tutor_conversation_pin.sql adds nullable pinned_at timestamptz to tutor_conversations without a default or backfill. Existing RLS policies and grants remain unchanged. Conversation-management mutations explicitly filter by conversation ID, validated session user ID and institution ID because the API service role bypasses RLS. Fred applies 0037 at FG-3 before deployment; local implementation does not establish hosted availability. Existing create/detail response contracts remain unchanged; the pin projection is added to list and PATCH only.

## AI usage (if any)
Tutor selects the existing chat role and its fallback. Embedding, prompt, context, and prior messages pass the existing sanitizer before reaching a provider. Timeout settings are opt-in; other callers keep their existing defaults.

## Edge cases and known limits
TutorChat retains an unconfirmed answer locally when its refetch fails or lacks the returned turn, and removes the duplicate display if that turn later arrives from storage. This local copy lasts only while the conversation remains open and does not retry saving automatically. The budget begins after authentication, at handler entry. It reserves 3s for response work. Synchronous provider operations may continue in a worker after the handler stops waiting; they cannot start later tutor stages. On Lambda, an abandoned synchronous call can resume when the warm execution environment serves the next request; returning a response does not terminate that call or guarantee cancellation of its remote side effects. An in-flight persistence write can commit after timeout, so persistence completion is uncertain. No live Lambda/Blackboard recovery claim.

## APPROVAL-07 local verification boundary

At integrated source `8e51040f1dda4235f9b12ad344da4cd81442e1e9`, reviewed staff guards, H history/error states, M repair tooling and student-read admission are locally integrated. Full API: 1,014; worker: 117; frontend/tour unit: 33; Study component: four. Web lint/typecheck/build and configuration inventory pass. Final integrated synthetic browser verification passes 1,474 assertions; real LTI acceptance is not inferred. Earlier revision-specific evidence retains its recorded attribution. Hosted 0038/0039 application, release, real-pair repair or safe refusal, and live acceptance are separate human gates; this record upgrades no live result.

## Change log
| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-27 | Require no name-based address and distinguish people in course material from the student; one _SYSTEM literal only | APPROVAL-09 Amendment1, Fred's course-material classification | TUTOR-REQ-019 |
| 2026-10-27 | Specify rename dialog, single waiting indicator, prompt-only small talk, planned images, conditional last-prompt editing and delegated read-only timing before implementation | APPROVAL-08, coordinator C1/C2 | TUTOR-REQ-005/010/012–016; DIAG-REQ-008 |
| 2026-10-25 | Record merged local verification and supersede stale implementation-pending findings; retain hosted gates and bounded summary/statistics limits | APPROVAL-07 coordinator integration; no new behavior | AUTH-REQ-007 |
| 2026-10-25 | Require existing enrollment admission on inventoried student GETs; preserve staff, mutations and enrolled processing | APPROVAL-07 Amendment 7; coordinator spec before follow-up implementation | AUTH-REQ-007; WI-26 |
| 2026-10-24 | Minimal freeze spec created before implementation | APPROVAL-01, section 2 Lane T and confirmed amendment A1 | TUTOR-REQ-001 |
| 2026-10-24 | Complete timeout detail and unconfirmed-answer display in TutorChat | APPROVAL-01 standing rule; coordinating planner grant for TutorChat.tsx and dedicated UI tests | TUTOR-REQ-001 |
| 2026-10-24 | Explicitly document that an abandoned synchronous call can resume during the next request in a warm Lambda environment | APPROVAL-02 from Fred | TUTOR-REQ-001 |
| 2026-10-25 | Define owner-scoped conversation rename and pin, additive pinnedAt responses and pinned-first listing | APPROVAL-05 rev 2, section 2 and confirmed coordinator amendments | TUTOR-REQ-002, TUTOR-REQ-003 |
| 2026-10-25 | Define responsive conversation management, centered empty chat, local greetings and starters, PromptInput attachments, waiting state and component boundary before implementation | APPROVAL-05 rev 2, Lane U and confirmed coordinator amendments | TUTOR-REQ-004–011 |
| 2026-10-25 | Permit pills only for ComposeDock/PromptInput text-entry containers; Tutor uses an existing token radius while dragging or holding attachments; every control remains boxy | Approved APPROVAL-05, 2026-10-25; DESIGN.md scoped chat-entry exception; lead designer review remains a handover follow-up | TUTOR-REQ-009, TUTOR-REQ-011 |
| 2026-10-25 | Permit a slow subtle idle loop only for Kala's logo in Tutor's new-chat empty state; stop on typing or sending, use a static reduced-motion mark, and exclude conversations, Study, Test and Diagnostic | Approved APPROVAL-05, 2026-10-25; DESIGN.md scoped mascot exception; lead designer review remains a handover follow-up | TUTOR-REQ-007 |
| 2026-10-25 | Reconcile accepted implementation: managed conversations; resizable history/local sorting; centered/floating composer; retired starters; memory-only staging and raw previews; scoped visual corrections | APPROVAL-06 section 2, accepted e1b0250 handoff and Fred’s direct Lane U instructions; supersedes initial APPROVAL-05 presentation details where stated | TUTOR-REQ-002–011 |
