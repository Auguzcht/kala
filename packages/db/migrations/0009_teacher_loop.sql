-- =====================================================================
-- Kala — 0009_teacher_loop.sql
-- The human-in-the-loop teaching layer.
--
-- 0001 created `recommendations` as a thin (action, rationale) row and
-- nothing ever wrote to it. This migration turns it into the object the
-- product is actually about: an AI-proposed next action for ONE learner
-- that a named teacher approves, modifies, or rejects, and that only
-- reaches the learner after that decision.
--
-- The shape mirrors the skill-proposal gate in 0007: propose -> review ->
-- live. Same principle, different object. Nothing here auto-applies. A
-- recommendation with status 'suggested' is invisible to the student; the
-- student-facing plan endpoint reads status in ('approved','modified')
-- only.
--
-- Why the decision fields live on the same row rather than a separate
-- decisions table: there is exactly one decision per recommendation and
-- the audit question ("who decided this, when, and why") is answered by
-- reading the row. audit_log already captures the mutation history, so a
-- second table would duplicate it without adding an answer.
-- =====================================================================

-- ---- recommendations: the decision loop ----------------------------------

alter table public.recommendations
  -- What the teacher reads at a glance. `action` (0001) stays the machine
  -- verb; `title` is the human sentence.
  add column if not exists title text,

  -- The gate. 'suggested' = AI proposed it, no human has looked.
  -- 'approved' = teacher accepted as written. 'modified' = teacher accepted
  -- with edits (kept distinct from 'approved' on purpose: the research
  -- question "how often do teachers edit the AI rather than take it" is
  -- only answerable if the two are different values). 'rejected' = teacher
  -- declined, stays for the audit trail and the model-quality signal.
  -- 'completed' = the learner finished the work it asked for.
  add column if not exists status text not null default 'suggested',

  add column if not exists priority text not null default 'medium',

  -- Which surface the learner is sent to when they act on this.
  add column if not exists kind text not null default 'practice',

  -- Model self-reported confidence, 0..1. Shown to the teacher as a number
  -- with its band, never as a bare "84%" badge with no explanation.
  add column if not exists confidence numeric,

  -- Projected readiness delta if the learner completes it, 0..1. A
  -- heuristic, labelled as one in the UI.
  add column if not exists expected_gain numeric,

  -- The receipts: the specific evidence rows / mastery facts this was
  -- derived from, as [{label, detail}]. A recommendation without evidence
  -- is not shown — "never a bare score" (DESIGN.md).
  add column if not exists evidence jsonb not null default '[]'::jsonb,

  -- Provenance: which model produced it, or 'heuristic' when the
  -- deterministic fallback did. The teacher can see which.
  add column if not exists source text,

  -- Who decided, when, and the reason they typed. decision_note is the
  -- teacher's own words; it is the most valuable row in the research
  -- dataset and the thing that makes the loop auditable rather than
  -- theatrical.
  add column if not exists decided_by uuid references public.users(id) on delete set null,
  add column if not exists decided_at timestamptz,
  add column if not exists decision_note text,

  -- Shown to the learner alongside the action when the teacher wants to
  -- say something in their own voice. Optional.
  add column if not exists instructor_note text,

  add column if not exists updated_at timestamptz not null default now();

-- Constraints added separately so re-running the migration is safe.
alter table public.recommendations
  drop constraint if exists recommendations_status_check;
alter table public.recommendations
  add constraint recommendations_status_check
  check (status in ('suggested', 'approved', 'modified', 'rejected', 'completed'));

alter table public.recommendations
  drop constraint if exists recommendations_priority_check;
alter table public.recommendations
  add constraint recommendations_priority_check
  check (priority in ('high', 'medium', 'low'));

alter table public.recommendations
  drop constraint if exists recommendations_kind_check;
alter table public.recommendations
  add constraint recommendations_kind_check
  check (kind in ('practice', 'lesson', 'flashcards', 'tutor', 'diagnostic', 'outreach'));

-- The two hot reads: the teacher's queue for a course, and one learner's
-- approved plan.
create index if not exists recommendations_course_status_idx
  on public.recommendations (course_id, status, created_at desc);
create index if not exists recommendations_user_status_idx
  on public.recommendations (user_id, course_id, status, created_at desc);

-- ---- RLS -----------------------------------------------------------------
-- Read policy (recs_read, 0002) already covers the right audience: own
-- rows, the teacher of the course, institution admins. What was missing is
-- write: only a teacher of the course (or an institution admin) may create
-- or decide a recommendation. A student can never write one about
-- themselves, which is the whole point of the gate.

drop policy if exists recs_insert on public.recommendations;
create policy recs_insert on public.recommendations for insert to authenticated
  with check (
    institution_id = public.current_institution()
    and (public.teaches(course_id) or public.is_admin())
  );

drop policy if exists recs_update on public.recommendations;
create policy recs_update on public.recommendations for update to authenticated
  using (
    institution_id = public.current_institution()
    and (public.teaches(course_id) or public.is_admin())
  )
  with check (
    institution_id = public.current_institution()
    and (public.teaches(course_id) or public.is_admin())
  );

grant insert, update on public.recommendations to authenticated;

-- ---- readiness_snapshots: make the trend line real -----------------------
-- The worker already writes these (services/worker/app/jobs/readiness_snapshot.py).
-- The instructor trend chart reads them per course over a window, which had
-- no supporting index.
create index if not exists readiness_snapshots_course_time_idx
  on public.readiness_snapshots (course_id, created_at desc);
create index if not exists readiness_snapshots_user_time_idx
  on public.readiness_snapshots (user_id, course_id, created_at desc);
