# Question bank: generate at ingest, serve from the database

Status: proposed. Supersedes the click-time generation paths (Piece 2's `item_generation_jobs` for diagnostic, practice, and lesson checks, plus the flashcard deck top-up). Nothing in this doc changes ingest, embedding, or tagging.

## 0. Audit amendments (2026-10-06)

From Codex's read-only audit. **Where this section conflicts with any later section, this section wins.** File is `docs/design/question-bank-design.md`.

### A1. Context and depth use similarity plus tags, not tags alone

Today `_context_for()` embeds the skill name and calls `match_content_items`, which ignores `skill_id`. The tagger is the least reliable stage (partial coverage, `finish_reason=length` on large chunks). The bank must not depend on it.

- **Context for a batch:** union of (a) chunks with `skill_id` = this skill and (b) top similarity matches for the skill name with similarity at or above `SIM_THRESHOLD`. Deduplicate by chunk id. Rotate the window per batch as before.
- **Depth (§4):** count of distinct chunks in that union, minimum 200 characters each.
- **`SIM_THRESHOLD`:** set from Brief B's measured similarity distribution. Not guessed.
- **§6.6 Gotcha 1 downgraded:** retag on approval still runs (it improves context), but a new skill can build from similarity alone. It never blocks on the tagger.

### A2. One MCQ pool per skill, used by both Study and Test

Flashcards are MCQs presented as flip cards (front = prompt, back = correct choice label plus explanation). The study-to-test bridge needs choices to exist. So:

- The bank generates **MCQs only**, `kind = 'practice'`, `origin = 'bank'`. The separate flashcard batch schema in §6.3 is **dropped**.
- §4 collapses to one target per skill: `mcq_target`. `card_target`, `CARD_*` constants, `card_ready` and `cardTarget` are dropped everywhere.
- Study's deck draws from the same pool and calls `srs.ensure_tracked` as today.
- Existing `kind = 'flashcard'` items keep working. The deck reads both kinds during cutover.

### A3. Exposures distinguish studied from tested

Studying a card then testing on it is the bridge's whole purpose, so a studied item must not count as "seen" for test picking. `item_exposures` gets:

| Column | Meaning |
|---|---|
| `last_studied_at` | Shown in Study (flip deck) |
| `last_tested_at` | Served in a test set, diagnostic, or lesson check |
| `last_answered_at`, `last_correct` | Graded answer only |
| `times_tested` | Replaces `times_served` |

Test picking (§7.1) uses only tested and answered columns. Study uses SRS as today.

### A4. Submit carries `set_id`

With `quiz_set_items`, one item can be in many sets. The server can no longer read the set off the item.

- `POST /practice/{course_id}/submit` body gains optional `set_id`. When present, the server verifies (`set_id`, `item_id`) exists in `quiz_set_items` and updates `quiz_set_attempts` for that set. When absent, no set bookkeeping happens.
- Frontend `PracticePanel` passes its current `setId`.
- Every `generated_items.set_id` reader and writer listed in the audit (§4 of the report) moves to the join table. `set_id` is never written for new rows. The study-to-test bridge stops updating `set_id` and inserts join rows instead.

### A5. Tag and bank alternate when both have work

Today `tagBackfill` is skipped whenever item generation claims work, which starves tagging for a whole first build. New rule: a small `worker_state` row records which long job ran last. When both `bankBuild` and `tagBackfill` have pending work, they alternate runs. When only one has work, it runs every time. Targeted on-demand runs (§6.6) follow the same rule for their own course.

### A6. Remaining click-time model calls to remove

- `GET /practice/{course_id}/next` (sync `generate_question`). No frontend caller. Switch to a single bank pick or delete the route. Decide in the build brief.
- Flashcard deck top-up (sync, concurrency 8). Replaced by bank reads per A2.

### A7. Cutover hygiene

- Cancel live `item_generation_jobs` rows at cutover (two stuck `in_progress` practice rows exist now).
- `source_chunk_ids` was added in migration 0008. The audit missed it. Verify which writers populate it before §6.2 relies on it.

### A8. Benchmark results (2026-10-06, `docs/bugs/batch-generation-benchmark.md`)

These **replace** the starting values in §4 and §6 where they conflict.

| Constant | Value | Source |
|---|---|---|
| `SIM_THRESHOLD` | 0.544 | Measured similarity distribution |
| `MCQ_BATCH` | 5 | 98.3% validator pass, no near-duplicate batches |
| `max_tokens` (bank batch) | 8192 | Same |
| `BANK_CONCURRENCY` | 2 | Concurrency 4 was 2x slower (provider queuing), no 429s |
| Batch schema | `{"items": [...]}` | Both shapes accepted. Object chosen for consistency with existing strict schemas |

**A1 is revised:** bank context and depth use **similarity only** (chunks at or above `SIM_THRESHOLD`). Tagged chunks are not included, because current tags are noisy. Revisit after the tagger fix (Brief 3).

**Open before the build brief:** p50 and p95 batch latency, and whether the "3 batches to usable" estimate covered all approved skills or only the 3 benchmark skills.

**Latency (follow-up):** batch 5 at 8192 tokens measured p50 62.9s, p95 214.4s. 5 of 15 runs over 75s, 4 of 15 over 90s. **This blocks the bank builder as specified.** A ~27% rate of calls exceeding the 90s per-call cap means wasted spend and permanent retries on slow skills. Resolved by Brief B2 (routing and reasoning effort) and, if needed, a worker timeout increase (A11).

**Depth (follow-up):** similarity depths for the 10 approved skills are `3, 1, 8, 7, 1, 1, 2, 9, 8, 9`. None are zero. Four skills are thin (depth 1 or 2) and will cap at 6 to 12 questions. Expected, and the depth cap is doing its job.

### A13. Final bank model config (Brief B2, 2026-10-06)

`docs/bugs/batch-generation-routing-benchmark.md`. Variant D chosen.

| Setting | Value |
|---|---|
| Model | `deepseek/deepseek-v4.1-flash:nitro` |
| `reasoning` | `{"effort": "low"}` |
| Token param | `max_completion_tokens: 8192` (`max_tokens` is deprecated) |
| Measured | p50 6.0s, p95 8.2s, max 8.3s, 100% validator pass, $0.003 per batch |
| Per-call cap | 45s |
| Bank job budget | 100s inside the existing 120s worker |

Scoped to a new `bank` model role. The legacy `item` role is not changed by this work.

### A11. Worker timeout: VOID

B2 brought p95 to 8.2s. Worker timeout stays at 120s. Kept below for the record only.

### (void) A11 original text

If B2 does not bring p95 batch latency under 75s: raise the worker Lambda timeout to 600s and set the bank per-call cap to 240s, bank job budget to 540s. This is not the "bigger timeout moves the cliff" mistake: every call stays individually capped and all bank work is already chunked and resumable. Leases (§6.6) prevent overlap with the next scheduled run.

### A12. `quiz_set_items.item_id` uses NO ACTION, not RESTRICT

RESTRICT is checked immediately, so deleting a legacy set (which cascades to both `quiz_set_items` and `generated_items`) can fail depending on cascade order. NO ACTION checks at end of statement. Still blocks deleting a bank item that is in a set.

### A14. Thin context is a content state, not a failure (Brief D2, 2026-10-06)

D2 found 7 bank calls ran on 241 to 507 characters of context and produced ungrounded or runaway output. Those items were retired.

- `MIN_CONTEXT_CHARS = 1000`. Below it, **no model call**.
- A thin skill gets status `no_material` with no backoff, no failure count, and no path to `error`. Staff see the reason in `last_error` (for example `thin: 241 chars across 1 chunk`). Students see the normal no-material copy.
- Every run re-evaluates depth and context. When new material pushes context over the threshold, status returns to `building` automatically.
- Result on AWS101: 8 of 12 skills buildable. The EC2 troubleshooting skill's only match is a 60-character assessment heading, which is correct `no_material`.
- `max_completion_tokens` stays 8192. Normal-context batches peaked at 5,928 tokens.

### A15. First full build and quality review (Brief D3, 2026-10-06)

Result: 8 of 8 buildable skills usable in 3m30s, 30 model calls, $0.19.

Quality rules added for `generation_version = "bank-v2"`:
- **Shuffle choice order at insert.** Correct answer position is uniformly random. Choice ids are kept, only array order changes (the frontend never shows ids). Applied once to existing live bank items, safe because `bank_serving` is false and no student has seen them.
- **Plausible distractors.** Prompt requires every wrong choice to be believable to an unprepared student. Validator rejects an item whose wrong choices contain absolute words (always, never, no, none, identical, only, every, all) in 2 or more of them.
- **Vary format.** Prompt forbids reusing a choice set already used in the "do not repeat" stems.
- **Clamp batch to need.** Request `min(MCQ_BATCH, target - ready)` items.
- **Clear `last_error`** on any successful batch.

Not fixed by code: three AWS101 skills are course logistics (badge deliverables, certification readiness, certification pathways). These are a skill-review decision for the instructor. Logistics-skill filtering in the skill proposer is a later brief.

### A9. Deck must filter explicitly

The current flashcard deck query does not filter on `kind`, so it can include tutor and diagnostic items. The bank deck reads only `kind in ('practice', 'flashcard')` and `retired_at is null`. Tutor items (lesson-check legacy) and diagnostic items are never shown in Study.

### A10. `source_chunk_ids` writers

Only the lesson shell writes it today. The bank builder must write it on every bank item. It drives round-robin chunk diversity (§7.1) and retirement when a chunk is removed.

## 1. The rule

**Reusable learning content is built in the background and stored. Personalized conversation stays live.**

| Surface | Source | Model call when a student clicks? |
|---|---|---|
| Test (practice sets) | Bank MCQs | No. Database pick. |
| Study (flashcards) | Bank flashcards | No. Database pick plus SRS tracking. |
| Diagnostic | Bank MCQs, one per skill | No. |
| Lesson comprehension checks | Bank MCQs for the step's skill | No. |
| Lesson teaching steps | Live (ling, sync) | Yes, as today. Already works. |
| Tutor | Live (ling, sync) | Yes, as today. Already works. |

The student never waits on the slow structured-output model. The only places a model runs at click time are the two that already fit inside 30 seconds.

## 2. The pipeline

```
Instructor side (background, existing):
  ingestWalk -> embedBackfill -> tagBackfill
  skill approval (HITL, existing)

Bank side (background, NEW):
  bankBuild  (worker job, deficit-driven reconciler)
      reads: approved skills + tagged, embedded chunks
      writes: generated_items rows (origin='bank')

Student side (instant):
  Test / Study / Diagnostic / Lesson checks
      -> pick from bank, filtered by what this student has seen
```

### Why a reconciler and not a trigger

The bank builder does not react to events like "ingest finished" or "skill approved". Every run it asks one question per approved skill: **how far below target is this skill?** Then it fills the gap.

That single mechanism covers every case without special code:

| Situation | What the reconciler sees | What it does |
|---|---|---|
| New course just ingested | Every skill at 0 | Builds all of them |
| Skill approved mid-term | One new skill at 0 | Builds that one |
| A student is running out of unseen questions | Target raised (see §5) | Tops up |
| Run killed mid-batch | Skill still below target | Finishes next run |
| Model provider down | Skill still below target, backoff set | Retries after backoff |
| Content added to a skill | Depth cap rises (see §4) | Builds more |

Nothing to forget to wire up. Nothing that silently never fires.

## 3. Schema changes

One migration, `0021_question_bank.sql`. Apply before deploying the worker, same order rule as 0018.

### 3.1 `generated_items`: new columns

| Column | Type | Purpose |
|---|---|---|
| `origin` | text, default `'legacy'`, check in (`legacy`, `bank`) | Separates bank items from old per-click items |
| `retired_at` | timestamptz, nullable | Soft delete. Every reader filters `retired_at is null` |
| `generation_version` | text, nullable | Prompt version. Lets a prompt fix retire a whole old generation |
| `stem_hash` | text, nullable | Normalized prompt hash for exact-duplicate blocking |

Plus a partial unique index on (`course_id`, `skill_id`, `kind`, `stem_hash`) where `retired_at is null` and `origin = 'bank'`. The database refuses exact duplicates even if two runs race.

**Never hard-delete a bank item.** `srs_state.item_id` cascades on delete and `guided_lesson_steps.check_item_id` nulls on delete. Retiring is safe. Deleting destroys student schedules.

### 3.2 `quiz_set_items` (new join table)

| Column | Notes |
|---|---|
| `set_id` | FK to `quiz_sets`, cascade |
| `item_id` | FK to `generated_items`, restrict |
| `position` | smallint |

Primary key (`set_id`, `position`), unique (`set_id`, `item_id`).

**This fixes a real trap.** Today `generated_items.set_id` means an item belongs to at most one set, and deleting a set cascades and deletes its items. With a shared bank, one MCQ appears in many students' sets. If we kept writing `set_id`, deleting any set would delete bank questions out from under every other student. Rule: **bank items never get `set_id` written.** The migration backfills `quiz_set_items` from existing `set_id` rows so old sets keep working, and all set readers switch to the join table.

### 3.3 `item_exposures` (new)

Per student, per item. This is how "unseen" works.

| Column | Notes |
|---|---|
| `institution_id`, `user_id`, `course_id`, `skill_id`, `item_id` | Tenant scoped |
| `first_served_at`, `last_served_at` | Set when the item lands in a set, deck, diagnostic, or lesson check |
| `times_served` | integer |
| `last_answered_at`, `last_correct` | Set on submit |

Primary key (`user_id`, `item_id`).

Why not derive this from `evidence_events`? Because `evidence_events` has no `item_id`. It cannot answer "has this student seen this question". It's also append-only, so we can't add the column after the fact without a migration on the research dataset. A small purpose-built table is the honest fix, same reasoning as `quiz_set_attempts` in 0013.

RLS: student reads own rows, teacher of the course reads theirs, writes are service role only.

### 3.4 `skill_bank_state` (new)

One row per (course, skill). The reconciler's bookkeeping and the frontend's status source.

| Column | Notes |
|---|---|
| `institution_id`, `course_id`, `skill_id` | Unique on (`course_id`, `skill_id`) |
| `status` | `waiting_content`, `building`, `ready`, `no_material`, `error` |
| `mcq_target`, `card_target` | Current targets (§4, §5) |
| `mcq_ready`, `card_ready` | Cached counts of live bank items |
| `leased_until` | Prevents two worker runs building the same skill |
| `next_attempt_at` | Backoff after provider failure |
| `consecutive_failures` | Drives backoff and the `error` state |
| `last_error` | Sanitized, never shown to students |
| `updated_at` | |

RLS: default deny, same as `item_generation_jobs`. Students see counts only through the API.

## 4. Targets and the shallow-content cap

Corpus depth is the real ceiling on question quality. The 2026-09-19 sample proved it: five questions from a skill with one real fact are five rewordings. So targets scale with content, and never exceed what the content supports.

```
depth          = tagged, embedded chunks for this skill (min 200 chars each)
mcq_target     = min(MCQ_BASE + replenish, MCQ_PER_CHUNK * depth, MCQ_MAX)
card_target    = min(CARD_BASE,           CARD_PER_CHUNK * depth, CARD_MAX)
```

Starting values, tune after the first live build:

| Constant | Start |
|---|---|
| `MCQ_BASE` | 20 |
| `MCQ_PER_CHUNK` | 6 |
| `MCQ_MAX` | 80 |
| `CARD_BASE` | 20 |
| `CARD_PER_CHUNK` | 8 |
| `CARD_MAX` | 60 |
| `MIN_USABLE` | 5 (minimum for a skill to count as `ready`) |

A skill with zero qualifying chunks goes to `no_material`. That's a permanent state until content changes, not a retry loop. The frontend shows setup copy, never "try again".

## 5. Replenishment (low-water mark)

Each run, for each skill, the reconciler checks the student closest to running out:

```
min_unseen = minimum over active students of (live bank MCQs not in their exposures)
if min_unseen < LOW_WATER (10) and mcq_target < MCQ_MAX:
    mcq_target += REPLENISH_STEP (15), capped by the depth cap
```

"Active student" means any evidence in this course in the last 14 days. A course with no active students never replenishes, so we don't pay for questions nobody will see.

When a skill hits its depth cap and a student exhausts it anyway, the student gets repeats (§7.3). They never hit an empty screen.

## 6. The bank builder job

### 6.1 Placement in the worker

```
reconcileMastery -> ingestWalk -> embedBackfill -> readinessSnapshot
  -> bankBuild -> tagBackfill
```

`bankBuild` replaces `itemGeneration`. Same budget rule as today: when it claims the long-model slot, `tagBackfill` is skipped and the skip is logged visibly.

### 6.2 One run

1. Recompute `mcq_ready`, `card_ready`, targets, and status for every approved skill in active courses.
2. Pick skills below target where `leased_until` and `next_attempt_at` have passed. **Breadth first:** any skill below `MIN_USABLE` goes before any skill being topped up. Every skill becomes usable before any skill gets deep. That's what makes a new course feel fast.
3. Lease the picked skills (`leased_until = now + 110s`).
4. Run batch calls with at most `BANK_CONCURRENCY` (start at 2) in flight, inside a 100 second job deadline, 90 second per-call cap.
5. For each response: validate each item individually, keep the valid ones, drop the rest (§6.4). Insert with `origin='bank'`, `stem_hash`, `source_chunk_ids`, `generation_version`. Unique-index conflicts are silently skipped.
6. Release leases, update counts, clear or bump backoff.

### 6.3 One batch call

One request returns several items as a JSON array, grounded on a rotating window of the skill's chunks. Each call starts at a different chunk offset so batches don't converge on one fact. That's `_rotated_context` reused.

| | MCQ batch | Flashcard batch |
|---|---|---|
| Items per call | `MCQ_BATCH` (start 5) | `CARD_BATCH` (start 8) |
| Schema | array of the existing MCQ object | array of {front, back, explanation} |
| `max_tokens` | Sized from measurement (§10, Step 1). Floor 4096. | Same |

**The `max_tokens` rule applies with more force here.** A batch is a bigger output and the item model is a reasoning model. Undersized budget returns `finish_reason=length` with empty content, which looks like "the model found nothing". Size from the longest measured run, and log `finish_reason` on every call (Brief 2's telemetry).

The prompt receives the stems already in the bank for this skill (most recent 30, truncated) with an instruction not to repeat them. The model sees what exists before writing more.

### 6.4 Validation per item (reject, never repair)

- Exactly 4 unique choices, `correct_choice_id` matches one of them
- Banned meta phrases (the existing list: excerpt, passage, according to, ...)
- No "all of the above" / "none of the above"
- Stem 20 to 400 characters
- `stem_hash` not already live for this skill
- Near-duplicate check: token Jaccard similarity above 0.8 against live stems for the skill is rejected

A batch where every item fails counts as a failure for backoff. A batch where some pass is a success.

### 6.5 Failure handling

| Failure | Result |
|---|---|
| Provider timeout or 5xx | `consecutive_failures += 1`, `next_attempt_at` backoff 15m, 30m, 60m, 120m, 240m |
| Provider 429 | Same backoff, and stop starting new calls this run |
| `finish_reason=length` | Counts as failure. Logged with token count so the budget can be raised |
| 5 consecutive failures | `status = error`. Still retried at the 240m cadence. Visible on the instructor dashboard |
| No qualifying chunks | `status = no_material`, no retry until depth changes |
| Worker killed mid-run | Lease expires, skill picked up next run, unique index blocks duplicates |

### 6.6 On-demand trigger (approved 2026-10-06)

The 15 minute schedule stays as the safety net. On top of it, the API async-invokes the worker (`InvocationType=Event`, returns in milliseconds) at these moments:

| Event | Payload |
|---|---|
| Ingest job completes (worker-side, invokes itself) | `{"trigger": "bank", "courseId": "..."}` |
| Instructor approves one or more skills | `{"trigger": "skills_approved", "courseId": "..."}` |
| Bank status poll sees a skill below `MIN_USABLE` with no build in progress | `{"trigger": "bank", "courseId": "..."}` |

**Gotcha 1: approval does not retag.** Content rows already attempted by the tagger are excluded from the pending query. A newly approved skill has zero tagged chunks until those rows are re-attempted. So a `skills_approved` run does, in order: reset `tag_attempted_at` on unmatched rows for that course (the existing `/content/retag` logic), run `tagBackfill` for that course, then `bankBuild` for that course. Without this step the bank sees `depth = 0` and marks the new skill `no_material`. Codex must confirm in the audit whether bank depth comes from tags or from RAG retrieval, because that decides whether this retag step is required or optional.

**Gotcha 2: one run is not enough.** Tagging plus building a course can exceed 120 seconds. When a targeted run ends with work remaining, the worker re-invokes itself with the same payload and `chainDepth + 1`.

Guards, all required:

- **Debounce.** `courses.bank_kicked_at`. The API only invokes if the last kick was over 60 seconds ago. Approving 10 skills one click at a time sends one invoke, not 10.
- **Chain limit.** `chainDepth` stops at 20. After that the 15 minute schedule takes over. Logged loudly. Prevents a runaway loop from a bug or a permanently failing skill.
- **Leases.** `skill_bank_state.leased_until` already prevents a scheduled run and a targeted run from building the same skill at once.
- **No chaining on throttle.** A run that stopped because of a 429 or provider failure does not re-invoke. Backoff decides when it retries.
- **Targeted runs stay narrow.** A targeted run only touches its own course. It skips `reconcileMastery`, `ingestWalk`, and `readinessSnapshot`.

**Infra change (explicitly approved for this work):** the shared Lambda role gets `lambda:InvokeFunction` on the worker function ARN only. The API gets the worker ARN as an env var. Both changes go through `infra/terraform`, not the console.

## 7. Serving (the student side)

### 7.1 Picking order (shared helper `pick_bank_items`)

For a student, skill, kind, and count `n`:

1. **Unseen** items (no exposure row), shuffled, round-robin across `source_chunk_ids` so one set covers different facts
2. **Previously missed** (`last_correct = false`), oldest answer first
3. **Seen and correct**, least recently served first

Write exposure rows for every served item in the same request. Retired items are never picked.

### 7.2 Per surface

**Test, `POST /practice/{course_id}/set?size=N`**
Sync, no model. Allowed sizes 5, 10, or 20. Creates `quiz_sets` plus `quiz_set_items`. If the skill has at least `MIN_USABLE` items, returns `status: "ready"` with up to N items (fewer if that's all there is, with `readyCount` telling the truth). Below `MIN_USABLE` returns `status: "preparing"` with no set created.

**Study, `GET /flashcards/{course_id}/deck`**
Due cards first (existing SRS), then fills with untracked bank cards via `srs.ensure_tracked` (database only). Top-up generation is removed. This also solves parked item #19: a fully graduated queue now pulls fresh bank cards instead of going empty.

**Diagnostic**
One MCQ per due skill. The pick must be stable across page reloads before submit, so it uses a deterministic choice: the oldest unseen item for this student whose Bloom level is closest to the skill's level. Same input, same question, until the student answers. Skills below `MIN_USABLE` appear in `pendingSkillIds` (building) or `failedSkillIds` (no material), using the contract the frontend already handles.

**Lesson checks**
When a lesson is first generated, each step gets a bank MCQ for the skill, preferring one whose `source_chunk_ids` overlap the step's chunks. If none exist yet, `check_item_id` stays null and the next lesson GET fills it in. No lesson queue rows.

**Study-to-test bridge**
Unchanged, except it writes `quiz_set_items` instead of `set_id`.

### 7.3 Exhaustion

A student who has seen everything gets tier 2 and tier 3 items. The UI says "You've seen every question for this skill. Here are the ones worth another look." Replenishment (§5) is already running in the background. They never see an empty state because of exhaustion.

## 8. Bank status API and live updates

### 8.1 Endpoint

`GET /courses/{course_id}/bank/status`

```json
{
  "courseId": "...",
  "building": true,
  "skills": [
    {
      "skillId": "...",
      "status": "building",
      "mcqReady": 12,
      "mcqTarget": 30,
      "cardReady": 8,
      "cardTarget": 20,
      "usable": true
    }
  ]
}
```

`usable` is `mcqReady >= MIN_USABLE`. The frontend never computes it.

### 8.2 Polling, not Realtime

The frontend polls this endpoint every 10 seconds **only while `building` is true**, and stops when it's false. That's the same pattern already used for lesson generation.

Why not Supabase Realtime:

- Realtime on `generated_items` would push rows (answer keys included) to any subscribed student. RLS on that table is staff only for exactly this reason.
- Realtime on `skill_bank_state` is possible later, but the worker writes in batches every run. A socket adds no visible speed over a 10 second poll.
- Polling reuses code, tests, and patterns that exist today.

Revisit only if the build cadence gets fast enough that 10 seconds is the bottleneck.

## 9. Frontend contract (states to design for)

Every student surface handles exactly these states per skill. Nothing else exists.

| State | Condition | Test tab | Study tab | Skill card on picker |
|---|---|---|---|---|
| Ready | `usable`, status `ready` | Sets generate instantly | Deck loads | Normal |
| Building, usable | `usable`, status `building` | Sets generate instantly. Subtle "More questions on the way" | Normal | Normal |
| Building, not usable | not `usable`, status `building` | "Preparing questions (12 of 30)" with live count. Generate disabled | Same copy | Small progress indicator |
| No material | status `no_material` | "This skill doesn't have course material yet." No retry button | Same | Muted, still openable for Lesson and Tutor |
| Error | status `error` | Treated as "Building, not usable" for students. Instructor sees the error | Same | Same |
| Exhausted | student has no unseen items | Sets still generate (repeats), banner from §7.3 | SRS handles it | Normal |

The Brief 1a "Preparing questions (x/y)" gate on a single set goes away. The wait (if any) moves to the skill level, before a set exists.

## 10. Build order (do not reorder)

**Step 0. Audit (no code).** Codex reports every generation call site, every hardcoded cap and token budget, and confirms the claims in this doc against the repo. Anything that disagrees gets resolved before Step 1.

**Step 1. Measure a batch call.** On real AWS101 chunks: 5 MCQs per call and 8 flashcards per call, 5 runs each. Record latency, `finish_reason`, output tokens, valid-item rate. This sets `max_tokens`, batch sizes, and concurrency. If batch latency is over 60 seconds, stop and reconsider batch size before building anything.

**Step 2. Migration 0021.** Schema in §3, including the `quiz_set_items` backfill. Apply before deploying anything that reads it.

**Step 3. Bank builder in shadow mode.** `bankBuild` runs and fills the bank. Nothing reads it yet. Old paths still serve students. Let it build AWS101 fully and sample 30 items by hand for quality.

**Step 4. Switch surfaces one at a time**, each behind a per-course flag `courses.bank_serving` (boolean, default false):
1. Flashcards (lowest risk)
2. Practice sets
3. Diagnostic
4. Lesson checks

Each switch is its own reviewable step with its own smoke check.

**Step 5. Retire the old paths.** Stop enqueuing to `item_generation_jobs`, cancel live rows, remove flashcard top-up generation, remove the frontend set-level generating poll. Leave the tables in place.

**Step 6. Frontend.** Bank status hook, the state table in §9, size picker on Test.

## 11. Open decisions for sign-off

1. ~~Kick the worker on demand.~~ **Approved 2026-10-06.** See §6.6. The IAM and env var change is explicitly authorized for this work.
2. **Starting targets** in §4. Approve as a starting point, tune after Step 3.
3. **Bank concurrency** of 2. Raise only after Step 1 shows provider headroom.
4. **Diagnostic items from the shared MCQ pool** rather than a separate diagnostic pool. Recommended: shared pool, with exposure tracking preventing a student from meeting the same question twice.
5. **Instructor "remove this question" button.** Retiring exists in the schema. The UI to trigger it is deferred unless you want it in this pass.

## 12. Measured versus assumed

Measured: the 30 second API wall, the 120 second worker ceiling, single-item latency (51 to 82s on `:floor` earlier, about 3 to 6s in the later Step 0 run), the corpus-depth repetition problem, `evidence_events` having no `item_id`, the `set_id` cascade.

Assumed until Step 1: batch latency, batch valid-item rate, the `max_tokens` a 5-item batch needs, and how many skills one worker run can build. Those numbers decide the constants. Nothing in §4 or §6 is final until they exist.
