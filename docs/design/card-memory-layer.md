# Card memory layer: adaptive review on top of the question bank

Status: Phases 0–5 deployed or verified on 2026-10-11. XP-only Phase 5 verification is complete.

Builds on: `docs/design/question-bank-design.md` (section 0 amendments win). This doc does not
change ingestion, bank building, or skill mastery.

### Changes from draft

- The shrinking deck is due tracked cards plus first-show/new-card seeding, not a membership
  listing. In legacy mode, top-up happens only for skills with no tracked card; in bank mode,
  the picker can add untracked bank cards. The deck still does not enumerate all live cards.
- `ensure_tracked` creates a row when a card is first served, before its first rating. An
  untouched membership listing can remain row-free, but the rule “rows are created on first
  review only” must change; `reps = 0` distinguishes shown-but-unreviewed cards.
- Graduation excludes a card from the normal due queue, not from the bank or a future membership
  view. Existing rows remain and the stats endpoint counts them as mastered.
- The original deck endpoint remains a session queue. A separate membership endpoint now lists all
  live cards for a skill, and the course memory summary reports per-skill counts.
- Existing practice submissions are repeatable and not idempotent. The current API performs
  several independent PostgREST writes, so the proposed atomic schedule/log/idempotency behavior
  needs a database RPC called through FastAPI with the service-role client.
- XP currently counts every evidence event. Preserve flashcard evidence for research; implement
  the “counted reviews only” reward by changing the XP derivation to use the review log, not by
  suppressing evidence events.
- The current flashcard endpoint still has a model-backed legacy fallback when bank serving is
  disabled (`flashcards.py`, lines 159–172). The question-bank section 0 removes click-time deck
  generation; the card-memory implementation must preserve the hard no-model-call study rule.
- The proposed state rule cannot use `due_at - last_reviewed_at` as the scheduled interval after
  early reviews. Under the Leitner design, derive interval from `box` and `ease_milli`; reassess
  storage if the later FSRS implementation needs a persisted scheduled interval.
- Current `srs.review` advances a successful rating even when a card is not due. “Early success
  does not advance” is therefore an intentional behavior change to the flashcard path, not a
  no-behavior-change wrapper; recommend retaining it as an explicit cramming rule.
- No live database was available for an `EXPLAIN` of proposed membership/summary queries. Keep
  query-plan validation as a pre-implementation check.

---

## 1. Summary

Kala already generates a fixed bank of MCQ items per skill at ingest time and serves Study and
Test from it with no model calls. What it lacks is a clear per-student memory model on top of
that bank.

This design adds a **card memory layer**: a per student, per item record of whether a card is
in memory right now, fed by both flashcard ratings and quiz answers, used to pick what each
study session serves.

It does **not** touch skill mastery. Skill mastery and card memory are two separate layers that
never write to each other.

Desired loop:

Generate once at ingest → store in the bank → study instantly → record recall → update the
card schedule → pick the next session from it → reinforce weak cards.

---

## 2. The bug that motivated this

The Study tab list for a skill can shrink after a student marks cards "Got it." The current deck
endpoint returns due tracked cards, then tops up from untracked cards. In bank mode those are
untracked bank items; in legacy mode generation/top-up is limited to skills without any tracked
card. A successful rating moves a card into the future, and a served card is tracked, so neither
is necessarily selected again for the current deck. The item remains in `generated_items`.

Root problem: a session queue is being used as a browse list. The browse list should show
**membership** (every eligible live card in the skill); scheduling should only decide **what a
session serves**. The original 20-to-15 reproduction is product context; the repository confirms
the selection mechanism, not that exact count or client list behavior.

Interim frontend copy fix already requested: "15 to review" instead of "15 cards."

---

## 3. Principles

1. **Content, membership, memory, scheduling, and session selection are separate concerns.**
   - Content: the items generated at ingest (`generated_items`).
   - Membership: which live items belong to a skill (`skill_id`, `retired_at is null`).
   - Memory: what this student knows about each item (`srs_state`).
   - Scheduling: when this student should see it again (`srs_state.due_at`).
   - Session selection: which items this session serves (computed per request).
2. **A student's progress never changes the bank.** Every live card stays available, including
   Known cards.
3. **Skill mastery is untouched.** `mastery_state` and its bands (No evidence, Developing,
   Proficient, Mastered) feed the instructor heatmap, at-risk flags, the twin, and readiness.
4. **Flashcard self-ratings never feed skill mastery.** Self-report is not assessment (existing
   rule, `routers/flashcards.py`).
5. **No model calls in any study path.** Scheduling is arithmetic on stored rows.
6. **Writes go through FastAPI with the service role.** The client never writes schedule fields.
7. **Items are never edited or hard deleted, only retired.** `srs_state.item_id` cascades on
   delete, so a hard delete would destroy student schedules.
8. **Missing data means New.** Membership reads do not need eager rows. The current deck creates a tracking row the first time it serves a card, before any rating; `reps = 0` means New for these shown-but-unreviewed cards.

---

## 4. Evidence base

The design leans on well-established learning research:

| Finding | What it means for Kala |
|---|---|
| Retrieval practice (testing effect) | A flip without a rating records nothing. Only recall attempts count. |
| Spacing | Successes on separate days matter more than repeats in one sitting. |
| Successive relearning | Practice a card until recalled once in a session (requeue on "Still learning"), then repeat across spaced sessions. Already shipped in the flashcard UI. |
| Interleaving | Shuffle within a session. Mixed order beats blocked order for retention. |
| FSRS scheduling | Models retrievability, stability, and difficulty per card. Default parameters outperform SM-2 for nearly all users in the public benchmark. Adopt later behind the scheduler interface (section 7). |

Gizmo publicly uses spaced repetition with XP, levels, leagues, streaks, and hearts. It does not
publish its scheduling rules or mastery thresholds. Nothing here is a copy of Gizmo internals.
Hearts are deliberately excluded: locking students out of study does not fit a school tool.

---

## 5. Two layers

| | Skill mastery (exists, unchanged) | Card memory (new) |
|---|---|---|
| Question | How well do you know this skill? | Is this card in your memory right now? |
| Grain | Per student, per skill | Per student, per item |
| Fed by | Graded evidence only (diagnostic, quiz, lesson checks) | Flashcard ratings and quiz answers |
| Storage | `mastery_state`, `evidence_events` | `srs_state`, new `item_reviews` |
| Seen by | Student and instructor | Student (instructor read later, optional) |
| Words | No evidence, Developing, Proficient, Mastered | New, Learning, Slipping, Known |

The two layers never write to each other. A quiz answer writes to both because both already
receive it, not because one derives from the other.

Card state words deliberately avoid "Mastered" so a student never sees a skill marked
"Proficient" next to cards marked "Mastered."

---

## 6. Card states

Derived on read from `srs_state`. Not stored as a separate column unless verification shows a
need.

| State | Rule |
|---|---|
| New | No `srs_state` row, or a row with zero counted reviews |
| Learning | Has been reviewed, last outcome was a success, scheduled interval under 21 days. Also a card missed before ever succeeding. |
| Slipping | Last outcome was a miss AND the card had at least one earlier success |
| Known | Last outcome was a success AND scheduled interval is 21 days or more |

21 days matches Anki's long-standing "mature card" convention. Intervals grow only across
separate days, so Known cannot be reached in one session. This satisfies "one correct answer
never establishes mastery" without a special rule.

Derivation needs the last outcome. `srs_state` has `streak`, `reps`, `lapses` but no last
outcome ([migration 0008, lines 51–76](../../packages/db/migrations/0008_learn_loop_v2.sql#L51)). Add one column:

| Column | Type | Notes |
|---|---|---|
| `last_outcome` | text, nullable, check in (`again`, `good`) | Backfill: `reps = 0` → null; `streak > 0` → `good`; `streak = 0 AND reps > 0` → `again`. In `srs.py`, only the miss branch resets streak; successful reviews increment it. |

Prior success exists when `reps - lapses > 0`: `reps` increments on every review and `lapses`
increments on misses ([srs.py, lines 94–120](../../services/api/app/learn/srs.py#L94)). This count cannot identify the last outcome by itself.

For the current Leitner scheduler, derive the scheduled interval from the box base interval and
`ease_milli` (the same calculation used by `srs.schedule_after`). Do not use `due_at -
last_reviewed_at`: an early review updates `last_reviewed_at` while leaving the due date unchanged,
which would distort the interval and state. If FSRS is adopted, decide whether to persist its
scheduled interval/state explicitly.

**Graduation must not hide cards from membership.** Current `due_cards` filters graduated cards out
of the normal queue; `stats` still counts them as mastered. They remain live generated items and can
appear in a membership view or explicit Study all. This preserves parking item #19 while keeping
normal review behavior.

---

## 7. Scheduler

### Interface

One module owns scheduling; put the interface in `app/learn/srs.py` or a sibling
`app/learn/scheduler.py` under `services/api/app/learn/` (current scheduler is
[`srs.py`](../../services/api/app/learn/srs.py)). Everything else calls it.

```
next_state(current_state, outcome, mode, was_due, reviewed_at) -> new_state
```

- `outcome`: `again` or `good`
- `mode`: `flashcard` or `quiz`
- `was_due`: whether the card was due at review time

### Now: keep Leitner

Keep the current Leitner interval math in `srs.py` behind the interface. Due/new flashcard
ratings keep the existing transition. The proposed early-success rule below intentionally changes
current behavior: `srs.review` presently advances every successful rating, due or not. Keep the
change explicit and cover it as a product rule for cramming:

| Situation | Effect |
|---|---|
| Success on a due or new card | Advance as today |
| Success on a card not yet due (early review) | Record the review, do not advance the box |
| Miss, any time | Lapse as today (box 0, due soon) |
| Quiz correct | Treated as a success, advances only if due (guessing risk on 4-choice MCQ) |
| Quiz wrong | Full lapse (objective failure) |

### Later: FSRS

Swap the implementation behind the interface to FSRS with default parameters. The `fsrs` package
is available on PyPI (current listed release 6.3.2) and the upstream [`py-fsrs` repository](https://github.com/open-spaced-repetition/py-fsrs) is MIT-licensed ([license](https://github.com/open-spaced-repetition/py-fsrs/blob/main/LICENSE)). It is not currently a project dependency. Recheck version and license at adoption. Two buttons map to FSRS Again and Good.
`item_reviews` (section 8) records everything FSRS needs from day one, so no data is lost by
deferring the swap. Migration seeds FSRS state from current boxes.

---

## 8. Data model

All additions in one migration. `0024_bank_saturation.sql` is the latest committed migration,
but the parallel shared-tree change already occupies `0025` with
`0025_reject_approved_skill_retire_bank_items.sql`; use `0026_card_memory.sql` for this design.
([migration directory](../../packages/db/migrations/)).

### 8.1 `srs_state` (extend)

| Change | Notes |
|---|---|
| Add `last_outcome` | Section 6 |

No other changes. PK stays (`user_id`, `item_id`), so a card has one schedule per student no
matter which view shows it.

### 8.2 `item_reviews` (new, append-only)

The per card review log. Separate from `evidence_events`, which stays the research dataset and
has no item id.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | |
| `institution_id` | uuid not null | Tenant |
| `user_id` | uuid not null | |
| `course_id` | uuid not null | |
| `skill_id` | uuid | Denormalized from the item |
| `item_id` | uuid not null, FK `generated_items`, on delete no action | Items are never hard deleted |
| `mode` | text, check in (`flashcard`, `quiz`) | |
| `outcome` | text, check in (`again`, `good`) | |
| `was_due` | boolean not null | |
| `counted` | boolean not null | False for early reviews and duplicates. Drives XP. |
| `elapsed_days` | numeric | Since the previous review. Null for first review. |
| `box_before`, `box_after` | smallint | Leitner snapshot |
| `due_before`, `due_after` | timestamptz | Schedule snapshot |
| `session_id` | uuid | Flashcard session id from the client, or the quiz set id |
| `idempotency_key` | text not null | Client generated per rating |
| `created_at` | timestamptz default now() | |

Constraints and indexes:

- Unique (`user_id`, `idempotency_key`)
- Index (`user_id`, `item_id`, `created_at`)
- Index (`course_id`, `created_at`)
- Append-only trigger: reuse `public.forbid_mutation()` like `evidence_events`

RLS: enable. Read policy: own rows, or `teaches(course_id)`, or admin in institution (same shape
as `quiz_set_attempts`). No authenticated write policy. Service role writes.

### 8.3 Unchanged

`generated_items`, `item_exposures`, `quiz_sets`, `quiz_set_items`, `quiz_set_attempts`,
`mastery_state`, `evidence_events`.

### 8.4 Related hardening (optional, separate commit)

`srs_state` read policy is institution-wide for staff (0008). Migration 0023 tightened other
learning tables to course scope. Consider the same for `srs_state` and `item_reviews`.

---

## 9. Write paths

### 9.1 Flashcard review: `POST /flashcards/{course_id}/review`

Current request is `{item_id, remembered: bool, latency_ms: int = 0}` ([flashcards.py,
lines 229–232](../../services/api/app/routers/flashcards.py#L229)). Add required
`idempotency_key`, `session_id`, and `outcome` (`again` or `good`); keep `remembered` as a
compatibility alias only during a deliberate API transition. The current response is
`remembered`, `graduated`, `dueInHours`, `box`, and a full `reward` summary
([flashcards.py, lines 284–292](../../services/api/app/routers/flashcards.py#L284)).

One transaction, implemented as a database RPC invoked by the FastAPI service-role client. The
current `db.select`/`insert`/`upsert` helpers issue separate PostgREST HTTP requests and cannot
provide `SELECT FOR UPDATE` or a multi-request transaction ([supabase.py, lines 18–80](../../services/api/app/db/supabase.py#L18)).


1. If a row with this (`user_id`, `idempotency_key`) exists, return its stored result. No change.
2. If this (`user_id`, `item_id`, `session_id`) already has a counted review, record it as
   `counted = false` and do not change the schedule (server-side guard for "first rating only").
3. Lock the `srs_state` row (select for update), compute `next_state`, write `srs_state`.
4. Insert `item_reviews`.
5. Always write the flashcard `evidence_events` row so the research export remains complete. XP
   must use counted `item_reviews` instead of counting flashcard evidence (section 12).

Response: new card state, due date, XP delta. Frontend already advances optimistically.

### 9.2 Quiz submit: `POST /practice/{course_id}/submit`

Existing behavior unchanged: grade server-side, write `evidence_events`, update `mastery_state`,
`item_exposures`, `quiz_set_attempts`.

Add, in the same transaction: card schedule update through `next_state` with `mode = quiz`, and
an `item_reviews` row with `session_id = set_id`. Today every valid resubmission is graded and
adds another evidence row and set-attempt count; there is no idempotency key or attempt number in
the request ([practice.py, lines 404–408 and 602–655](../../services/api/app/routers/practice.py#L404)).
Add a client-generated attempt/idempotency key; server-derived deduplication is impossible until
attempt identity exists.

### 9.3 Not wired in MVP

Diagnostic answers and lesson checks do not feed card memory yet (open decision 6).

---

## 10. Read paths

### 10.1 Membership: new endpoint

`GET /flashcards/{course_id}/skills/{skill_id}/cards`

Eligible items are bank MCQs (`origin = 'bank'`, `kind = 'practice'`) plus legacy flashcards
(`kind = 'flashcard'`) during cutover; filter by institution, course, skill, approved skill, and
`retired_at is null`. This follows question-bank section 0, A2/A9: tutor and diagnostic items must
not leak into Study. Left join the student's `srs_state`; do not create tracking rows from this
membership read. Current bank selection filters `origin='bank'`, `kind='practice'`, approved skill,
and live status ([serving.py, lines 17–29](../../services/api/app/bank/serving.py#L17)).

```json
{
  "skillId": "...",
  "counts": { "new": 10, "learning": 20, "slipping": 8, "known": 22, "dueToday": 14 },
  "cards": [
    {
      "itemId": "...",
      "prompt": "...",
      "back": { "label": "...", "explanation": "..." },
      "state": "learning",
      "due": true,
      "dueAt": "..."
    }
  ]
}
```

The four state counts always sum to the number of live cards. `dueToday` is separate and
overlaps them.

### 10.2 Session selection: existing deck endpoint

`GET /flashcards/{course_id}/deck?skill_id=&mode=review|all&limit=&offset=`

| Mode | Selection |
|---|---|
| `review` (default) | Slipping first, then due cards most overdue first, then New up to the daily new-card cap. New mode requests are capped at 20 cards per session. |
| `all` | Every eligible live card in stable shuffled order, in 20-card chunks selected with `offset`. Reviews are recorded as early reviews where not due. |

Omitting `mode` keeps the old due-first request and response contract; the old default size is 10.
The new-card cap is enforced atomically by `claim_study_cards`: no more than 20 cards first tracked
for one course during the institution-local day. The RPC serializes competing requests for the
same student, course, and local date.

`srs.ensure_tracked` keeps its current role for session selection (database only). The membership
endpoint must not call it. Today it creates a row on first serve, before review
([srs.py, lines 137–166](../../services/api/app/learn/srs.py#L137)); preserve `reps = 0` as New.

### 10.3 Due today

Store timestamps in UTC. `institutions.timezone` stores an explicit IANA time zone and the pilot
institution is seeded to `Asia/Manila`; do not hard-code that zone globally. Compute the
institution-local end-of-day boundary, then compare in UTC.

### 10.4 Course summary (phase 4)

`GET /courses/{course_id}/memory/summary`: read-only per-skill counts for New, Learning, Slipping,
Known, and due today. Missing schedule rows count as New.

---

## 11. Frontend

| Surface | Change |
|---|---|
| Study tab browse list | Uses membership. Shows every card with a state chip and due marker. Header counters New, Learning, Slipping, Known, Due today. |
| Study tab actions | Primary "Review due (N)". Secondary "Study all". Review due disabled with "All caught up" when N is 0. |
| Session | Unchanged one-tap grading, requeue, first-rating-only, slide transition. Passes `mode`, `session_id`, `idempotency_key`. |
| Card header | Replace "box 0" (jargon) with the card state chip. Skill band stays in the hub header, visually distinct. |
| Recap | Adds state movement: "3 cards moved to Known." |
| Test tab | Unchanged for MVP. |
| Skills page | Per skill memory summary (phase 4). |

Card state chips must look different from skill bands (different shape or icon), so the two
layers are never confused.

---

## 12. XP

Other assessment XP is derived from non-flashcard/non-practice `evidence_events`; counted card
reviews earn 10 points per good answer plus 2 per counted attempt. Flashcard evidence rows remain
in `evidence_events` for research and streak history, but do not add XP. `GET
/gamification/{course_id}/summary` exposes it. See
[`xp.py`, lines 62–82](../../services/api/app/learn/xp.py#L62) and
[`gamification.py`, lines 14–21](../../services/api/app/routers/gamification.py#L14).

MVP rule: **only reviews that count earn XP.** Counted means first rating of a card in a
session, on a due or new card, plus first quiz attempts. Requeued repeats and early reviews earn
nothing. Derive card XP from counted reviews in `item_reviews`, while leaving flashcard
`evidence_events` intact for research. `xp.summary` excludes flashcard and practice evidence so
those attempts cannot be counted twice; other event types keep the existing formula. This changes
XP semantics, not mastery or the evidence ledger. This rule is implemented and verified.

Deferred, needs a product decision: a course leaderboard. Constraints if built: course-scoped,
weekly reset, pseudonymous by default, opt-in to real names, instructor can switch it off. PDPA
applies.

---

## 13. Edge cases

| # | Case | Behavior | Enforced by |
|---|---|---|---|
| 1 | Flip without rating | Nothing recorded | Frontend posts only on rating |
| 2 | Lucky quiz guess | Success advances only if due. Known needs 21+ day interval, so one guess can't reach it. | Scheduler |
| 3 | Repeats in one session | First rating counts. Later ones `counted = false`, no schedule change. | Frontend + server guard 9.1 step 2 |
| 4 | Known card answered wrong | Lapse to Slipping, short interval | Scheduler |
| 5 | Review before due | Logged. Success doesn't advance. Miss counts. | Scheduler, `was_due` |
| 6 | Hundreds overdue | Review due serves most overdue first, capped per session | Session selection |
| 7 | Alternating flashcards and quiz | One schedule per card. Mode logged per review. | `srs_state` PK, `item_reviews.mode` |
| 8 | Broad skill tag | Skill bands unaffected. Card states are per card. | Two-layer rule |
| 9 | Multiple skill tags | Not applicable. One `skill_id` per item. | Schema |
| 10 | Item edited or regenerated | Items are never edited. Retired items leave sessions and counts. Replacements start New. No progress transfer. | `retired_at` filters |
| 11 | Student resets progress | Deferred. Study all covers cramming. | n/a |
| 12 | Two devices at once | Row lock on `srs_state` in the review transaction | 9.1 step 3 |
| 13 | Retry after network failure | Same idempotency key returns stored result | Unique constraint |
| 14 | Time zone change | Schedule stored in UTC. Due today uses institution timezone. | 10.3 |
| 15 | All due reviews done | "All caught up" with Study all offered | Frontend |
| 16 | Cramming before an exam | Study all, logged as early reviews | Mode `all` |
| 17 | Wrong AI answer key | Reporting from Study is deferred. Staff can still retire an item through the existing review process. | Deferred |
| 18 | Same card in different views | One schedule per student per item | PK |
| 19 | New user, thousands of cards | No eager rows. Missing row means New. Counts by aggregate query. | Read path |
| 20 | Retired item in history | `item_reviews` keeps it. Excluded from membership and counts. | FK no action, filters |

---

## 14. Phases

Each phase is local commits only. Nothing is pushed until the whole set is verified together.

### Phase 1: membership and states (fixes the bug)

- Migration: add `srs_state.last_outcome` and backfill exactly from `reps`/`streak`: `reps = 0`
  → `NULL`; `streak > 0` → `good`; `streak = 0 AND reps > 0` → `again`.
- Membership endpoint 10.1.
- Frontend browse list and counters.
- Acceptance: the list count equals live items in the skill and never changes as cards are
  rated. State counts sum to the total. Known cards remain listed.

### Phase 2: review log and scheduler interface

- `item_reviews` table, RLS, trigger.
- Scheduler interface wrapping Leitner with no change to existing flashcard outcomes.
- Flashcard review: idempotency, session guard, row lock, log.
- Acceptance: replaying the same review is a no-op. A second rating in one session doesn't move
  the schedule. Concurrent submits produce one schedule change. All existing srs tests pass.

### Phase 3: quiz feeds card memory

- Practice submit writes schedule and log.
- Acceptance: a wrong quiz answer turns a Known card into Slipping. A right answer on a not-due
  card doesn't advance it. Skill mastery results are identical before and after.

### Phase 4: session modes and summaries — deployed

- Review due and Study all, caps, institution-local due today.
- Course memory summary endpoint. The frontend Skills and Study views use the separate membership read.
- Acceptance: Review due serves Slipping, then most overdue, then New within the cap. Study all
  serves every live card in chunks. `make deploy` succeeded; live rollback testing of
  `claim_study_cards` admitted exactly 20 of 21 new cards.

### Phase 5: XP only — verified

- XP from counted `item_reviews` only; flashcard evidence remains available for research and is
  excluded from XP so it is not counted twice.
- "Report this card" is deferred. No reporting UI or endpoint is part of this phase.

### Deferred

FSRS swap, Practice weak skills across a course, leaderboard, progress reset, diagnostic and
lesson checks feeding card memory, due cards as a Test picking tier.

---

## 15. Accepted decisions

1. **Card state names accepted:** New, Learning, Slipping, Known.
2. **Known threshold accepted:** 21-day scheduled interval, derived from the Leitner box/ease calculation.
3. **Caps accepted:** 20 new cards per course per institution-local day and 20 cards per session.
4. **Quiz weighting and early-review behavior accepted:** correct advances only when due; wrong lapses. Early success records the review but leaves box/due unchanged, for quiz and Study all. This intentionally changes current early flashcard success behavior; existing mastery updates stay unchanged.
5. **Timezone accepted:** add `institutions.timezone`, seed the pilot institution to `Asia/Manila`, and use an explicit IANA zone per institution.
6. **Diagnostic and lesson-check answers deferred** from card memory; MVP inputs remain flashcard ratings and practice quiz submissions.
7. **Leaderboard deferred** pending a separate product/privacy decision.
8. **Instructor visibility deferred:** card memory remains student-only for MVP.
9. **Remove the model-backed flashcard fallback:** when bank serving is unavailable, return the existing no-material state; Study must never make a model call.

**Backfill correction accepted:** `reps = 0` → `last_outcome = NULL`; `streak > 0` → `good`; `streak = 0 AND reps > 0` → `again`. `srs.py` confirms streak increments on success and resets only on a miss (lines 101–113).

---

## 16. Verification checklist

- **Changed — deck selection explains the symptom, but the exact 20-to-15 count is not independently reproduced.** Due tracked cards are selected first and fresh items top them up; bank mode picks untracked bank cards, while legacy generation considers only untracked skills. A successful rating reschedules a card away from “due.” The endpoint is a session queue, not membership. [`flashcards.py`, lines 56–158](../../services/api/app/routers/flashcards.py#L56); [`srs.py`, lines 209–237](../../services/api/app/learn/srs.py#L209); [`serving.py`, lines 40–67](../../services/api/app/bank/serving.py#L40).
- **Changed and implemented — `srs_state` has `last_outcome`; PK remains (`user_id`, `item_id`).** Migration 0026 backfilled it exactly from `reps`/`streak`. [`0026_card_memory.sql`](../../packages/db/migrations/0026_card_memory.sql).
- **Changed and implemented — scheduler facts and state derivation.** Leitner base intervals are 4, 24, 72, 168, 384, and 840 hours before ease. Reviews increment `reps`; misses increment `lapses` and reset box/streak; graduation is box 5 with streak at least 3. Early successful reviews are recorded without advancing. Derive interval from box/ease. [`srs.py`](../../services/api/app/learn/srs.py); RPC migrations 0027–0028.
- **Changed — graduated cards are excluded from the normal due queue only.** `due_cards` filters them; `stats` counts them as mastered. They remain in the bank and should stay visible to membership/Study all. [`srs.py`, lines 209–266](../../services/api/app/learn/srs.py#L209).
- **Changed — `ensure_tracked` inserts on first serve, not membership listing or first review.** It is an idempotent select-then-insert and silently tolerates write failure. Keep membership reads side-effect-free; distinguish served/unreviewed rows with `reps = 0`. [`srs.py`, lines 137–166](../../services/api/app/learn/srs.py#L137); call site: [`flashcards.py`, lines 140–158](../../services/api/app/routers/flashcards.py#L140).
- **Changed and implemented — review contract.** Legacy `remembered` and `latency_ms` remain valid; optional `outcome`, `session_id`, `idempotency_key`, and `mode` are additive. Existing response fields remain. [`flashcards.py`](../../services/api/app/routers/flashcards.py).
- **Changed — practice resubmits are not deduplicated.** Body has `item_id`, `choice_id`, optional latency and `set_id`; each valid call writes evidence, applies mastery, increments set counters when set-scoped, and records exposure. Set membership is validated. [`practice.py`, lines 404–408 and 602–655](../../services/api/app/routers/practice.py#L404).
- **Changed and implemented — XP source.** Counted `item_reviews` award card XP; flashcard/practice evidence is excluded from that calculation and remains append-only for research. Tests cover the no-double-count rule. [`xp.py`](../../services/api/app/learn/xp.py); [`test_xp.py`](../../services/api/tests/test_xp.py).
- **Verified — mastery readers and write boundary.** Readers: [`twin.py`, lines 41–45](../../services/api/app/routers/twin.py#L41), [`dashboard.py`, lines 77–83](../../services/api/app/routers/dashboard.py#L77), [`items.py`, lines 477–481](../../services/api/app/learn/items.py#L477), [`readiness.py`, lines 8–16](../../services/api/app/twin/readiness.py#L8), [`summary.py`, lines 35–48](../../services/api/app/twin/summary.py#L35), [`cohort.py`, lines 140–147](../../services/api/app/twin/cohort.py#L140), and XP badges at [`xp.py`, lines 85–99](../../services/api/app/learn/xp.py#L85). Existing graded practice, diagnostic and lesson checks call `tracer.apply_evidence`; flashcard ratings do not. Card-memory changes must not change those assessment writes or add a mastery write to flashcard ratings. [`tracer.py`, lines 11–25](../../services/api/app/twin/tracer.py#L11); [`practice.py`, lines 648–665](../../services/api/app/routers/practice.py#L648); [`diagnostic.py`, lines 693–697](../../services/api/app/routers/diagnostic.py#L693); [`lessons.py`, lines 109–123](../../services/api/app/routers/lessons.py#L109); [`flashcards.py`, lines 271–283](../../services/api/app/routers/flashcards.py#L271).
- **Verified — Study filter and no-model constraint.** Bank selection uses `origin='bank'`, `kind='practice'`, approved skill and `retired_at is null`; question-bank section 0/A2 retains legacy `kind='flashcard'` during cutover. The model-backed fallback is removed. The endpoint preserves existing due cards, never generates on click, and returns additive `bankStatus: no_material` when bank serving is off. [`serving.py`, lines 17–29](../../services/api/app/bank/serving.py#L17); [`flashcards.py`, lines 128–200](../../services/api/app/routers/flashcards.py#L128); regression coverage: [`test_learn_routes.py`](../../services/api/tests/test_learn_routes.py).
- **Changed and implemented — migrations 0026–0029.** `last_outcome`, item reviews, review RPCs, and capped session tracking are present in [`packages/db/migrations`](../../packages/db/migrations/).
- **Changed and implemented — timezone.** `institutions.timezone` is seeded for the pilot, and due-today/daily-new calculations use its local date. [`0026_card_memory.sql`](../../packages/db/migrations/0026_card_memory.sql); [`flashcards.py`](../../services/api/app/routers/flashcards.py); [`courses.py`](../../services/api/app/routers/courses.py).
- **Verified — FSRS package and license.** `fsrs` is published on PyPI; upstream `py-fsrs` identifies the package and its repository license is MIT. It is not a dependency in this repository. [PyPI `fsrs`](https://pypi.org/project/fsrs/); [upstream repository](https://github.com/open-spaced-repetition/py-fsrs); [MIT license](https://github.com/open-spaced-repetition/py-fsrs/blob/main/LICENSE).
- **Blocked — EXPLAIN output.** Live timing and reads are available; no query-plan output was captured. Phase 1 membership timing on the largest AWS101 skill (21 cards) was 2.98s cold, then 525ms and 382ms warm. No index change was made from timing alone.
