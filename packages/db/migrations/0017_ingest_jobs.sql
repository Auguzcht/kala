-- 0017_ingest_jobs.sql
--
-- Async, checkpointed course ingest. Replaces the request-path tree walk that
-- ran inside the api Lambda's 30s wall and silently timed out at 30000.00 ms
-- on a real course (the AWS101 walk alone measured 31.8s for ~40 sequential
-- Blackboard REST calls, before any PDF fetch). Same architectural move that
-- fixed tagging: take a background batch OFF the request-response door and let
-- the worker drain it on its own schedule, with progress living in the
-- database so any killed run resumes from where it stopped.
--
-- This table is the JOB record. It deliberately does NOT hold the content --
-- content still lands in content_items exactly as before, and the existing
-- dedupe-by-lms_ref keeps a resumed walk from re-storing what it already
-- stored. What this table adds is:
--   1. an enqueue point the api can write in O(1) and return 202 immediately;
--   2. a lifecycle the worker can pick up, advance, and checkpoint;
--   3. a persisted FRONTIER, so an incremental walk that expands only some
--      folders per invocation knows which folders it has not reached yet.
--
-- APPLY THIS IN SUPABASE like every migration so far -- this sandbox has no
-- linked Supabase CLI or DB password.

create table public.ingest_jobs (
  id             uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  course_id      uuid not null references public.courses(id) on delete cascade,

  -- pending   : enqueued, no worker has started it
  -- in_progress: a worker has expanded at least one frontier slice; more remain
  -- complete  : the frontier is empty -- every folder was expanded
  -- failed    : a non-recoverable error (recorded in last_error); a human
  --             decides whether to re-enqueue. Transport blips do NOT land
  --             here -- they leave the job in_progress to be retried, mirroring
  --             tag_backfill's transport-vs-real-failure distinction.
  status         text not null default 'pending'
                 check (status in ('pending','in_progress','complete','failed')),

  -- The walk frontier. Blackboard content ids (text refs like "_449_1") whose
  -- children have NOT yet been fetched. The worker pops a bounded slice per
  -- run, fetches those folders' children, stores new content rows, appends any
  -- newly discovered child folders, and removes the ones it expanded. An empty
  -- frontier on a job that has started means "complete". NULL means "not yet
  -- seeded" -- the first worker touch seeds it with the course's top-level
  -- content ids. jsonb (not text[]) so the whole frontier is one atomic
  -- read/replace per checkpoint.
  frontier       jsonb,

  -- Observability, not control flow. Lets an operator (or the instructor
  -- dashboard) see progress without re-deriving it from content_items.
  folders_expanded int not null default 0,
  items_stored     int not null default 0,
  pdfs_fetched     int not null default 0,

  -- Set only when status='failed'. Human-readable, for a person deciding
  -- whether to re-enqueue -- not machine-retried.
  last_error     text,

  -- include_attachments carries the gate decision from the enqueue call
  -- through to the worker, so the worker fetches PDFs only for jobs that asked
  -- for it -- the same default-cheap contract get_content() already has.
  include_attachments boolean not null default false,

  created_at     timestamptz not null default now(),
  -- Advanced on every checkpoint. A stale started_at + in_progress is how a
  -- future stuck-job sweep would detect a job whose worker died mid-frontier
  -- (out of scope for the pilot -- noted, not built).
  started_at     timestamptz,
  updated_at     timestamptz not null default now(),
  finished_at    timestamptz
);

-- The worker's pickup query: oldest pending or in_progress job for a scope.
-- Partial index keeps it cheap -- complete/failed rows are the vast majority
-- over time and never need to be scanned for pickup.
create index ingest_jobs_pickup_idx on public.ingest_jobs (institution_id, created_at)
  where status in ('pending','in_progress');

-- At most one live job per course. A second enqueue while one is already
-- pending/in_progress is a no-op (the api returns the existing job), so a
-- double-click or a retry never spawns a duplicate walk against the quota.
-- Partial unique: a course can have many historical complete/failed jobs, but
-- only one live at a time.
create unique index ingest_jobs_one_live_per_course
  on public.ingest_jobs (course_id)
  where status in ('pending','in_progress');

-- RLS: default-deny like every other table (see 0002_rls.sql). The backend
-- uses the service_role key and bypasses RLS, so these govern only the
-- authenticated client path, defense in depth. A job row is course-scoped
-- operational state, so read is gated to staff who teach the course, matching
-- content_items' "staff only" posture. No client-side insert/update/delete
-- policy: only the backend (service_role) ever writes here.
alter table public.ingest_jobs enable row level security;

create policy ingest_jobs_read on public.ingest_jobs for select to authenticated
  using (
    public.teaches(course_id)
    or (public.is_admin() and institution_id = public.current_institution())
  );
