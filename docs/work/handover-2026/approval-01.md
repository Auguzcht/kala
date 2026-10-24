# APPROVAL-01: planner decisions on the four audits, and the fix plan to Oct 28

Paste this whole message to the coordinating Codex chat. It replaces nothing in AGENTS.md. Base for every lane: `origin/main` at `e9de105` unless a lane says otherwise.

## 0. Audit acceptance

All four audits are accepted as complete. Two corrections to the pack, effective now:

- Migration filenames: CLI 2.114.0 accepts `0001_name.sql`. No timestamp renames. Move files as they are.
- Generated types path: keep the path the frontend already imports. `docs/engineering/database.md` will be corrected to that path by Lane DB. Do not create `packages/schema/src/database.types.ts` if it is not the existing path.

Audit evidence lives in temp folders that will disappear. Lane D copies the human-readable reports (not raw dumps, not anything secret-shaped) into `docs/work/handover-2026/evidence/` as `audit-endpoints.md`, `audit-docs-inventory.md`, `audit-migration-replay.md`, `audit-config.md`, `tutor-cloudwatch-queries.md`.

## 1. Spec-first for every fix

Full feature specs come later (WI-08). For this freeze, each code lane creates the minimal spec file for its feature from `templates/feature-spec.md`, containing only the requirements it touches, with the IDs given below and a change-log line citing APPROVAL-01. Tests name the REQ ID.

## 2. Lanes (run in parallel, disjoint paths)

### Lane S: staff route authorization (branch `codex/staff-route-auth`)
Owned: `services/api/app/routers/diagnostic.py` (only the two routes below), their tests, `docs/features/lms-ingest/README.md`.

- `GET /courses/{course_id}/assessments` and `PATCH /courses/{course_id}/assessments/{column_id}/grade` get the same staff course authorization gate already used by `POST /courses/{course_id}/content/upload`. Reuse it. Do not write a new one.
- Do not delete the routes. Grade passback stays `planned` (AGS).
- REQ: `INGEST-REQ-001` LMS gradebook read and write routes are restricted to staff who teach the course.
- Tests: student gets 403, instructor of another course gets 403, instructor of this course passes the gate (LMS mocked, no real Blackboard call).

### Lane T: tutor de-identification and request deadline (branch `codex/tutor-boundary`)
Owned: `services/api/app/routers/tutor.py`, `services/api/app/ai/rag.py`, `services/api/app/ai/router.py`, `services/api/app/ai/deidentify.py`, `services/api/app/main.py` (error mapping and timing log only), their tests, `docs/features/tutor/README.md`, `docs/features/ai-platform/README.md`.

De-identification (`AI-REQ-001`): every text sent to any model or embedding provider passes the existing sanitizer first. That covers the RAG embedding input, every prior history message, the current question and the built context. Stored rows in Supabase stay unchanged. Only the model-bound copy is sanitized. Record the sanitizer's real coverage (emails and `name:` patterns only) as a known limitation with status `partial`. Do not expand the sanitizer in this lane.
- Tests: an email in the question never reaches the embedding call payload. An email in a prior history message never reaches the chat call payload.

Request deadline (`TUTOR-REQ-001`): one budget per `/tutor/ask` request, 26 seconds from handler start.
- Every outbound call in the handler uses `timeout = min(its current timeout, remaining budget minus 3s reserve)`.
- Skip the model fallback when less than 6 seconds remain.
- Budget exhausted before an answer: return 503 with `{"detail": "...", "code": "tutor_timeout"}` and a plain retry message. Make `code` optional on the frontend (`.nullish()`). The frontend shows the message.
- Answer received but persistence fails or runs out of budget: still return the answer, and log a warning with conversation ID prefix and stage. Do not fail the request.
- Add one `tutor_timing` log line per request (same style as `practice_submit_timing`) with stage durations in ms, mode (stateless or persistent), provider role used, fallback used yes or no, and outcome. No question text, no user names, user ID prefix only.
- Tests: a slow mocked chat call yields 503 `tutor_timeout` within the budget. A slow mocked fallback is skipped near the deadline. A persistence failure after an answer still returns 200 with the answer.

### Lane F: Study deck correctness (branch `codex/study-deck`)
Owned: `services/api/app/routers/flashcards.py`, `services/api/app/bank/serving.py`, `services/api/app/learn/srs.py`, `apps/web/src/features/flashcards/`, `apps/web/src/routes/course/flashcards.tsx`, `apps/web/src/features/skill-hub/components/StudyBrowser.tsx`, their tests, `docs/features/study/README.md`.

- `STUDY-REQ-001` counts-only request: `limit=0` returns counts and stats with `cards: []` and has no side effects. No claim, no `ensure_tracked`, no exposure, no daily cap spend. The frontend comment already states this. The backend is wrong.
- `STUDY-REQ-002` served but unrated cards: a card claimed in an earlier session and never rated (`reps = 0`) is served again in review mode before any fresh top-up, and does not spend the daily new-card allowance a second time. "All caught up" shows only when there is nothing due now, no claimed-unrated card and no eligible fresh card.
- `STUDY-REQ-003` end of deck: the completion view offers two actions.
  - "Go through these again" replays the same session cards locally from card 1. It sends no new rating POSTs (the existing posted-rating guard already ensures this). Label the round as practice that does not change the schedule.
  - "Check for more cards" is today's reload behavior.
  - Empty-state copy distinguishes "All caught up" (with the next due time if the response provides it) from "No cards yet". If you add a next-due field, it is optional and nullable.
- Fix the stale docstring "Answer keys never leave the server" so it describes the Study and Test response policy accurately.
- **SQL gate:** do this in Python and selector logic if at all possible. If `STUDY-REQ-002` needs a SQL or RPC change, stop and report the exact SQL. Do not write a migration file. Lane DB is moving the migrations folder.
- Tests: `limit=0` called twice creates no schedule rows and leaves the remaining cap unchanged. A claimed-unrated card is re-served and not double-counted. Replay sends zero review POSTs.

### Lane DB: local throwaway stack (BRIEF-03 Part B) (branch `codex/supabase-local-stack`)
**Gated until Fred posts the hosted Postgres major version.** If it is 17, proceed with the CLI default.
Owned: as in BRIEF-03, plus `docs/engineering/database.md`.
- Keep the existing `supabase/config.toml` and its `project_id`. Add `[db] major_version` matching hosted.
- Move `packages/db/migrations/*.sql` to `supabase/migrations/` unchanged, leave a pointer README, update every reference listed in Part A.
- Replace the existing hosted-ref types script with the local `db:types`, written to the existing types path. Add `db:start`, `db:stop`, `db:new`, `db:reset`, `db:schema`, `db:verify`. No script may use `--linked` or a project ref.
- Write `supabase/seed.sql` with fake placeholder institution values and the minimum test fixtures.
- Run `pnpm db:verify` twice. The second run shows no diff.
- Record the 13 notices in the evidence with a one-line disposition each.
- Part C (drift) waits for Fred's dump at `.tmp/hosted_schema.sql`.

### Lane C: configuration inventory apply (BRIEF-04) (branch `codex/config-inventory`)
Approved as proposed: create `scripts/config_inventory.py`, `docs/engineering/secrets.md` and `services/worker/.env.example`, and complete the API and web `.env.example` files. Placeholders only. You may now read the two existing `.env.example` files. They are examples, not secrets. Never open `.env` or `.env.local`.

### Lane D: documentation framework install (WI-02 and WI-03) (branch `codex/docs-framework`)
Owned: `AGENTS.md`, root `CLAUDE.md`, `docs/` except `docs/engineering/database.md` and the feature spec files the code lanes create, folder `CLAUDE.md` files, `MEMORY.md`, and the three applied patch notes.
- Install the pack's docs. Reduce root `CLAUDE.md` to the pointer. Carry any still-true rule from the old root `CLAUDE.md` into `AGENTS.md` (DESIGN.md governs visuals).
- Delete the three applied patch notes (P01 to P03). The deletion commit message cites the audit evidence. Git history keeps them.
- Move every inventory row marked "archive" into `docs/archive/`, with a header naming the replacement document and the archive date.
- Turn the recap-only knowledge (inventory section 2) into ADRs or evidence files as the inventory proposes. The ADR seed list is in `docs/decisions/README.md`.
- F08 (radius) and F09 (orange usage) are recorded as findings in the design notes. No CSS or code changes.
- Create `docs/archive/incidents/INC-002-tutor-30s.md` with recovery marked "live recovery unverified".
- Run a link check over `docs/` and report broken links.

## 3. Recorded, not fixed before the freeze

Write each one as a `planned` work item in `docs/work/handover-2026/` (Lane D):
- Lessons inline generation can exceed the Lambda wall (outline plus steps). Needs an async or deadline design.
- Content upload can exceed the wall. Correct the comment that claims it cannot.
- Launch, roster and content LMS paths have no whole-request deadline.
- Bedrock client has no explicit timeout or retry config.
- No API Gateway access logs. Observability item, infra change, so it is ITO's call.
- Sanitizer only covers emails and `name:` patterns.

## 4. Merge and deploy order

1. Lanes C and D merge when green. Docs only, no deploy needed.
2. Lanes S, T and F merge when tests, lint, typecheck and build pass and the planner has approved each AUDIT REPORT.
3. Fred runs `make deploy` once after S, T and F are on `main`. Vercel deploys the web app.
4. Fred's click-through: the TESTING.md student and instructor runs, plus tutor ask (stateless and in a conversation), Study `limit=0` landing with no cap change, end-of-deck replay, and a student calling the grade route getting 403.
5. Lane DB merges after Postgres major confirmation and two clean `db:verify` runs. It affects no deploy.
6. Feature freeze after Oct 28. From then on: specs (WI-08), runbooks (WI-06, WI-07), backlog (WI-10).

Every lane ends with the AUDIT REPORT and stops before merging.

## 5. Confirmed amendments and standing scope rule
A1. Lane T also owns services/api/app/ai/bedrock.py, services/api/app/db/supabase.py, apps/web/src/lib/api-error.ts, the tutor api/schema files and their tests. Shared changes are opt-in only: a new optional deadline/timeout parameter whose default reproduces today's behavior exactly. Non-tutor callers are not edited. Add a test proving the default path is unchanged. Global Bedrock timeout/retry policy stays deferred. api-error.ts must parse flat {detail}, the new {detail, code} and a non-JSON body, with a test for each.
A2. docs/engineering/secrets.md belongs to Lane C only. Lane D excludes it.
A3. Applied migrations are immutable, comments included. Move SQL byte for byte and verify with checksums before and after. Keep the 0036 old-path comment. Update references outside supabase/migrations/ only. The pointer README explains that historical comments inside migrations keep old paths.
A4. Lane S also corrects the upload comment near diagnostic.py:304. Comment text only, stating the real bound. No code change there.
A5. Lane DB rebases after Lane D merges and updates references in the post-archive tree. It stays gated on the hosted Postgres major.
Standing rule: if a lane needs a path no other lane owns, the coordinating planner may grant it without stopping, but only when the change is opt-in or comment-only, keeps behavior unchanged outside the lane, and is listed with a reason in that lane's AUDIT REPORT. Stop only when two lanes would edit the same file or a change would alter behavior outside the lane's feature.
Dispatch Lanes S, T, F, C and D now. Each stops at its AUDIT REPORT before merging.
