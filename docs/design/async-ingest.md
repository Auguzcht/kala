# Async, checkpointed course ingest — design

Status: proposed scaffold, awaiting sign-off on table shape and job lifecycle
before the connector duplication and chunking wiring are finished.

## The problem, precisely

The old `POST /ingest` walked the whole Blackboard content tree synchronously
inside the api Lambda's 30-second wall, then stored + embedded inline. On the
real AWS101 course the walk **alone** measured 31.8s for ~40 sequential REST
calls — over the wall before a single PDF. Result: 8 invocations killed at
exactly 30000.00 ms, with no "Ingest pulled" log line ever printed, because the
request died before its own logging ran. Ingest for any non-trivial course was
silently broken.

Capping PDF fetches (built earlier this cycle) was correct but insufficient: it
caps the wrong thing. You cannot cap your way out of an operation that was
already over budget before the cap applied.

## Why "bigger timeout" is not the fix

Moving the walk to the worker's 120s ceiling would let AWS101 through, but a
course with ~3x the content walks past 120s too. Raising a timeout moves the
cliff to the next-bigger course. This system has already learned this lesson
once: tagging had the identical shape (a minutes-long batch on a 30s door) and
was fixed not by more time but by taking it off the request path entirely and
letting the worker drain it, with the database rows as the progress record.

## The design: same fix, applied to traversal

**Enqueue, don't walk.** `POST /ingest` writes one `ingest_jobs` row
(status=pending) and returns 202 immediately. It makes zero Blackboard calls,
so it is safe on the 30s wall by a wide margin and can never time out.

**Incremental, checkpointed walk on the worker.** A new `ingest_walk` worker
job picks up pending/in_progress jobs and advances each by a *bounded slice*:
pop up to N folders off the job's persisted frontier, fetch each folder's
children (one REST call each), store new content rows, append newly discovered
child folders to the frontier, checkpoint. Empty frontier => complete; else
in_progress, continued next scheduled run.

**The frontier is the cursor, and it lives in the database.** A killed worker
run loses at most the current un-checkpointed slice, which is simply
re-expanded next run — dedupe-by-lms_ref makes the re-store a no-op. No job
scheduler beyond the EventBridge cadence that already exists, no external queue.

**PDF fetch (Lead B) folds in.** The walk is now the code that both discovers a
document item and can fetch its short-lived signed href in the same pass — no
hand-off of an expiring URL, which was the exact reason the PDF fetch could not
live in the worker before. Bounded per run, same as folders.

## Why no SQS / Step Functions

The database already gives us a durable queue: pending rows are the backlog,
the frontier is the cursor, EventBridge already wakes the worker every 15
minutes. Adding SQS would be a second queue beside the one we already have in
Postgres. That earns its place only when multiple workers must pull
concurrently without colliding — which the pilot is nowhere near. Reaching for
it now is the over-engineering trap. Rows-as-queue is the right size.

## Credentials — no new AWS surface

The worker already runs under the same IAM role, already has
`secretsmanager:GetSecretValue` on the `kala/app` bundle, and already loads that
whole bundle (which already contains the `LMS_REST_*` and `LTI_AUTH_TOKEN_URL`
values the api uses) via `KALA_SECRETS_ARN`. The "worker has no LMS creds"
boundary was purely that the slim worker `config.py` did not *declare* the
fields and the image did not carry a connector. Spending that boundary costs a
config block and a duplicated connector — the same deliberate-duplicate pattern
already used for `embed.py` and `tagger.py`. No terraform change is required.
The security delta: the worker Lambda's environment now holds LMS credentials it
did not declare before, though it could already read them. Given the api peer
already holds them under the same role, this is a small increment, not a new
exposure class — but it is a conscious yes, recorded here.

## The `ingest_jobs` table

See migration `0017_ingest_jobs.sql`. Key columns:

- `status`: pending | in_progress | complete | failed
- `frontier` (jsonb): container ids not yet expanded — the cursor
- `folders_expanded` / `items_stored` / `pdfs_fetched`: observability
- `include_attachments`: carries the PDF gate from enqueue to worker
- `last_error`: set only on `failed`, for a human to inspect and re-enqueue
- partial unique index: at most one live (pending/in_progress) job per course,
  so a double-enqueue is a no-op, not a duplicate walk

## Failure semantics (carried from tag_backfill, do not simplify)

- **Rate limit (429):** transient by definition. Checkpoint what we have, leave
  the job in_progress, stop touching Blackboard this run, resume next run. Never
  loop against an exhausted quota. (This is the outage this whole cycle fixed —
  the walk must not re-create it.)
- **Real, non-transport error:** mark the job `failed` with `last_error` for a
  human. Never machine-retried.
- **Mid-slice kill:** the un-checkpointed folders are re-expanded next run;
  dedupe makes it safe.

## Rate-limit safety of a faster walk

First pass is deliberately serial and bounded (folders-per-run, pdfs-per-run),
same conservative posture as tagging. A bounded-concurrency pool over
`fetch_children` is the obvious later win (the walk is network-bound, ~0.8s per
call), but it is explicitly gated on proving quota headroom first — concurrency
that re-triggers the 429 outage would be a regression, not an optimization.

## Open decisions for sign-off

1. Table shape above — approve or adjust before the connector work is finished.
2. `_FOLDERS_PER_RUN` (20) and `_PDFS_PER_RUN` (5) — starting values; tune after
   the first live drain.
3. Chunking on the worker side: duplicate `chunk_text` + `strip_pii` into
   services/worker (the embed.py/tagger.py pattern), or move shared modules to
   packages/ (an infra change requiring a separate ask). Recommend the
   duplicate for now to stay inside the standing "no infra change unasked" rule.
