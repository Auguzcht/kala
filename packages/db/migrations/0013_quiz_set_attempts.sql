-- =====================================================================
-- Kala — 0013_quiz_set_attempts.sql
-- Per-student attempt tracking for shared quiz sets.
--
-- quiz_sets (0012) is shared course content, like generated_items and
-- content_items before it: one set generated for a skill can be taken by
-- any student in the course, same content, same answer key, no
-- regeneration cost per student. That's correct, it mirrors the Gizmo
-- reference the UI is modeled on, decks are shared and studied
-- collectively (see the Leaderboard tab sitting next to Materials there).
--
-- What's genuinely personal is whether YOU took it and how YOU did.
-- quiz_sets has no user_id on purpose, that would make it a private copy
-- per student, which is the wrong shape. This table is the missing half:
-- per (user, set) attempt counters, read to answer "have I done this one"
-- and "what was my score" without touching the shared set itself.
--
-- Deliberately NOT derived from evidence_events. That table has no
-- item_id, so there is no way to reconstruct "which set was this
-- evidence row for" after the fact, evidence rows for the same skill
-- from two different sets are indistinguishable. Rather than widen the
-- immutable, research-exported evidence log to carry set linkage it
-- doesn't otherwise need, this is a small, purpose-built counter table
-- updated alongside the untouched evidence/tracer writes, not instead
-- of them.
-- =====================================================================

create table public.quiz_set_attempts (
  id                 uuid primary key default gen_random_uuid(),
  institution_id     uuid not null references public.institutions(id) on delete cascade,
  user_id            uuid not null references public.users(id) on delete cascade,
  course_id          uuid not null references public.courses(id) on delete cascade,
  set_id             uuid not null references public.quiz_sets(id) on delete cascade,
  attempted_count    smallint not null default 0,
  correct_count      smallint not null default 0,
  last_attempted_at  timestamptz,
  created_at         timestamptz not null default now(),
  unique (user_id, set_id)
);
create index quiz_set_attempts_set_idx on public.quiz_set_attempts (set_id);
create index quiz_set_attempts_user_idx on public.quiz_set_attempts (user_id, course_id);

alter table public.quiz_set_attempts enable row level security;

-- Self / course staff / admin read, exactly the evidence_events and
-- mastery_state shape from 0002_rls.sql. Unlike quiz_sets (staff-only,
-- shared content), this table IS personal, so the student reads their
-- own rows directly, same as their own mastery and evidence.
create policy quiz_set_attempts_read on public.quiz_set_attempts for select to authenticated
  using (
    user_id = auth.uid()
    or public.teaches(course_id)
    or (public.is_admin() and institution_id = public.current_institution())
  );

grant select on public.quiz_set_attempts to authenticated;
-- No authenticated insert/update/delete: written only by the API via the
-- service_role key from submit(), same pattern as evidence_events.
