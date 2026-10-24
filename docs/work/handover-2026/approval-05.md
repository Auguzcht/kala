# APPROVAL-05 (rev 2): tutor provider 502 (P0), Diagnostic and Tutor UI overhaul, parallel docs work

For Astra (coordinator). Base: `main` at `cab26de` (deployed as API `live` v6). AGENTS.md, the stop rule and the standing ownership rule all apply. Feature freeze is still **after Oct 28**. Anything not merged and deployed by then becomes a `planned` work item, not a rushed merge.

## 0. Smoke results recorded (Fred, 2026-10-25, live v6)

| Observation | Disposition |
| --- | --- |
| Study "Explain more" worked earlier and was slow. **Now returns 502** | Lane X, P0 |
| Study "Give me a hint" worked earlier. **Now returns 502** | Lane X, P0 |
| Dock follow-up in Study and in Review missed returns 502 | Lane X, P0 |
| Every 502 body is `{"detail":"Kala's model provider is unavailable right now. Please try again."}` | That is our `ModelUnavailableError` handler. The API is up and the request reached the handler. An embedding or chat provider call failed, so this is not a Lambda timeout or crash. One unexplained 503 also appears in the console. Lane X identifies its route |
| Tests and their dock follow-up worked earlier and felt fast | Re-check now. Test explanations are stored with the item. Only the follow-up is live |
| New skill shows 0 due after rating 4 cards | **Correct** (STUDY-REQ-002). Rated cards are scheduled into the future |
| Console: "Blocked aria-hidden on an element because its descendant retained focus" on card flip | Accessibility bug. Lane U fixes it with `inert` |

Paths that worked earlier in the same session now fail, so the leading explanation is **provider-side and global**, not one request shape. Ranked:

1. A provider key was rotated, revoked or disabled (401 or 403). This includes keys rotated after the exposure warning.
2. OpenRouter credits exhausted (402), or a rate or daily limit hit (429). This is especially likely on the `:free` fallback model.
3. OpenAI embeddings key or billing failing. RAG embedding runs first on every `/tutor/ask`, so this would break every path at once.
4. A regression from v6 in a specific request shape. This is now the least likely, because unchanged shapes that worked after deploy also fail.

## 1. Lane X: tutor provider failure (P0) (branch `codex/tutor-provider-502`)

Investigation first. No code until the planner approves the fix.

1. **Evidence from Fred, no code.** Fred runs the CloudWatch Logs Insights query below on `/aws/lambda/kala-api` for the last 3 hours and pastes the rows. Fred also checks:
   - the OpenRouter dashboard: key status, credit balance, and Activity for failed requests with their status codes
   - the OpenAI platform: key status, usage and billing

   He confirms whether he rotated or deleted any key today.
   ```
   fields @timestamp, @message
   | filter @message like /tutor_timing|OpenRouter|openrouter|embedding|chat request|ModelUnavailable|status/
   | sort @timestamp desc
   | limit 100
   ```
2. **Static check:** list every status code that maps to `ModelUnavailableError` in embeddings and in chat, and whether each one triggers the fallback. 402 (payment required), 401 and 403 are not in the fallback list. Confirm whether Lane T's privacy-safe logging still records the **provider name, model id, HTTP status and stage** for each failure. If it does not, that is a defect: we cannot diagnose provider failures in production.
3. **Classify** the cause from the evidence and report it. If it is a key or credit problem, the fix is operational (Fred updates the key in `kala/app` or tops up credits) and needs no deploy. Say so plainly.
4. **Approved fix scope, applied after the planner confirms the cause:**
   - Failure logs record `stage` (embed or chat), `provider`, `model`, `http_status` and `request_id`. Never bodies, never keys.
   - Distinct handling for 401, 403 and 402: log at error level, and return the same student-safe 502 message.
   - If the configured fallback model is a `:free` variant, report it. Changing models is a config decision for Fred, not a code change.
5. Then the earlier items, only once the provider path works again:
   - Compare the `/tutor/ask` bodies of Test dock, Study Explain more, Study hint, Study dock and Review-missed dock, field by field.
   - Check the sanitizer output for each shape with a unit test against the mocked provider.
   - Report the Explain-more latency stage breakdown from `tutor_timing`, and propose the smallest non-infra improvement (for example a shorter style for card explanations). No streaming work.

Owned: read access everywhere. Writes only in `docs/work/handover-2026/evidence/tutor-provider-502.md` and new tests under `services/api/tests/` until a fix is approved. An approved logging fix may touch `services/api/app/ai/router.py`, `services/api/app/ai/bedrock.py` and `services/api/app/main.py` (error mapping only). Lane B does not edit those files.

## 2. Lane B: Tutor conversation management API (branch `codex/tutor-conversation-api`)

Spec first: add `TUTOR-REQ-002` (rename) and `TUTOR-REQ-003` (pin) to `docs/features/tutor/README.md`.

- Migration `0037_tutor_conversation_pin.sql` in `packages/db/migrations/` (Lane DB has not moved the folder yet, so it carries this file along with the rest). It adds `pinned_at timestamptz null` to `tutor_conversations`. Additive only. RLS is unchanged: the existing owner policies already cover the column. Run it once against a throwaway local Supabase replay of `0001` to `0036` before review. Write `docs/runbooks/0037-apply.md` with pre-checks and post-checks. **Fred applies it in the SQL editor. Agents never do.**
- `PATCH /tutor/conversations/{id}` with body `{title?: string 1..80, pinned?: boolean}`. Scoped to owner and institution. Returns 404 for anyone else's conversation, 422 for an empty body. `pinned=true` sets `pinned_at=now()`. `false` clears it.
- `GET /tutor/conversations` adds `pinnedAt` (optional and nullable on the frontend). Order: pinned first by `pinned_at` desc, then the existing order.
- Tests: owner rename, other user 404, cross-institution 404, pin and unpin, list order, a title over 80 characters rejected.
- The API must stay compatible with the current frontend. Only new optional fields.

Owned: `services/api/app/routers/tutor.py` (new route and the list order only), `packages/db/migrations/0037_*`, `docs/runbooks/0037-apply.md`, tests, the tutor spec sections above. Lane X does not edit `tutor.py`.

## 3. Lane U: Diagnostic and Tutor UI overhaul (branch `codex/ui-overhaul`, one worktree, one dev server)

**Live dev server:** this lane runs `pnpm dev` from its own worktree on **port 5173**, because the live API's CORS allows only `http://localhost:5173`.
- First stop any other Vite on 5173, including the one kept for Kala Audit. Report which process you stopped.
- Fred copies his own `apps/web/.env.local` into the worktree. The agent only checks that the file exists and never reads it.
- Fred opens Kala through a Blackboard launch and swaps the domain for `http://localhost:5173` (the token lasts 60 minutes in one tab).
- Keep the server running while you work, so Fred sees changes as you make them.
- Diagnostic goes first, then Tutor, then the pin and rename wiring once Lane B is deployed.

Spec first: create `docs/features/diagnostic/README.md` (`DIAG-REQ-001` onward) and add `TUTOR-REQ-004` onward to the tutor spec for the behavior below. DESIGN.md governs every visual choice: tokens only, boxy buttons, no hardcoded colors.

### 3a. Diagnostic
1. Remove the leftover page header ("Build your baseline" and its subtitle) and the "Topics without course material are not included." note.
2. Remove the Study-shell imitation: the SessionBar back chevron and the progress bar. Diagnostic is opened from the sidebar and has nothing to go back to. Show the answered count next to the submit action instead ("3 of 6 answered").
3. Fix the clipping. The last question must scroll fully above the fixed submit bar on desktop and on a 375px viewport (add bottom padding equal to the bar height, or put the bar in normal flow).
4. Stale routes: list every link, route and redirect that points to an old diagnostic entry, the same way the skill-hub pass did. Redirect or remove each one. Report the list. Do not change the diagnostic API or the "due" logic.
5. Fix the flip-card `aria-hidden` focus warning (see section 0).

### 3b. Tutor layout and sidebar
1. On desktop (lg and up) the chats sidebar is always open. Remove the collapse chevron and collapsed state. On small screens the sidebar opens as a Sheet from a header button. That is required for mobile.
2. Replace Today / Yesterday / Older with two collapsible groups: **Pinned** (shown only when something is pinned) and **Recents**. Use the existing Collapsible primitive.
3. Each row on hover or keyboard focus shows a pin button and a `...` DropdownMenu with **Rename**, **Pin or Unpin** and **Delete**. Delete uses a confirm dialog and the existing DELETE route. Rename edits the title inline. **Do not add** Share, Archive or Move to project. There is no sharing (privacy) and no archive concept.
4. Pin and rename call Lane B's PATCH. Until B is deployed, keep these actions behind a check for `pinnedAt` being present in the list response, so the UI never shows a control the live API cannot serve.

### 3c. New chat start
1. Empty conversation: the dock sits vertically centered, with a greeting line above it. After the first message the dock moves to the bottom (standard chat layout).
2. Greeting: a client-side pool picked by time of day (morning, afternoon, evening, late night), plus course-aware variants ("Ready to dig into AWS101?"). Pick deterministically per day so it does not change on re-render. No model call, no extra cost, no added latency. No student name.
3. Mascot: animate Kala's own logo mark with a subtle idle loop in SVG or CSS. Respect `prefers-reduced-motion` with a static mark. Do not imitate another product's mascot. If the lead designer provides an animation asset, it replaces this.
4. Below the dock: 3 or 4 starter Suggestion chips built from the course's skills ("Explain {skill}", "Quiz me on {skill}"). Templates, not generated.

### 3d. Attachments and dock shape
1. Dragging files anywhere over the Tutor view shows a drop overlay ("Drop files to attach"). The existing PromptInput already has drag and drop. Reuse it, do not rebuild it.
2. The dock is pill-shaped when empty. It becomes a rounded rectangle (token radius) while dragging or when it holds attachments, with attachment chips inside it above the text field. Animate the change, respecting reduced motion.
3. On a new chat, the first attachment creates the conversation lazily, then uploads through the existing attachments route. Respect the backend's file-type and size limits and show its errors.

### 3e. Thinking state
While waiting, show the existing `Shimmer` with "Thinking". After about 8 seconds switch to "Still working on it". Show no invented step traces. No Reasoning component (reasoning is stripped server-side). On `tutor_timeout`, show the server's message (Lane T's work).

### 3f. Component boundary (write this into both specs)

| | Tutor | Study hub dock (lesson, study, test, review-missed) |
| --- | --- | --- |
| Purpose | Open conversations about the course | Help on the one card or question in front of the student |
| Persistence | Saved conversations, rename, pin, delete | None. Stateless, card-scoped |
| Files and images | Yes, through conversation attachments | **No.** Stateless asks have no conversation to attach to, and adding one is out of scope |
| Dock | `PromptInput` with attachments. Pill, becomes a rounded rectangle with files | `ComposeDock`, text only, always a pill |
| Shared pieces | `Message`, `MarkdownText`, `Shimmer` thinking state, `Suggestion` / `FollowUpChips`, error display, de-identified `/tutor/ask` | same |
| Not used anywhere | Reasoning, Tool, Agent, Plan, Task, Queue, Sandbox, Terminal, Model Selector (students do not pick models, cost control), Speech, Artifact, Canvas, Web Preview | same |
| Later, planned | **Sources and Inline Citation** showing which course material grounded the answer. Strong fit for Kala, but the API must first return source titles from RAG. Work item, not now | n/a |

We already vendor Vercel AI Elements in `components/ai-elements/`. Add nothing from third-party catalogs that need an account. Reuse and restyle what is there.

Owned: `apps/web/src/features/diagnostic/`, `apps/web/src/routes/course/diagnostic.tsx`, `apps/web/src/routes/course/index.tsx` (diagnostic card copy only), `apps/web/src/features/tutor/`, `apps/web/src/components/shell/TutorSidebar.tsx`, `apps/web/src/components/ai-elements/` (styling and props only), the flip-card component for the a11y fix, `docs/features/diagnostic/`, and the tutor spec sections 3b to 3f. Do not edit `ComposeDock.tsx` behavior. If shared styling must change, use an opt-in prop.

Tests: route redirects, the greeting pick, the sidebar groups, the pin and rename action gating, dock shape state, and that Delete asks for confirmation. Then lint, typecheck and build. Then a screen recording or screenshots at 1440px and 375px for: the new Diagnostic, Tutor empty state, Tutor mid-conversation, drag-over, and the sidebar menu.

## 4. Docs lanes, in parallel (no overlap with U, B or X)

- **Lane R (runbooks, WI-06 and WI-07):** draft runbooks 01 to 13 from the archived session records, MEMORY.md and the existing READMEs. Mark every unknown as `[Fred to confirm]`. Runbook 03 (Blackboard instance), 04 (Developer Portal) and 08 (LTI registration) come first. Owned: `docs/engineering/runbooks/`.
- **Lane P (specs, WI-08):** full specs for features nobody else is touching: `lti-auth`, `lms-ingest` (extend S's file), `skills`, `question-bank`, `lessons`, `twin`, `instructor-insights`, `gamification`, `tour`. Written from code and tests, with REQ statuses honest about what is implemented. Owned: those `docs/features/*` folders only.
- **Lane C2 (small):** in `docs/engineering/secrets.md`, record that `FRONTEND_URL` and `WORKER_FUNCTION_ARN` (API) and `WORKER_FUNCTION_ARN` (worker) are Lambda environment variables that override the secret bundle. Observed in the v6 deploy output. Also add WI-13 cost-driver placeholders to `infrastructure-requirements.md`.
- **Lane DB:** still gated on Fred's Postgres major. When it runs, it carries `0037` along with the other migrations.

## 5. Second deploy (target Tue Oct 27)

1. Fred applies `0037` in the SQL editor using its runbook, after B is approved. It is additive, so the live v6 keeps working.
2. Merge B, and X's logging fix if approved, then run the full checks on merged main and stop.
3. `make deploy`, check the alias moved, then push. Vercel deploys U's work if it is merged, or B's API-only change if U is not ready yet.
4. Click-through: Study hint, Explain more, Study and Review-missed dock follow-ups, Test dock, the new Diagnostic, the Tutor sidebar (pin, rename, delete), new chat with the centered dock, a file drop, and a 375px viewport check.

Anything unfinished on Oct 28 is recorded as a `planned` work item, with its branch name and status, in `docs/work/handover-2026/`.

## 6. Confirmed coordinator amendments — 2026-10-25

These direct decisions from Fred supersede conflicting assignments above.

- Current implementation base is `4f3ec29` on main. The changes since the original `cab26de` base are deployment-evidence documentation only.
- Coordinator exclusively edits `docs/features/tutor/README.md` and `docs/features/ai-platform/README.md`. B, U and X submit proposed REQ text, acceptance and a change-log line citing APPROVAL-05 before implementing. Coordinator commits one small spec commit per lane on main; the lane rebases onto that commit before implementation. B owns TUTOR-REQ-002/003 behavior; U owns TUTOR-REQ-004 onward behavior, in separate sections. If implementation exposes an incorrect spec, the lane stops and submits its correction. U alone owns the diagnostic spec.
- Coordinator first records two narrow exceptions in DESIGN.md in a separate docs commit. Chat entry containers only (Study ComposeDock and Tutor PromptInput) may be pill-shaped when empty; Tutor becomes a token-radius rounded rectangle while dragging or holding attachments. Every control, including send buttons, chips, cards and inputs, keeps the existing boxy rules. ComposeDock behavior remains unchanged.
- The second exception permits a slow, subtle idle loop only for Kala's logo mark in the Tutor new-chat empty state. It stops when typing starts or a message is sent, is absent mid-conversation and from Study, Test and Diagnostic, uses existing tokens, and is static under prefers-reduced-motion. All other motion follows DESIGN.md unchanged.
- Both exceptions carry scope, rationale and “approved APPROVAL-05, 2026-10-25” in DESIGN.md; both Tutor and Diagnostic spec change logs record them. Lead designer review remains a handover follow-up.
- Fred explicitly authorizes read-only CLI investigation of the live provider failure, replacing the instruction that Fred alone collects CloudWatch evidence. Only sanitized allowlisted metadata may be reported; no raw messages, request bodies, credentials or secret payloads. This grants no deploy, hosted writes, migration application or key rotation.
- Fred reports an OpenRouter balance of $2.63. Empty balance must not be assumed as the cause. Key status, individual request status, OpenAI billing and the failed stage require evidence.
- B, U, X, R, P and C2 work in separate GPT-6.1 sol chats/worktrees. Each returns an AUDIT REPORT before merging. DB remains gated on the hosted PostgreSQL major; migration 0037 must later be carried with the existing files.
