-- =====================================================================
-- Kala — 0020_async_lesson_checks.sql
-- Extend the durable item-generation queue to backfill guided-lesson checks.
-- Follow-up to 0019; do not edit the already-applied queue migration.
-- =====================================================================

alter table public.item_generation_jobs
  add column lesson_step_id uuid
    references public.guided_lesson_steps(id) on delete cascade;

alter table public.item_generation_jobs
  drop constraint if exists item_generation_jobs_kind_check;

alter table public.item_generation_jobs
  add constraint item_generation_jobs_kind_check
  check (kind in ('diagnostic', 'practice', 'lesson'));

alter table public.item_generation_jobs
  drop constraint if exists item_generation_jobs_set_kind_check;

-- The target column is explicit for every queue kind. In particular, a lesson
-- row never overloads quiz_sets.id and cannot be mistaken for a practice roll.
alter table public.item_generation_jobs
  add constraint item_generation_jobs_set_kind_check check (
    (kind = 'diagnostic' and set_id is null and lesson_step_id is null)
    or (kind = 'practice' and set_id is not null and lesson_step_id is null)
    or (kind = 'lesson' and set_id is null and lesson_step_id is not null)
  );

create index item_generation_jobs_lesson_step_idx
  on public.item_generation_jobs (institution_id, lesson_step_id)
  where kind = 'lesson';

create unique index item_generation_jobs_one_live_lesson_step
  on public.item_generation_jobs (institution_id, lesson_step_id)
  where kind = 'lesson'
    and status in ('pending', 'in_progress');

-- RLS and default-deny privileges are inherited from 0019. Queue rows remain
-- service-role operational state; clients receive only assembled lesson data.
