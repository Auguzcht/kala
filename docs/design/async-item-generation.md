# Async item generation — design

Move diagnostic and batched practice question generation out of the API
request path. This is a design for sign-off; it deliberately contains no
implementation changes. The implementation pass must not begin until the
schema, worker budget, and response contracts below are approved.

## The problem, precisely

`app.learn.items.generate_question()` does four expensive things in one
request: RAG retrieval, a structured-output item call, validation (with one
bounded validation retry), and persistence of the answer key. The item model
role is currently DeepSeek because it is the only measured model that accepts
the strict structured-output schema. The live benchmark in
`docs/bugs/model-latency-and-capability-benchmark.md` measured one item call at
51.2–81.7 seconds on real input.

Two API callers put that call behind API Gateway/Lambda's 30-second ceiling:

* `GET /courses/{course_id}/diagnostic` generates one diagnostic item for each
  approved skill that has no course-wide diagnostic item. It uses
  `map_concurrent_partial`, so a cold ten-skill bank launches ten calls at
  once, but concurrency does not help the request survive the 30-second wall.
* `POST /practice/{course_id}/set` creates a `quiz_sets` row and launches one
  call per roll for one skill. The default is five and the maximum is ten.
  Each roll carries its `context_offset` into `_rotated_context()` so a batch
  is not grounded in the same leading chunk.

The existing partial-tolerance fixes make these paths less brittle, but they
cannot make a 51–82 second call fit inside a 30-second request. A cold bank
therefore returns a diagnostic 503, and practice generation has the same
long-parked timeout failure.

## Why a larger timeout is not the fix

The API Lambda timeout is 30 seconds in `infra/terraform/lambda.tf`; the
worker Lambda timeout is 120 seconds. The worker is the established place for
unbounded, resumable work: rows are the durable queue, the job processes a
bounded slice, and the next scheduled run resumes it. No SQS, Step Functions,
new Lambda, or EventBridge target is proposed here.

The item queue follows the same philosophy as `ingest_jobs` and the
`content_items` progress fields. A request only validates input and enqueues
work. The worker owns model calls and writes complete `generated_items` rows.

## Measurements — worker budget is shared

The worker currently runs five jobs sequentially in one 120-second invocation:

1. `reconcileMastery`
2. `ingestWalk`
3. `embedBackfill`
4. `tagBackfill`
5. `readinessSnapshot`

The timeout is confirmed by `infra/terraform/lambda.tf`, not inferred from a
comment. I queried `/aws/lambda/kala-worker` CloudWatch logs for the most recent
24 hours available on 2026-09-25. There were 96 complete invocations, and the
logged job durations were:

| job | count | average | observed range |
|---|---:|---:|---:|
| `reconcileMastery` | 96 | 1,449.7 ms | 1,247–1,930 ms |
| `ingestWalk` | 96 | 90.5 ms | 63–172 ms |
| `embedBackfill` | 96 | 98.0 ms | 70–149 ms |
| `readinessSnapshot` | 96 | 210.5 ms | 141–334 ms |
| **the four jobs excluding tag** | — | **1,848.7 ms** | **2,585 ms if each observed max is combined** |

That is roughly 118.15 seconds of typical budget, or 117.42 seconds using
the sum of the four observed maxima, before adding an item call. The normal
24-hour `tagBackfill` average was only 131.4 ms (81–320 ms), but that is not a
safe budget assumption. The wider 48-hour log sample contained tag runs at
61,143 ms and 72,773 ms, with the corresponding whole invocations spending
roughly 70 seconds in tag backfill. `ingestWalk` and `embedBackfill` also had
historical backlog-drain outliers of 7,158 ms and 5,003 ms.

The conclusion is not “there is room for a sixth job.” There is room for one
bounded item-generation slice only when the worker gives it scheduling
priority and does not then blindly start a potentially 73-second tag call.

## Sequential versus concurrent generation

Sequential generation is technically safe but operationally too slow:

* one item per run means a five-item practice set takes five 15-minute
  schedules, with a worst-case wait of about 75 minutes if the request arrives
  just after a scheduled run;
* one diagnostic with ten missing skills takes up to ten runs, and a student
  sees a moving or incomplete baseline for hours;
* the worker's other jobs consume only about 1.85 seconds in a normal run, so
  the bottleneck is model latency, not database bookkeeping.

The proposed generation slice uses a small `ThreadPoolExecutor` over the
existing synchronous HTTP/model path, with **at most two item calls in
flight**. Two calls have the same wall-clock shape as one call: approximately
51–82 seconds, plus RAG/database overhead, rather than 102–164 seconds
serially. With a conservative 100-second item-job budget, two calls fit inside
the measured 117.42-second four-job ceiling and leave approximately 17 seconds
of invocation reserve in the worst measured non-tag case.

For a five-item practice set, this drains two, two, then one item: three
scheduled runs, or roughly 45 minutes worst case. A sequential design drains
one per run and is not acceptable for the practice-session contract. A larger
pool is rejected for now: the benchmark does not measure provider behavior
under three or more simultaneous structured-output calls, and the worker must
not turn the current request timeout into a provider-throttling problem.

The 100-second item-job budget is a design guard, not a new Lambda timeout. A
call that has not completed by the worker's client timeout remains pending for
retry; a worker invocation must not start another call after its item budget is
exhausted.

## Worker ordering and contention

Item generation needs embedded course content for RAG, so it cannot run before
`ingestWalk` and `embedBackfill`. This is the same dependency that put
`ingestWalk` before embedding: the producer must run before the consumer.
Item generation does not depend on tagging; the generator retrieves content by
skill and only needs approved skills plus embeddings.

The proposed logical order is:

1. `reconcileMastery`
2. `ingestWalk`
3. `embedBackfill`
4. `readinessSnapshot`
5. `itemGeneration` — bounded two-call slice
6. `tagBackfill` — only when the item slice did not claim the invocation

The important part is the scheduling rule, not merely the list: when pending
item work exists, item generation gets the long-model slot and tag backfill is
skipped for that invocation. When no item work exists, tag backfill retains its
existing opportunity to drain. This prevents a 61–73 second tag run from
consuming the headroom needed by an 82-second item call, and prevents the
handler from starting a sixth unbounded job after the other five.

The implementation must make the skip visible in the result/logs (for
example, `tagBackfill: skipped_item_generation`) rather than making it look
like a successful empty tag run. A future scheduling change can revisit fair
sharing after real item and tag queue data exists; this design does not add
parallel item and tag model calls in the same invocation.

The exact placement of the readiness snapshot is not correctness-critical; it
is before item generation here so a long item slice cannot suppress the cheap
nightly snapshot. If the current handler's error-isolation structure makes
that reorder undesirable, the implementation may retain readiness last only
if it also adds a remaining-budget guard. That is an implementation decision
to confirm before coding.

## Durable queue schema

Add a migration for a small `item_generation_jobs` table. It is a queue of
individual requested items, not a second copy of `generated_items` and not an
SQS replacement.

Suggested columns:

```text
id                 uuid primary key default gen_random_uuid()
institution_id     uuid not null references institutions(id) on delete cascade
course_id          uuid not null references courses(id) on delete cascade
skill_id           uuid not null references skills(id) on delete cascade
kind               text not null check (kind in ('diagnostic','practice'))
set_id             uuid null references quiz_sets(id) on delete cascade
context_offset     integer not null default 0 check (context_offset >= 0)
status             text not null default 'pending'
                   check (status in ('pending','in_progress','complete','failed'))
attempt_count      integer not null default 0 check (attempt_count >= 0)
item_id            uuid null references generated_items(id) on delete set null
last_error         text null
next_attempt_at    timestamptz not null default now()
created_at         timestamptz not null default now()
started_at         timestamptz null
updated_at         timestamptz not null default now()
finished_at        timestamptz null
```

`item_id` is set only after `generate_question()` has successfully persisted
the complete item. The queue row is then marked `complete`. The answer key
never lives in the queue, and a failed/in-progress row never masquerades as a
client-visible generated item.

Indexes and deduplication:

* pickup index on `(institution_id, next_attempt_at)` where status is `pending`
  or `in_progress`; the worker pickup query must include
  `next_attempt_at <= now()` and order by `next_attempt_at`, so backed-off rows
  are not repeatedly claimed during their cooldown;
* partial unique index on `(institution_id, course_id, skill_id)` where
  `kind = 'diagnostic'` and `status in ('pending','in_progress')`, so two
  diagnostic GETs cannot enqueue two questions for the same course/skill;
* partial unique index on `(institution_id, set_id, context_offset)` where
  `kind = 'practice'` and `status in ('pending','in_progress')`, so a retry
  that is re-enqueuing work for the same set cannot duplicate a roll;

### RLS and grants

The queue is operational state, not a client-readable content table. The
migration must enable RLS and leave it default-deny for authenticated clients:

```sql
alter table public.item_generation_jobs enable row level security;

-- No authenticated SELECT/INSERT/UPDATE/DELETE policies. The API and worker
-- use the service_role key and bypass RLS; clients see queue state only
-- through the tenant- and course-scoped API response contracts above.
revoke all on public.item_generation_jobs from anon, authenticated;
```

The migration should also grant no table privileges to `anon` or
`authenticated`. This is deliberate: exposing raw queue rows would leak
provider errors, skill/course operational details, and retry timing. The API
response is the policy boundary. The table still carries `institution_id`, and
every service-role query must filter it explicitly; service-role bypassing RLS
is not permission to omit tenant predicates.

The practice index does not deduplicate two independent POST requests, because
the current endpoint has no idempotency key and each POST intentionally creates
a new `quiz_sets` grouping. Whether a later client-generated idempotency key is
worth adding is backlog work, not part of this pass.

The diagnostic enqueue must be an atomic insert-or-existing operation backed by
the unique index. “Select, then insert” is not sufficient: two simultaneous
GETs can both observe the missing item. The route should read existing
`generated_items`, read live queue rows, and enqueue only the remaining skill
ids; a uniqueness conflict is treated as “already pending,” not a 500.

Terminal diagnostic failures are not reopened by a later GET. The route reports
the failed skill until an explicit re-open mechanism is added as follow-up
work; this pass does not add that endpoint.

For practice, the route first creates the `quiz_sets` row with the requested
size, then inserts one queue row per offset `0..size-1`, each carrying the same
`set_id`, skill, kind, and its own `context_offset`. A queue insert conflict
for an existing `(set_id, context_offset)` is likewise an idempotent success.

## Queue failure semantics

The worker should preserve the distinctions already used by `tag_backfill`,
with an explicit retry/budget policy:

* successful model output and persistence → `complete`, `item_id` set;
* the item job has a **100-second wall-clock budget** per invocation. The two
  selected rows are claimed before model calls begin. Each synchronous HTTP
  call gets a timeout no greater than 90 seconds and is capped by the remaining
  item-job deadline, leaving time for Supabase writes and queue checkpointing;
* a transport/provider timeout or provider error never gets an immediate
  second call in the same invocation. It increments `attempt_count`, stores a
  sanitized `last_error`, sets `status='pending'`, and sets
  `next_attempt_at` using 15m, 30m, 60m, 120m, then 240m backoff. After five
  scheduled attempts it becomes `failed` and waits for an explicit re-open;
* a validation/structured-output failure may get **one immediate validation
  reroll only when at least 85 seconds remain** in the 100-second item budget.
  Otherwise it follows the same pending/backoff path without spending another
  long call. With the measured 51–82 second latency, the normal case will not
  have enough remaining budget for an immediate reroll; that is intentional.
  The next scheduled attempt is the retry. No validation reroll may start once
  the deadline guard fails;
* no retrievable course content is also retryable, not terminal immediately:
  ingest may still be catching up. It follows the same five-attempt backoff
  policy and becomes `failed` only after the queue has had those chances;
* a worker kill between model persistence and queue update must be safe. The
  implementation must reconcile a queue row with an already-created item, or
  use an idempotent lookup before retrying, so a Lambda timeout cannot create
  duplicate diagnostic items or duplicate practice offsets.

Unlike tagging, “no match” is not a valid successful result here: every item
request must either produce a valid MCQ or retain an actionable failure state.
The API should not expose raw provider errors to students; it should expose a
stable generation-failed status and log the detailed error server-side.

The queue must be tenant-scoped in every query. The worker uses the service
role, but `institution_id` remains part of the row and every route lookup.

The job must stop claiming new rows when its 100-second deadline is reached.
Rows not yet claimed remain `pending`; a claimed row whose call timed out is
returned to `pending` with backoff. The handler must record the budget stop in
the job result/log, rather than letting the Lambda's 120-second hard kill be
the checkpoint mechanism.

## Route contracts

These are proposed response contracts for the second pass. They are
intentionally explicit because the current frontend schemas assume complete,
immutable responses.

### `GET /courses/{course_id}/diagnostic`

The request remains a read-shaped route, but it may enqueue missing shared
course items as an idempotent side effect. It returns HTTP 200 in all normal
generation states:

```json
{
  "courseId": "…",
  "status": "generating",
  "questions": [],
  "pendingSkillIds": ["skill-a", "skill-b"],
  "failedSkillIds": [],
  "skippedSkillCount": 0
}
```

When some items already exist, `questions` contains those ready questions in
skill order and the status is still `generating`. When all requested skills
have an item, the response is:

```json
{
  "courseId": "…",
  "status": "ready",
  "questions": ["…"],
  "pendingSkillIds": [],
  "failedSkillIds": [],
  "skippedSkillCount": 0
}
```

If a request has terminal failures but at least one ready question, the
response remains `status: "ready"`, with `failedSkillIds` and any ready
questions. The frontend can surface “9 of 10 ready; one skill has no material
yet” without hiding the usable baseline. Only `readyCount == 0` returns
`status: "failed"`. The existing `skippedSkillCount` can remain for the old
partial-tolerance meaning only if the frontend distinguishes it from queue
failure; otherwise it should be replaced by the explicit lists.

The frontend work required in the implementation pass is real, not a
bolt-on: extend the Zod schema, make `useDiagnostic` poll while status is
`generating`, stop polling on `ready`/`failed`, and render a waiting state that
does not offer submission until all questions are present. The diagnostic due
check can remain a cheap evidence read; it must not become a generation poll.

### `POST /practice/{course_id}/set`

The route creates the set and queue rows, then returns immediately with HTTP
202 (recommended) and no generated item requirement:

```json
{
  "courseId": "…",
  "setId": "…",
  "status": "generating",
  "skillId": "…",
  "requestedSize": 5,
  "readyCount": 0,
  "pendingCount": 5,
  "failedCount": 0,
  "items": []
}
```

If a future enqueue race finds already-complete rows for the same set, the
counts and items reflect reality. The route must never return `setId: null`
for a valid skill merely because generation has not finished; `null` remains
reserved for the existing “no approved skill” branch.

The current `usePracticeSet` contract must change from “immutable complete
query” to “poll a set until ready.” Specifically, the implementation pass must
remove `staleTime: Infinity` for the generating state, poll the set detail
endpoint, keep the set id stable, and only enter the answerable session when
the required readiness policy is met. The set becomes enterable once every
offset is resolved (`complete` or `failed`). `readyCount` is the playable
count and may be lower than `requestedSize`; if `readyCount` is zero, the
response is `status: "failed"` and the UI does not enter the session.

### `GET /practice/{course_id}/sets/{set_id}`

This is the natural poll target and should return HTTP 200 while work is in
flight:

```json
{
  "courseId": "…",
  "setId": "…",
  "skillId": "…",
  "kind": "practice",
  "status": "generating",
  "requestedSize": 5,
  "readyCount": 2,
  "pendingCount": 3,
  "failedCount": 0,
  "items": ["two sanitized ready items"]
}
```

When all requested offsets resolve, `status` is `ready` if `readyCount` is
greater than zero, or `failed` if it is zero. A partial terminal failure
returns `status: "ready"`, counts, ready items, and stable failure metadata
such as failed offsets—not provider internals; the frontend may enter with the
playable items. The answer key remains server-side in every state.

The saved-set Zod schema, the test browser, `PracticePanel`, and the set list
will need status/count fields in the implementation pass. A partially
generated set must not be presented as an immutable retake until every offset
has resolved; a partially successful set is then a ready, playable set.

## Explicit exemptions

The study-to-test bridge remains synchronous:

* `POST /practice/{course_id}/set/from-items` only selects already-generated
  items, creates a `quiz_sets` grouping, and attaches `set_id`; it makes no
  model call and should remain exactly as it is.
* `GET /practice/{course_id}/next` remains the single-item path and is not
  part of this migration. The source comment says it is retained for the
  single-item loop, but the current frontend grep shows no component calling
  `useNextPracticeItem`; the hook and API function are only exported/defined.
  `PracticePanel` uses `usePracticeSet`, not `/next`. No async queue behavior
  should be introduced there in this pass.

The bridge is actively called by `FlashcardDeck` through
`useCreateSetFromItems`, which confirms why it must not be changed. The
`/next` endpoint is covered by backend tests and remains a compatibility path,
but it has no current UI caller.

### Flashcards are explicitly out of Piece 2

Flashcards are not added to `item_generation_jobs` and do not become a third
async caller in this pass. `GET /flashcards/{course_id}/deck` currently tops
up fresh cards by calling `generate_question(kind="flashcard")` for up to the
visible deck limit, then immediately calls `srs.ensure_tracked()` and returns
the card backs. Moving that path asynchronously would require a separate
per-student queue contract: the generated item is coupled to `srs_state`, the
deck is due-first and user-specific, and the endpoint currently returns cards
plus scheduling state in one response. It is a different product contract
from course-shared diagnostic items and practice `quiz_sets`.

For Piece 2, flashcards therefore remain unchanged and retain their existing
request-path behavior. This is a deliberate scope boundary, not an assertion
that their generation cost is harmless. If flashcard top-up reaches the same
30-second wall, it gets a separately designed queue that includes the student
and SRS handoff; it must not reuse this course/skill item queue by accident.

## Worker implementation shape (second pass)

The worker image cannot import `services/api/app`; its Dockerfile copies only
the worker `app` tree. The implementation should therefore use the same
deliberate trimmed-duplicate pattern as `tag_backfill.py` + `tagger.py`:

* add a worker-side item-generation module containing only the RAG retrieval,
  context rotation, item-role call, validation, and persistence needed by the
  job;
* keep the prompt, strict response schema, 2,048-token budget, banned-stem
  validation, and bounded validation retry aligned with
  `services/api/app/learn/items.py`;
* add a worker queue job that selects bounded pending rows, claims them, runs
  at most two synchronous calls concurrently, writes complete items, and
  updates queue state;
* add the API-side enqueue/read logic and the migration separately;
* add tests for atomic dedupe, retry/timeout behavior, context offsets,
  partial set reads, and no answer-key leakage.

The worker duplicate is intentional under the repository's standing
no-infrastructure-change constraint. If either item-generation implementation
changes later, both trees must be searched and updated together.

## Rejected alternatives

### Keep fan-out in the API and raise the client timeout

Rejected. API Gateway/Lambda still kills the request at 30 seconds, and a
larger frontend timeout cannot change that platform ceiling.

### Generate sequentially in the worker

Rejected as the primary design. It is simple and safe, but a five-item set
would take five 15-minute runs (up to 75 minutes), and a ten-skill diagnostic
could take ten runs. The measured non-model overhead does not justify that
student-facing wait.

### Run item generation concurrently with tag backfill

Rejected. Historical tag runs consumed 61–73 seconds, leaving too little room
for an item call at the measured 51–82 seconds. It also increases provider
load exactly when tagging is already slow. The worker should alternate queue
ownership, not make two unbounded model workloads compete.

### Add SQS, Step Functions, or another AWS queue

Rejected for this pass. The database queue is sufficient for the pilot,
matches `ingest_jobs`, and avoids an infrastructure/hosting change that was
not requested.

### Put pending placeholders in `generated_items`

Rejected. A placeholder would have to violate the generated-item contract or
make every reader understand incomplete prompts/choices. The queue row keeps
generation state separate and only links a fully persisted item through
`item_id`.

### Move only diagnostic generation and leave practice synchronous

Rejected. Both callers invoke the same slow item role, and the practice
timeout is the same 30-second-wall failure. Splitting the fix would preserve a
known outage in the main practice session.

### Switch item generation to ling-3.0

Rejected by the measured benchmark. Ling returned HTTP 400 because the
provider does not support the strict structured-output response format used by
the item role.

## Approved decisions for implementation

The following decisions are signed off for the implementation pass:

1. `item_generation_jobs` uses the schema, tenant-scoped unique indexes, and
   default-deny RLS/grants above. The pickup index is keyed by
   `next_attempt_at`, and pickup filters `next_attempt_at <= now()`.
2. A practice set becomes enterable once every offset is resolved, whether
   complete or failed. `readyCount` may be lower than `requestedSize`; zero
   ready items means `status: "failed"` and nothing is playable.
3. Diagnostic terminal failures are not automatically reopened by GET. No
   retry endpoint is added in this pass; explicit re-open is follow-up work.
4. No client idempotency key is added now. Deduplication remains per
   `(set_id, context_offset)`; broader POST idempotency is backlog work.
5. The concurrency cap is two item calls.
6. `itemGeneration` runs before `tagBackfill`; tagging is skipped and the skip
   is visible in the job result whenever item generation claims the long-model
   slot.
7. Both generation GET routes return HTTP 200 while `status: "generating"`.
   Frontend polling uses a 4–6 second interval, to be selected within that
   range during implementation.
8. Status names are `generating`, `ready`, and `failed`, with
   `requestedSize`, `readyCount`, `pendingCount`, and `failedCount`.

## Measured versus assumed

Measured here:

* item latency range: 51.2–81.7 seconds from the real-input benchmark;
* worker timeout: 120 seconds from Terraform;
* CloudWatch job durations were queried live from the
  `/aws/lambda/kala-worker` log group through the AWS Logs API on 2026-09-25,
  not reconstructed from repository code or inferred from the Terraform
  timeout;
* recent 24-hour job counts, averages, and ranges from CloudWatch;
* historical tag/ingest/embed outliers from the same worker log sample;
* route callers and the fact that the bridge is used by `FlashcardDeck` while
  the `/next` hook currently has no component caller;
* flashcard's current synchronous `generate_question(kind="flashcard")` plus
  immediate SRS tracking path;
* item generation's `context_offset` and diagnostic/practice behavior from the
  full source files requested for this design.

Still assumptions requiring verification during implementation:

* two simultaneous item calls will remain within the provider's rate and
  structured-output limits;
* a 100-second job budget leaves enough time for Supabase writes and clean
  queue checkpointing under all cold-start conditions;
* the proposed worker-side duplicate can faithfully use the API's RAG and
  model helpers without a shared-package change;
* the exact safe transaction/idempotency strategy for a model-success followed
  by a Lambda kill;
* whether the existing database connection and model client are safe to use
  from two worker threads at once.

Those are implementation/test gates, not facts this design should pretend to
have measured already.
