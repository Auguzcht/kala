-- =====================================================================
-- Kala — 0007_skill_proposals.sql
-- AI-proposed skills with a human-in-the-loop review gate, plus
-- institution-wide dedup so shared/reused MMCM courses converge on one
-- canonical skill instead of re-minting near-duplicates per course.
--
-- Design notes:
--  * skills stays course-scoped (nothing that already reads it changes).
--  * status gates what the learner/instructor UI shows: only 'approved'
--    skills feed the twin, heatmap, diagnostic. 'proposed' skills are
--    staged for review; 'rejected' are kept for audit, never shown.
--  * embedding lets the proposal step find an already-approved skill
--    (in ANY course in the institution) that means the same thing, and
--    reuse its wording/bloom/weight instead of creating a new row.
--  * canonical_skill_id points a course's skill row at the first approved
--    skill it was matched to, so "the same skill across 40 courses" is
--    traceable back to one origin without restructuring the table.
-- =====================================================================

-- 'proposed'  : AI-generated, awaiting human review (HITL gate)
-- 'approved'  : reviewed and live (or auto-approved via a prior match)
-- 'rejected'  : reviewed and dismissed, retained for audit
alter table public.skills
  add column status text not null default 'approved'
    check (status in ('proposed', 'approved', 'rejected')),
  add column embedding vector(1024),
  add column canonical_skill_id uuid references public.skills(id) on delete set null,
  add column proposed_source text,   -- e.g. the module_ref / content the proposal came from
  add column reviewed_by text,       -- lms_user_id of the human who approved/rejected
  add column reviewed_at timestamptz;

-- Existing rows predate this pipeline; they were hand-entered and are live.
-- The default 'approved' above already covers them, but be explicit so a
-- re-run is harmless.
update public.skills set status = 'approved' where status is null;

create index skills_status_idx on public.skills (course_id, status);

-- Institution-wide nearest-approved-skill search for dedup. Mirrors
-- match_content_items (0004) but over skills, and deliberately NOT
-- course-scoped: the whole point is to find an approved skill in a
-- DIFFERENT course that means the same thing. SECURITY DEFINER so the
-- service path can search; caller passes the institution scope explicitly.
create or replace function public.match_skills(
  p_institution_id uuid,
  p_query vector(1024),
  p_match_count int default 5
)
returns table (id uuid, name text, bloom_level text, blueprint_weight numeric,
               course_id uuid, similarity float)
language sql stable
set search_path = public, extensions
as $$
  select s.id, s.name, s.bloom_level, s.blueprint_weight, s.course_id,
         1 - (s.embedding <=> p_query) as similarity
  from public.skills s
  where s.institution_id = p_institution_id
    and s.status = 'approved'
    and s.embedding is not null
  order by s.embedding <=> p_query
  limit p_match_count
$$;
