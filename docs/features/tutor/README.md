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

### TUTOR-REQ-017: Copy a displayed message without a server action
- Rule: Tutor user messages and completed Kala replies expose an accessible Copy control using the browser clipboard API. Copy only that message's text, without initials, status/control text, other turns or HTML execution. Show “Copied” only after the clipboard promise succeeds; report denied/unavailable clipboard access without false success. Cover saved and locally returned/unsaved messages. Pending answer placeholders have nothing to copy. Controls remain keyboard/touch accessible and use existing tokens.
- Presentation: On hover-capable devices, reveal a small rounded icon-only Copy button only within the corresponding message hover/focus region. Keyboard focus reveals it, and touch/no-hover devices keep it discoverable with a 44px target. Use the shared root-sidebar Tooltip primitive above the icon. Keep truthful Copied feedback in the tooltip and accessible status, preserve clipboard failure direction and avoid layout shifts.
- Rule: This is frontend-only. Copy never sends, uploads, edits, deletes or makes an API request. Sent-message editing remains deferred under TUTOR-REQ-015 / WI-29; no edit control or edit-message work is authorized. Shared Study components must keep their current default behavior outside Tutor.
- Acceptance: Exact selected-message content, both roles, saved/local messages, clipboard success/failure/unavailability, repeated activation, keyboard/touch and375px/1440px. No mutating request and no edit affordance.
- Status: done-awaiting-confirmation. The remaining APPROVAL-09 clipboard-only item is implemented locally during Fred’s 2026-10-28 open-item audit, WI-34.
- Verified by: message-copy.browser.mjs passes 97 assertions at 375px/1440px, including hover/focus visibility, icon-only shared top tooltip and touch targets. Integrated Tutor browser checks pass 383 assertions, including saved/local/optimistic user copying, completed saved/local replies and no copying of pending answers. Focused Tutor/draft units pass 13. Shared Study blocks are unedited. No live clipboard acceptance claim.

### TUTOR-REQ-018: Start an assigned Tutor item with an unsent skill draft
- Rule: “From your instructor” Start for a Tutor plan item opens the new-chat Tutor surface in the same validated course, with an editable draft about the assigned skill. Use the displayed skill name, falling back to the assignment title, to ask Kala to explain the key ideas and work through an example. Do not reopen the previously selected conversation or send automatically. No profile name, private history or implicit instructor-note payload is added.
- Handoff: Use browser navigation state carrying a unique draft ID, course ID and text, validated with Zod and matched to the current session course. Remove the conversation search parameter and suppress automatic history resume for this fresh entry. Keep draft text out of URLs and persistent storage. Seed the new composer's draft once and focus it so Enter or Send submits. Ordinary re-renders preserve user edits and staged attachments. Selecting New chat or a saved conversation clears the handoff's composer session rather than reapplying its text.
- Rule: Preserve lazy conversation creation on actual Send. Start alone does not create a persisted conversation, call ask, upload, complete a recommendation or change its decision/state. Use frontend state only; no backend/API/contract change or tour enablement is authorized.
- Acceptance: Tutor Start reaches a new-chat surface, has the right skill context and nonempty unsent draft, makes zero mutating requests, allows editing, and asks only after an explicit Send. Other plan item actions and roles stay unchanged. Preserve existing draft/attachment recovery behavior.
- Status: implemented locally for Fred's direct APPROVAL-09 assigned-start request, WI-34. The hidden tour remains untouched and human confirmation is pending.
- Verified by: assigned-draft.test.mjs and ui-overhaul.browser.mjs, 339 assertions including assigned topic/title fallback, focused editable draft, staging, New chat, Enter/Send and zero automatic mutations at both widths. Final cumulative frontend regression run is recorded in WI-34.

### TUTOR-REQ-019: Never use a material person's name to address the student
- Rule: The Tutor system prompt says never address the student by name. Any names in course material refer to people in that material, not the student. Keep normal discussion of named people in curriculum possible without turning those names into the learner's identity. This is a system-prompt-only instruction, not a new sanitizer, identity lookup, classifier or provider/configuration change.
- Acceptance: The existing mocked-provider small-talk tests assert both instructions reach the actual provider-bound system prompt for default/detail styles, alongside all retained teaching/safety rules. Whole-module AST proof permits only the one _SYSTEM string literal; all19 existing enrollment-guarded functions remain identical. Full API suite and the116-case enrollment matrix pass. Live model behavior remains Fred's deploy/FG-9 check; a mocked assertion does not establish compliance.
- Status: implemented locally; combined frontend integration, Fred deployment and live greeting acceptance remain pending under APPROVAL-09 Amendment1.
- Verified by: test_tutor_small_talk_approval08.py assertions for both styles; full API1016 and enrollment116 pass; whole-module E1 AST and all19 guarded functions remain identical apart from _SYSTEM. No live compliance claim.

### TUTOR-REQ-020: Load saved conversations and chat history with skeletons

- Rule: While a saved conversation or the chat-history list is initially loading, show skeleton blocks without visible “Loading conversation…” or “Loading chats…” copy. Keep an accessible status region with a descriptive aria-label and aria-busy. Skeleton motion stops under reduced motion. Show no spinner for these reads. Preserve conversation selection, responsive history, loaded/error/empty states, request scope and recovery behavior.
- Acceptance: Delayed conversation/list requests at 375px/1440px show skeleton-only regions with accessible names and busy state. The mobile history Sheet has the same skeleton-only behavior as desktop history. Successful reads replace the skeletons with their normal state. Reads introduce no create, ask, upload, edit or delete request. Existing retry and unsaved-answer recovery assertions continue to pass.
- Status: implemented locally under Fred's APPROVAL-09 loading-copy request, WI-34. Human confirmation remains pending.
- Verified by: ui-overhaul.browser.mjs passes 295 assertions, including WI-34-T05 at 375px/1440px for saved-chat/history skeletons, accessible busy states, reduced motion and unchanged mutation counts. No hosted acceptance claim.

### TUTOR-REQ-021: Make explanation chips explicit follow-up requests

- Rule: Explain like I'm 5 and More detail create a new student turn requesting that treatment of Kala's last answer in the active owned conversation. Send an explicit instruction and the existing eli5/detail style, rather than resending the original student question. The optimistic, saved and returned-unsaved user bubble must show the question actually submitted. Reuse conversation history through the existing ask contract, including after reopening a saved chat. If the latest visible answer is returned-unsaved, include that answer as quoted context in the new question so the request does not silently target older saved history.
- Presentation: Label the chips with static 🧸 and 🔎 emoji, hidden from assistive naming so the existing action names remain clear. Show them only after the latest completed explanatory exchange. Hide them for recognised greetings, thanks, farewells, simple acknowledgements and small talk, even after earlier learning content in the same chat. Hide them while a newer turn is pending or failed. Determine this locally from the current saved/local turn pair, with no intent API/model call or course-keyword allowlist. Common casual phrases are conservatively filtered, while mixed greeting-plus-learning requests and short technical questions keep their actions. This frontend heuristic is not a general semantic intent classifier.
- Rule: Preserve pending/error/retry and saved/unsaved-answer recovery. Only one ask runs at a time, with the existing single shimmer and stable disabled Send. Changing conversations discards the old scope's local turns and follow-up context. Add no backend field, provider change or sent-message edit.
- Acceptance: At 375px/1440px, both chips show a new explicit user bubble before the pending answer, submit the correct style and same conversation ID, and do not resubmit the original question. Repeated chips target the latest answer. Reopened conversations, returned-unsaved answers, failures/retry and conversation switches retain correct scope and request text. Synthetic requests prove intent and wiring, not live model quality.
- Status: implemented locally under Fred's APPROVAL-09 follow-up request, WI-34. Human confirmation remains pending.
- Verified by: TutorChat.test.mjs covers saved/reopened and returned-unsaved follow-up context. presentation.test.mjs passes 10 units. ui-overhaul.browser.mjs passes 383 assertions including explicit instructions, static emoji, latest saved/local casual-turn filtering, styles, conversation scope and retry at both widths. Synthetic wiring checks do not establish live answer quality.

### TUTOR-REQ-022: Browse the current chat's own prompts with arrow keys

- Rule: In the Tutor input, ArrowUp recalls the latest submitted user message and repeated Up moves toward older prompts. ArrowDown moves toward newer prompts, then restores the exact draft present before browsing, including empty. Never include assistant replies, other conversations, course chats or attachments in prompt history. Use existing owned conversation messages plus displayed local/unconfirmed user turns, not a persistent second store.
- Rule: History navigation never sends, creates, edits, uploads or asks the model. The recalled prompt remains editable and requires the existing explicit Enter/Send. Editing a recalled prompt ends browsing and treats the edited text as a new draft. Successful submit and chat/new-chat/course changes reset the history position. Retain the pre-submit draft on failed/blocked file submissions.
- Keyboard boundary: Preserve selection, IME composition and modified Up/Down. In multiline text, retain native movement except Up at the first logical line and Down at the last logical line. ArrowDown outside history does nothing beyond native editing. Clamp at the oldest entry and restore the original draft/caret when leaving the newest entry. Attachment readiness and submit locks remain unchanged.
- Acceptance: Test empty/draft restoration, older/newer bounds, edited recall, current-chat scope, local unsaved prompts, reset after send/new chat/change, multiline boundaries, modifier/selection/IME handling and zero requests from arrow navigation. Verify Enter sends exactly the chosen prompt and no extra calls at 375px/1440px.
- Status: done-awaiting-confirmation. Implemented locally under Fred's final APPROVAL-09 input-gesture request, WI-34.
- Verified by: prompt-history.test.ts passes four units. prompt-history.browser.mjs passes 62 assertions at 375px/1440px for traversal, draft/caret restoration, native editing boundaries, chat/submit resets and zero service writes. ui-overhaul.browser.mjs passes 383 assertions, including saved, failed and returned-unsaved user prompts. Live keyboard acceptance remains pending.

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
| 2026-10-27 | Define validated navigation-state handoff, fresh-chat resume suppression, editable focused skill draft and explicit-submit-only behavior before implementation | Fred's APPROVAL-09 assigned Tutor Start request, WI-34 | TUTOR-REQ-018 |
| 2026-10-27 | Specify explicit last-answer follow-up requests and truthful user turns for explanation chips before frontend implementation | Fred's APPROVAL-09 follow-up request, WI-34 | TUTOR-REQ-021 |
| 2026-10-27 | Specify skeleton-only saved-chat and history loading with accessible status names and reduced-motion support | Fred's APPROVAL-09 loading-copy request, WI-34 | TUTOR-REQ-020 |
| 2026-10-28 | Specify hover/focus copy icons with upward tooltip, emoji/contextual explanation chips and current-chat arrow-key prompt history before final freeze edits | Fred’s final Tutor polish and keyboard gesture requests, WI-34 | TUTOR-REQ-017/021/022 |
| 2026-10-28 | Resume the remaining clipboard-only message-copy item found during the open-item audit, preserving no-send/no-edit and shared Study defaults | Fred’s APPROVAL-09 completion audit, WI-34 | TUTOR-REQ-017 |
| 2026-10-27 | Specify frontend-only message copy and new-chat unsent skill prefill before Fred edits; keep sent-message edit deferred | APPROVAL-09 | TUTOR-REQ-017/018; TUTOR-REQ-015 retained |
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
