-- =====================================================================
-- Kala — 0003_research.sql
-- The ONLY surface external researchers can read. Researchers authenticate
-- through their own portal (app_role='researcher', sub = researchers.id) and
-- never touch base tables (RLS denies them). These views run as owner and
-- enforce three gates in the view body:
--   1. app_role must be 'researcher'
--   2. an active grant must exist for the institution
--   3. only rows for students who consented to research are included
-- Row-level views expose pseudonyms only (no names, no emails, no lms ids).
-- The cohort view is aggregate-only with k-anonymity (groups under 10 hidden).
-- =====================================================================

-- Row-anonymized mastery (scope: row_anon grants).
create or replace view public.research_mastery_anon as
select
  m.institution_id,
  u.pseudonym            as subject,
  m.course_id,
  s.name                 as skill,
  s.bloom_level,
  m.estimate,
  m.attempts,
  m.updated_at
from public.mastery_state m
join public.users  u on u.id = m.user_id
join public.skills s on s.id = m.skill_id
where public.current_app_role() = 'researcher'
  and public.has_grant(m.institution_id)
  and public.has_consent(m.user_id);

-- Row-anonymized evidence (scope: row_anon grants).
create or replace view public.research_evidence_anon as
select
  e.institution_id,
  u.pseudonym            as subject,
  e.course_id,
  e.skill_id,
  e.type,
  e.correct,
  e.latency_ms,
  e.hints_used,
  e.created_at
from public.evidence_events e
join public.users u on u.id = e.user_id
where public.current_app_role() = 'researcher'
  and public.has_grant(e.institution_id)
  and public.has_consent(e.user_id);

-- Aggregate cohort stats (scope: aggregate grants). k-anonymity: hide groups
-- with fewer than 10 attempts so individuals cannot be inferred.
create or replace view public.research_cohort_daily as
select
  e.institution_id,
  e.course_id,
  s.bloom_level,
  date_trunc('day', e.created_at)          as day,
  count(*)                                  as attempts,
  count(*) filter (where e.correct)         as correct
from public.evidence_events e
join public.skills s on s.id = e.skill_id
where public.current_app_role() = 'researcher'
  and public.has_grant(e.institution_id)
  and public.has_consent(e.user_id)
group by e.institution_id, e.course_id, s.bloom_level, date_trunc('day', e.created_at)
having count(*) >= 10;

-- Researchers read only these views.
grant select on
  public.research_mastery_anon,
  public.research_evidence_anon,
  public.research_cohort_daily
to authenticated;
