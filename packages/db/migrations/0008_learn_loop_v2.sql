-- =====================================================================
-- Kala — 0008_learn_loop_v2.sql
-- Learn Loop v2: spaced-repetition scheduling + persistent guided lessons.
--
-- Two new subsystems, both derived from / feeding the same append-only
-- evidence_events log the twin already runs on:
--
--   1. srs_state — the ONE piece of state the learn loop had no home for.
--      Per (user, generated_item) scheduling for spaced repetition: which
--      box a card is in, when it is next due, how many times in a row it
--      has been recalled. Scheduling is PER CARD (not per skill) on purpose
--      — see app/learn/srs.py for why. skill_id is denormalized so mastery
--      still rolls up per skill without a join.
--
--   2. guided_lessons / guided_lesson_steps — persistent, generated-once
--      guided walkthroughs (the Gizmo step-by-step). Generated on demand the
--      first time a student opens a skill's lesson, then stored and replayed.
--      Each step is an explain-then-check unit; the check writes a normal
--      tutor evidence_event so the guided tutor is a mastery source, not
--      just a chat window.
--
-- Also widens generated_items so tutor-check items live in the same table
-- as diagnostic/practice/flashcard items, and adds chunk-level provenance
-- so any generated item can cite the exact course passage it came from.
-- =====================================================================

-- ---- generated_items: widen kind + add chunk-level provenance -------------
-- 'tutor' lets a guided-lesson comprehension check be a first-class,
-- gradeable generated_item (same answer-key-stays-server pattern as MCQs).
alter table public.generated_items
  drop constraint if exists generated_items_kind_check;
alter table public.generated_items
  add constraint generated_items_kind_check
  check (kind in ('diagnostic', 'practice', 'flashcard', 'tutor'));

-- source_content_id already links an item to one content_item. source_chunk_ids
-- records the specific RAG chunks the item was grounded in, so "Explain" can
-- cite the exact passage and the research export can audit grounding. Nullable:
-- fallback-generated items (no retrieval) simply leave it null.
alter table public.generated_items
  add column if not exists source_chunk_ids jsonb;

-- module_ref denormalized onto items so a deck / lesson can be scoped to one
-- module without walking skills -> hierarchy every request (mirrors how skills
-- and content_items already carry module_ref since 0006).
alter table public.generated_items
  add column if not exists module_ref text;


-- ---- srs_state: per-card spaced-repetition schedule -----------------------
create table public.srs_state (
  institution_id      uuid not null references public.institutions(id) on delete cascade,
  user_id             uuid not null references public.users(id) on delete cascade,
  course_id           uuid not null references public.courses(id) on delete cascade,
  item_id             uuid not null references public.generated_items(id) on delete cascade,
  skill_id            uuid references public.skills(id) on delete set null,
  -- Leitner box, 0..5. 0 = brand new / just lapsed (seen most often),
  -- 5 = long-interval mature card. box drives the due interval; see srs.py.
  box                 smallint not null default 0 check (box between 0 and 5),
  -- SM-2 style ease factor, scaled x1000 to stay integer (2500 = 2.5).
  -- Bounded [1300, 3000]. Lowered by lapses, nudged up by easy recalls.
  ease_milli          integer not null default 2500 check (ease_milli between 1300 and 3000),
  -- Consecutive correct recalls at or above box 0. Resets to 0 on a lapse.
  -- Graduation (card considered mastered, stops surfacing) is a function of
  -- this plus box — kept as data so the threshold can be tuned centrally.
  streak              smallint not null default 0,
  reps                integer not null default 0,   -- total reviews, ever
  lapses              integer not null default 0,   -- total times forgotten
  -- Denormalized from the card's generated_item so a review deck can be
  -- scoped to one module/lesson (the Gizmo "study this subdeck" flow) without
  -- joining srs_state -> generated_items -> skills every query.
  module_ref          text,
  due_at              timestamptz not null default now(),
  last_reviewed_at    timestamptz,
  created_at          timestamptz not null default now(),
  primary key (user_id, item_id)
);
create index srs_state_due_idx
  on public.srs_state (user_id, course_id, due_at);
create index srs_state_skill_idx
  on public.srs_state (user_id, skill_id);
create index srs_state_module_idx
  on public.srs_state (user_id, course_id, module_ref);

alter table public.srs_state enable row level security;

-- Students read their OWN schedule; course staff may read their students'
-- (for the instructor drill-down); admins institution-wide. Mirrors the
-- evidence_events read policy shape.
create policy srs_read on public.srs_state for select to authenticated
  using (
    user_id = auth.uid()
    or (public.is_staff() and institution_id = public.current_institution())
  );
-- Writes go through the service role (the API), never the browser, exactly
-- like mastery_state and evidence_events. No authenticated insert/update
-- policy on purpose.
grant select on public.srs_state to authenticated;


-- ---- guided_lessons: persistent generated walkthroughs --------------------
create table public.guided_lessons (
  id                 uuid primary key default gen_random_uuid(),
  institution_id     uuid not null references public.institutions(id) on delete cascade,
  course_id          uuid not null references public.courses(id) on delete cascade,
  -- A lesson is generated for one skill (the atomic learning object). skill_id
  -- + course_id is unique, so "open the lesson for this skill" is idempotent:
  -- generate once, replay thereafter.
  skill_id           uuid not null references public.skills(id) on delete cascade,
  module_ref         text,
  title              text not null,
  -- 'ready' once all steps are generated; 'generating' guards against two
  -- concurrent first-opens both kicking off generation.
  status             text not null default 'ready'
                       check (status in ('generating', 'ready', 'failed')),
  source_chunk_ids   jsonb,        -- provenance for the whole lesson
  created_at         timestamptz not null default now(),
  unique (course_id, skill_id)
);
create index guided_lessons_course_idx
  on public.guided_lessons (course_id, skill_id);

create table public.guided_lesson_steps (
  id                 uuid primary key default gen_random_uuid(),
  lesson_id          uuid not null references public.guided_lessons(id) on delete cascade,
  position           smallint not null,        -- 0-based order within the lesson
  -- The teach half: structured so the client renders real hierarchy
  -- (summary, detail bullets, misconception, key takeaway) instead of a blob.
  summary            text not null,
  detail_points      jsonb not null default '[]'::jsonb,   -- [str, ...]
  misconception      text,
  key_takeaway       text,
  bloom_level        text check (bloom_level in
                       ('remember', 'understand', 'apply', 'analyze', 'evaluate', 'create')),
  -- The check half: the comprehension gate. Points at a generated_items row
  -- (kind='tutor') so grading reuses the server-side answer-key path and the
  -- pass writes a tutor evidence_event. Null for a pure-explanation step.
  check_item_id      uuid references public.generated_items(id) on delete set null,
  created_at         timestamptz not null default now(),
  unique (lesson_id, position)
);
create index guided_lesson_steps_lesson_idx
  on public.guided_lesson_steps (lesson_id, position);

alter table public.guided_lessons      enable row level security;
alter table public.guided_lesson_steps enable row level security;

-- Lessons are course content, not per-student: any enrolled member of the
-- institution may read them; the API (service role) writes them. Same shape
-- as generated_items' staff-scoped read, but widened to any authenticated
-- member of the institution since a student must read their own lesson.
create policy lessons_read on public.guided_lessons for select to authenticated
  using (institution_id = public.current_institution());
create policy lesson_steps_read on public.guided_lesson_steps for select to authenticated
  using (
    exists (
      select 1 from public.guided_lessons gl
      where gl.id = guided_lesson_steps.lesson_id
        and gl.institution_id = public.current_institution()
    )
  );
grant select on public.guided_lessons      to authenticated;
grant select on public.guided_lesson_steps to authenticated;
