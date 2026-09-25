-- =====================================================================
-- Kala — 0019_async_item_generation.sql
-- Durable queue for diagnostic and batched practice item generation.
--
-- The API enqueues one row per requested item and returns before the slow,
-- structured-output model call. The worker claims pending rows, persists a
-- complete generated_items row, then marks the queue row complete. The queue
-- is operational state; it is never exposed directly to authenticated
-- clients. See docs/design/async-item-generation.md.
-- =====================================================================

create table public.item_generation_jobs (
  id                 uuid primary key default gen_random_uuid(),
  institution_id     uuid not null references public.institutions(id) on delete cascade,
  course_id          uuid not null references public.courses(id) on delete cascade,
  skill_id           uuid not null references public.skills(id) on delete cascade,
  kind               text not null check (kind in ('diagnostic', 'practice')),
  set_id             uuid references public.quiz_sets(id) on delete cascade,
  constraint item_generation_jobs_set_kind_check check (
    (kind = 'diagnostic' and set_id is null)
    or (kind = 'practice' and set_id is not null)
  ),
  context_offset     integer not null default 0 check (context_offset >= 0),
  status             text not null default 'pending'
                     check (status in ('pending', 'in_progress', 'complete', 'failed')),
  attempt_count      integer not null default 0 check (attempt_count >= 0),
  item_id            uuid references public.generated_items(id) on delete set null,
  last_error         text,
  next_attempt_at    timestamptz not null default now(),
  created_at         timestamptz not null default now(),
  started_at         timestamptz,
  updated_at         timestamptz not null default now(),
  finished_at        timestamptz
);

-- The worker picks only rows whose backoff has elapsed. Ordering by the same
-- column keeps newly eligible work ahead of later-created rows without
-- repeatedly claiming a row that is still cooling down.
create index item_generation_jobs_pickup_idx
  on public.item_generation_jobs (institution_id, next_attempt_at)
  where status in ('pending', 'in_progress');

-- A diagnostic question is shared course content: only one live request for a
-- course/skill may exist. Historical complete/failed rows are allowed, so an
-- explicit re-open can create a new live row later.
create unique index item_generation_jobs_one_live_diagnostic
  on public.item_generation_jobs (institution_id, course_id, skill_id)
  where kind = 'diagnostic'
    and status in ('pending', 'in_progress');

-- Practice offsets are unique within their quiz set. The kind predicate is
-- explicit even though set_id is null for diagnostic rows; it keeps the
-- invariant readable and prevents future kinds from accidentally sharing it.
create unique index item_generation_jobs_one_live_practice_offset
  on public.item_generation_jobs (institution_id, set_id, context_offset)
  where kind = 'practice'
    and status in ('pending', 'in_progress');

-- Operational queue state is default-deny. The API and worker use the
-- service_role key and bypass RLS; clients receive only sanitized,
-- tenant-scoped route responses. Do not grant direct table access: raw queue
-- rows would expose provider errors and retry timing.
alter table public.item_generation_jobs enable row level security;
revoke all on public.item_generation_jobs from anon, authenticated;
