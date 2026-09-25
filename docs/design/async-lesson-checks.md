# Async guided-lesson comprehension checks — design

Status: proposed; awaiting sign-off before schema or route implementation.

## The problem, precisely

`GET /lessons/{course_id}/skill/{skill_id}` currently calls
`get_or_generate_lesson()`, which builds the outline, teaching content, and
comprehension checks before returning. `_build_step_payload()` calls
`item_gen.generate_question(kind="tutor")` once per step. An outline contains
3–6 steps, so a first lesson open can make 3–6 calls to the item-role model.
That model is the same structured-output DeepSeek path already moved off the
diagnostic and practice request paths; each call has measured 51–82 second
latency and the API Lambda has a 30-second request wall. The reported live
lesson requests returned HTTP 503 on the AWS101 course.

The slow call is not required to make a lesson useful. `_build_step_payload()`
already treats a missing check as a valid explanation-only step by leaving
`check_item_id` null. The existing client also accepts `check: null` and moves
to the next step when the student continues. The failure is therefore the
placement of check generation, not a requirement that a lesson be rejected
without checks.

## Proposed boundary

Keep these operations synchronous:

- RAG retrieval and provenance collection;
- the reasoning-tier outline call;
- per-step teaching content from the default/fast model;
- deterministic fallbacks for outline or teaching-content failures.

Persist the lesson and all teaching steps with `check_item_id = null`, mark the
lesson `ready`, and return it within the API request budget. For every persisted
step, enqueue one durable `item_generation_jobs` row with queue kind `lesson`.
The worker uses the existing item-generation implementation and writes the
generated `kind='tutor'` item, then updates that exact lesson step's
`check_item_id`. A later lesson GET assembles the check when it exists.

This keeps lesson generation course-level and shared, not per student. The
queue row is the durable work record; no SQS, Step Functions, or new scheduler
is required. Existing EventBridge worker runs drain it with the same two-call
concurrency cap, 90-second per-call cap, shared invocation budget, retry
backoff, and five-attempt terminal failure policy already approved for
diagnostic and practice generation.

## Queue schema decision

The current `0019_async_item_generation.sql` constraint only permits
`diagnostic` and `practice`, and its `set_id` column cannot identify a lesson
step. Widening only the kind check would leave the worker without a durable
step target, so the lesson extension should add a nullable `lesson_step_id`
foreign key to `guided_lesson_steps` with `on delete cascade`.

The resulting invariant should be enforced in SQL, not by route convention:

- `diagnostic`: `set_id IS NULL`, `lesson_step_id IS NULL`;
- `practice`: `set_id IS NOT NULL`, `lesson_step_id IS NULL`;
- `lesson`: `set_id IS NULL`, `lesson_step_id IS NOT NULL`.

Add `lesson` to the queue kind check, add a partial unique index on
`(institution_id, lesson_step_id)` where `kind = 'lesson'` and
`status IN ('pending', 'in_progress')`, and retain the tenant-scoped pickup
index on `(institution_id, next_attempt_at)` with the status predicate. The
existing diagnostic and practice partial unique indexes remain unchanged.

The enqueue path must insert the lesson step first, then enqueue against its
UUID. A second request or a retry after a worker kill therefore resolves the
same step row and cannot create a duplicate live check job. The queue row
still carries only operational state and `item_id`; it never carries prompt,
choices, `correct_choice_id`, or explanation.

`guided_lesson_steps` has no `institution_id` column of its own. Tenant
ownership exists only through `guided_lesson_steps.lesson_id ->
guided_lessons.institution_id`; that is also how the existing RLS read policy
proves ownership. The worker's completion update must therefore use a
tenant-scoped parent lookup before setting `check_item_id` (for example,
select the step joined through `guided_lessons` with both the step id and
institution id, then update the verified step id). A bare update filtered only
by `guided_lesson_steps.id` is not acceptable. The queue itself remains
default-deny under RLS, matching `0019`; only the service-role API and worker
write it.

## Route and client contract

The first lesson GET returns HTTP 200 with `status: "ready"` once outline and
teaching steps are persisted, even when some or all `check` values are null.
The response does not need a second lesson-level `checks_generating` status:
the existing step shape already makes an absent check distinguishable.

The current lesson viewer confirms the compatibility behavior:

- `lessonStepSchema` already allows `check: null`;
- while the lesson itself is `generating`, `useLesson` polls;
- once the lesson is ready, `LessonChat.openCheck()` treats a null check as an
  explanation-only step and advances;
- there is no current per-step loading or error indicator for a missing check.

Therefore the initial implementation should preserve this shipped behavior:
checks may appear on a subsequent GET, and a student may complete a step
without one. A visible “check coming” indicator is a follow-up product choice,
not a prerequisite for moving the expensive call off the request path. If the
product later requires a visible state, add an explicit step field or derived
queue status rather than guessing from a missing generated item.

## Lesson lifecycle and reclaim behavior

The current `_reclaim_for_regeneration()` deletes all steps whenever a lesson
row is `generating` or `failed`. That is safe for the current all-or-nothing
request generation, but it is wrong after checks become independent work:
`status='ready'` with null checks is a healthy lesson, not a stuck outline.

The implementation must change the reclaim boundary:

- only a missing lesson shell, or a lesson whose outline/content generation
  actually failed, may enter outline/content regeneration;
- a ready lesson is always assembled and returned, regardless of pending or
  failed check jobs;
- check-job failure must not change the lesson status or delete any step;
- an explicit future “regenerate lesson” operation may delete steps and their
  lesson queue rows, but an ordinary GET must not do so.

Because lesson checks are best-effort and the existing client already accepts
null checks, a terminally failed check remains an explanation-only step. The
queue row records the failure for operations and a later explicit re-open can
be added if the pilot needs recovery, but a normal lesson GET must not
re-trigger it or nuke the lesson.

## Worker ordering

`itemGeneration` remains before `tagBackfill`, after the existing prerequisite
jobs and readiness snapshot, so it shares the already-approved invocation
budget and skip behavior. Lesson rows use the same worker-side duplicate of
the item generator and the same RAG retrieval boundary as diagnostic/practice.
The worker claims at most two eligible rows across all kinds; if item work
claims the long-model slice, later slow jobs are reported as skipped exactly as
they are today.

No separate lesson-specific model path is needed. The worker calls the item
role with `kind='tutor'`, persists the generated item using the queue UUID as
the reconciliation identity, then updates the lesson step and marks the queue
row complete. If the worker dies after item persistence but before checkpoint,
the existing reconciliation lookup prevents a duplicate item.

## Rejected alternatives

**Keep checks synchronous and increase the API timeout.** This only moves the
30-second cliff and cannot accommodate 3–6 calls at 51–82 seconds.

**Queue the entire lesson.** This would unnecessarily delay the outline and
teaching content, which are fast and already have deterministic fallbacks. It
would also require a new lesson-level worker state and make the existing
explanation-only tolerance harder to use.

**Use `set_id` to store the lesson id.** That overloads a quiz-set foreign key,
weakens the database invariant, and makes tenant-safe lesson-step backfilling
less legible. A dedicated `lesson_step_id` expresses the actual ownership.

**Make the client poll until every check exists.** That would turn a useful
lesson back into an all-or-nothing experience and contradict the existing
`check: null` behavior. The lesson is ready when teaching content is ready;
checks are opportunistic enrichment.

## Verification required before implementation is complete

- A fresh lesson GET returns before the item-role latency wall with all steps
  present and null checks.
- The queue contains one lesson row per step, deduped under concurrent enqueue.
- A worker run moves at least one lesson row pending → complete and sets both
  `item_id` and the matching step `check_item_id`.
- A later lesson GET contains the completed check without exposing its answer
  key.
- No-content, transport failure, timeout, worker kill, stale reclaim, and
  five-attempt terminal failure leave the lesson steps intact.
- A ready lesson with pending or failed checks is never reclaimed or deleted.
- Tenant scoping and RLS prevent a lesson job from updating another
  institution’s step.

## Open decisions for sign-off

1. Approve the `lesson_step_id` queue extension and the three-way SQL kind
   invariant above.
2. Confirm the compatibility UX: null checks remain silently explanation-only
   for this pass; a visible per-step “check pending/failed” state is deferred.
3. Confirm that terminally failed checks remain explanation-only until a
   future explicit regeneration/re-open operation.
4. Confirm whether the existing 0019 migration may be amended by a follow-up
   migration (recommended) rather than editing an already-applied migration.

## Measured versus inferred

Measured/observed: the live lesson URL returned HTTP 503; the source call
chain contains one item-role generation per step; the item-role latency
benchmark is 51–82 seconds; and the current frontend accepts null checks.

Inferred for implementation: a dedicated `lesson_step_id` is the cleanest
queue key, and the existing item worker can backfill the step after item
success. Those should be covered by migration and worker tests before the
feature is enabled.
