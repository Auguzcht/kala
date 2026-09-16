-- =====================================================================
-- Kala — 0012_quiz_sets.sql
-- Quiz sets: a generated batch of practice questions for one skill.
--
-- Why this exists. Until now practice generated exactly ONE item per request
-- (GET /practice/{course_id}/next), so a student answering N questions paid
-- N serial model round trips — the "~10s per question" wait. Flashcards and
-- the diagnostic already fan out one bounded batch via ai/concurrency's
-- map_concurrent; practice was the last serial path. A set is the missing
-- noun: the unit that endpoint returns, so the client can hold N items and
-- advance through them locally instead of round-tripping the model per card.
--
-- A set is DELIVERY grouping only, never a grading unit. Each item inside a
-- set is still a normal generated_items row with its answer key on the
-- server, graded one at a time through the untouched /practice/{course_id}/
-- submit path. Nothing about evidence, mastery, or the tracer changes.
--
-- skill_id is NOT NULL on purpose: every set this ships resolves to exactly
-- one skill (an explicit picker choice, or the weakest-skill fallback) before
-- generation. A nullable column for a field that is always populated would
-- only stop the schema telling the truth about what a set is. If cross-skill
-- sets ever become real (mirroring flashcards' cross-skill due-review), that
-- is a trivial one-line ALTER later, not a cost worth pre-paying now.
-- =====================================================================

create table public.quiz_sets (
  id                 uuid primary key default gen_random_uuid(),
  institution_id     uuid not null references public.institutions(id) on delete cascade,
  course_id          uuid not null references public.courses(id) on delete cascade,
  skill_id           uuid not null references public.skills(id) on delete cascade,
  -- Widened the same way generated_items.kind was in 0008: start with the
  -- one kind this ships ('practice') and let a later migration add more
  -- ('quiz', 'flashcard') without a reshape. A CHECK, not an enum, so the
  -- widening is a drop-and-add, matching the established pattern.
  kind               text not null check (kind in ('practice')),
  -- What the caller asked for. The actual persisted item count can be lower
  -- if a generation call degraded — recorded here so "asked for 5, got 3" is
  -- auditable rather than silently indistinguishable from a size-3 set.
  size               smallint not null check (size > 0),
  created_at         timestamptz not null default now()
);
create index quiz_sets_course_idx on public.quiz_sets (course_id, skill_id, created_at desc);

alter table public.quiz_sets enable row level security;

-- Staff-only read, exactly the generated_items shape from 0005 (items_read):
-- students never read generated content tables directly. They receive a
-- sanitized view through the API, which uses the service_role key and is the
-- only writer. No authenticated insert/update/delete policy on purpose.
create policy quiz_sets_read on public.quiz_sets for select to authenticated
  using (public.is_staff() and institution_id = public.current_institution());

grant select on public.quiz_sets to authenticated;


-- ---- generated_items: link each item to the set it was generated in ------
-- A nullable FK, not a join table: one item belongs to at most one set, and
-- this mirrors how srs_state.item_id already references generated_items
-- directly rather than through an association row. on delete cascade so
-- pruning a set removes the items that only exist because of it — the answer
-- keys go with them, which is correct (there is nothing to grade once the
-- set is gone). Nullable because every non-practice item (diagnostic,
-- flashcard, tutor checks) is generated outside any set and stays null.
alter table public.generated_items
  add column if not exists set_id uuid references public.quiz_sets(id) on delete cascade;

create index if not exists generated_items_set_idx
  on public.generated_items (set_id) where set_id is not null;
