-- =====================================================================
-- Kala — 0018_ingest_job_dedupe_and_backoff.sql
--
-- TWO INDEPENDENT FIXES, deliberately in one migration only because they
-- land together. They solve different problems and neither depends on the
-- other; read them as two changes, not one feature.
--
--   FIX A (seen)       — correctness: persisted cross-run dedupe of expanded
--                        containers. Stops a container reachable from two
--                        parents (or a malformed/cyclic tree) being expanded
--                        more than once ACROSS runs, which the existing
--                        run-local `queued` set cannot do.
--
--   FIX B (not_before) — liveness: a retry-after skip. Stops the walk
--                        re-attempting a job every 15 minutes against a fully
--                        exhausted Blackboard quota, spinning with zero net
--                        progress and never surfacing as failed.
--
-- A new migration rather than an edit to 0017: 0017 is already applied, so
-- editing it would leave the live schema and the file disagreeing.
--
-- APPLY THIS IN SUPABASE like every migration so far — this sandbox has no
-- linked Supabase CLI or DB password.
--
-- *** APPLY BEFORE DEPLOYING THE WORKER. THIS ONE IS ORDER-DEPENDENT. ***
--
-- 0016 was safe either way: the code around its new column fails OPEN (an
-- unmigrated column reads as "not found" and the caller falls back). This
-- migration is NOT. run()'s pickup query filters on `not_before` and selects
-- `seen`, and on a database without them PostgREST answers 400, db.select
-- raises, and run() propagates — ingest goes fully OFFLINE rather than
-- degrading. Verified by running the new run() against the live database
-- before applying this: it raised HTTPStatusError '400 Bad Request'.
--
-- So: apply 0018 first, then deploy the worker image. Reversing that order
-- breaks ingest for every institution until the migration lands.
-- =====================================================================


-- ---------------------------------------------------------------------
-- FIX A — persisted set of containers already expanded for this job.
--
-- WHY. ingest_walk keeps a run-local `queued` set so a container discovered
-- under two parents is expanded once *within a run*. That set is gone by the
-- next run, so a container re-discovered later is queued again. Today the
-- live AWS101 tree lists every container exactly once (measured: 72
-- containers, 0 duplicates), so this is LATENT rather than firing — but a
-- tree that lists a node under two parents, or any cycle in malformed data,
-- would make the walk expand and re-store the same subtree indefinitely.
--
-- jsonb array of container ids, same shape as `frontier` so the whole
-- checkpoint stays one atomic read/replace. NULL means "never walked".
--
-- BOUNDED GROWTH: this holds one id per container for the job's lifetime.
-- AWS101 has 72. A course with tens of thousands of containers would make
-- this a large jsonb value; if that ever becomes real, this becomes a
-- separate child table rather than one blob. Noted, not pre-built.
-- ---------------------------------------------------------------------
alter table public.ingest_jobs
  add column if not exists seen jsonb;

comment on column public.ingest_jobs.seen is
  'Container ids already expanded for this job, across runs. Complements the '
  'run-local dedupe in ingest_walk: that one prevents a double-expand WITHIN '
  'a run, this one prevents it ACROSS runs (two parents pointing at one '
  'container, or a cycle in malformed data). NULL = never walked.';


-- ---------------------------------------------------------------------
-- FIX B — do not re-attempt a throttled job until the window resets.
--
-- WHY. When Blackboard answers 429 the walk checkpoints what it has and
-- leaves the job in_progress, deliberately — a throttle is transient and
-- `failed` in this system means "never auto-retried, a human decides", so
-- failing the job would defeat the schedule-driven design.
--
-- But that leaves the pathological case the per-folder checkpoint cannot
-- fix: if the quota window is FULLY exhausted, every subsequent run gets 429
-- on its FIRST call, expands nothing, checkpoints nothing, and the next run
-- 15 minutes later repeats. Zero net progress, forever, until the window
-- resets — and nothing in the job row says why. Reproduced against the fixed
-- code: folders_expanded frozen across 4 consecutive runs.
--
-- So: record the throttle's own retry-after and skip pickup until it elapses.
-- Blackboard tells us exactly when to come back (`Retry-After: 20807s`), and
-- the connector already parses it. Use that signal rather than counting
-- consecutive zero-progress runs — a counter needs N occurrences to be
-- confident about something we are already told outright, AND flipping to
-- `failed` on it would be actively wrong, since failed never auto-retries.
--
-- NULL means "not throttled" — every job that has never been rate-limited,
-- which is why the pickup query treats NULL as eligible.
-- ---------------------------------------------------------------------
alter table public.ingest_jobs
  add column if not exists not_before timestamptz;

comment on column public.ingest_jobs.not_before is
  'Set to now() + Retry-After when a 429 is hit; the pickup query skips the '
  'job until this passes. NULL = not throttled. FIX B, independent of `seen`.';


-- ---------------------------------------------------------------------
-- Pickup index for the guarded query.
--
-- The worker's pickup becomes:
--   status IN ('pending','in_progress')
--   AND (not_before IS NULL OR not_before <= now())
--
-- The existing partial index (institution_id, created_at) WHERE status IN
-- (...) still narrows correctly — not_before is a cheap row filter on top of
-- a small candidate set, not something that needs its own index at pilot
-- scale. Left simple deliberately; revisit only if the candidate set grows.
-- ---------------------------------------------------------------------
create index if not exists ingest_jobs_not_before_idx
  on public.ingest_jobs (not_before)
  where status in ('pending','in_progress');


-- ---------------------------------------------------------------------
-- VERIFY after applying. Expect two rows, seen and not_before.
-- ---------------------------------------------------------------------
-- select column_name, data_type, is_nullable
--   from information_schema.columns
--  where table_schema = 'public' and table_name = 'ingest_jobs'
--    and column_name in ('seen', 'not_before');
