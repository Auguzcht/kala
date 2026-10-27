-- INSTR-REQ-012 / WI-34: Fred runs this in the intended database privately.
-- Replace the NULLs in params using independently proved WI-24 anchors.
-- Copy the actual roster-row and drawer-request UUIDs privately, not names.
-- Legacy anchors may stay NULL only if Fred confirms there is no such anchor.
-- Do not paste identifiers, event rows, names, emails or secrets back to chat.
-- Return only the aggregate JSON. All identity checks must pass before edits.
-- Stop on cross-family anchors, aliases, targets or evidence. This cannot
-- establish who authored an event historically stored under the wrong UUID.
-- Compare two separately labelled environment/course runs for the 14/15 issue.
-- observed_before is the earlier observation time, optional if not known.
-- reviewed_at is current metadata, not an immutable approval history.
-- Boundary timestamp ties are reported because the API orders by time only.
begin transaction isolation level repeatable read read only;
with params as (
  select
    NULL::uuid as institution_id,
    NULL::uuid as course_id,
    NULL::uuid as hanna_canonical,
    NULL::uuid as hanna_legacy,
    NULL::uuid as alfred_canonical,
    NULL::uuid as alfred_legacy,
    NULL::uuid as roster_target,
    NULL::uuid as drawer_target,
    NULL::timestamptz as observed_before
), anchors as (
  select 'hanna' as family, 'canonical' as anchor, hanna_canonical as user_id from params
  union all select 'hanna', 'legacy', hanna_legacy from params
  union all select 'alfred', 'canonical', alfred_canonical from params
  union all select 'alfred', 'legacy', alfred_legacy from params
), cohort as (
  select distinct u.id from public.enrollments en
  join public.users u on u.id = en.user_id and u.institution_id = en.institution_id
  cross join params p
  where en.institution_id = p.institution_id and en.course_id = p.course_id
    and en.role = 'student' and u.role = 'student'
), course_events as (
  select e.* from public.evidence_events e cross join params p
  where e.institution_id = p.institution_id and e.course_id = p.course_id
), class_window as (
  select e.* from course_events e join cohort c on c.id = e.user_id
  order by e.created_at desc limit 2000
), roster_window as (
  select e.* from class_window e cross join params p where e.user_id = p.roster_target
), drawer_window as (
  select e.* from course_events e cross join params p where e.user_id = p.drawer_target
  order by e.created_at desc limit 200
), graded as (
  select correct, row_number() over (order by created_at desc) as n
  from drawer_window where correct is not null
), approved as (
  select s.* from public.skills s cross join params p
  where s.institution_id = p.institution_id and s.course_id = p.course_id
    and s.status = 'approved'
), measured as (
  select m.user_id, round(avg(m.estimate), 3) as readiness
  from public.mastery_state m join approved s on s.id = m.skill_id
  join cohort c on c.id = m.user_id cross join params p
  where m.institution_id = p.institution_id and m.course_id = p.course_id
  group by m.user_id
)
select jsonb_build_object(
  'identity_gate', jsonb_build_object(
    'required_inputs_set', (select count(*) from params where institution_id is not null
      and course_id is not null and hanna_canonical is not null and alfred_canonical is not null
      and roster_target is not null and drawer_target is not null),
    'anchors_supplied', (select count(*) from anchors where user_id is not null),
    'anchors_found_in_institution', (select count(*) from anchors a join public.users u on u.id = a.user_id
      cross join params p where u.institution_id = p.institution_id and u.role = 'student'),
    'canonical_learners_enrolled', (select count(*) from anchors a join cohort c on c.id = a.user_id where a.anchor = 'canonical'),
    'cross_family_anchor_collisions', (select count(*) from anchors a join anchors b on a.user_id = b.user_id where a.family = 'hanna' and b.family = 'alfred'),
    'targets_not_hanna_canonical', (select count(*) from params p cross join lateral (values (p.roster_target),(p.drawer_target)) t(id)
      where t.id is distinct from p.hanna_canonical),
    'cross_family_alias_owners', (select count(*) from anchors a join public.users u on u.id = a.user_id
      cross join params p join public.lms_identity_aliases la on la.institution_id = p.institution_id
      join anchors b on b.user_id = la.user_id and b.family <> a.family
      where u.institution_id = p.institution_id and la.lms_user_id = u.lms_user_id),
    'roster_alfred_owned_events', (select count(*) from roster_window e where exists (select 1 from anchors a where a.family = 'alfred' and a.user_id = e.user_id)),
    'drawer_alfred_owned_events', (select count(*) from drawer_window e where exists (select 1 from anchors a where a.family = 'alfred' and a.user_id = e.user_id))
  ),
  'anchor_counts', (select jsonb_object_agg(a.family || '_' || a.anchor, jsonb_build_object(
    'evidence', (select count(*) from course_events e where e.user_id = a.user_id),
    'graded', (select count(*) from course_events e where e.user_id = a.user_id and e.correct is not null),
    'correct', (select count(*) from course_events e where e.user_id = a.user_id and e.correct),
    'approved_mastery_skills', (select count(*) from public.mastery_state m join approved s on s.id = m.skill_id cross join params p
      where m.institution_id = p.institution_id and m.course_id = p.course_id and m.user_id = a.user_id),
    'approved_mastery_attempts', (select coalesce(sum(m.attempts),0) from public.mastery_state m join approved s on s.id = m.skill_id cross join params p
      where m.institution_id = p.institution_id and m.course_id = p.course_id and m.user_id = a.user_id)
  )) from anchors a),
  'windows', jsonb_build_object(
    'class_events_loaded', (select count(*) from class_window),
    'roster_events', (select count(*) from roster_window),
    'roster_graded', (select count(*) from roster_window where correct is not null),
    'roster_correct', (select count(*) from roster_window where correct),
    'drawer_events', (select count(*) from drawer_window),
    'drawer_graded', (select count(*) from drawer_window where correct is not null),
    'drawer_correct', (select count(*) from drawer_window where correct),
    'drawer_hints', (select coalesce(sum(hints_used),0) from drawer_window),
    'recent_graded', (select count(*) from graded where n <= 10),
    'recent_correct', (select count(*) from graded where n <= 10 and correct),
    'prior_graded', (select count(*) from graded where n between 11 and 20),
    'prior_correct', (select count(*) from graded where n between 11 and 20 and correct),
    'class_events_tied_at_boundary', (select count(*) from course_events e join cohort c on c.id = e.user_id
      where e.created_at = (select min(created_at) from class_window)),
    'drawer_events_tied_at_boundary', (select count(*) from course_events e cross join params p
      where e.user_id = p.drawer_target and e.created_at = (select min(created_at) from drawer_window))
  ),
  'course_counts', jsonb_build_object(
    'enrolled_learners', (select count(*) from cohort),
    'measured_learners', (select count(*) from measured),
    'learners_above_hanna', (select count(*) from measured m cross join params p
      where m.readiness > (select readiness from measured where user_id = p.hanna_canonical)),
    'learners_tied_with_hanna', (select count(*) from measured m cross join params p
      where m.readiness = (select readiness from measured where user_id = p.hanna_canonical)),
    'approved_skills', (select count(*) from approved),
    'proposed_skills', (select count(*) from public.skills s cross join params p where s.institution_id = p.institution_id and s.course_id = p.course_id and s.status = 'proposed'),
    'approved_reviewed_after_observation', (select count(*) from approved s cross join params p where s.reviewed_at > p.observed_before),
    'approved_created_after_observation', (select count(*) from approved s cross join params p where s.created_at > p.observed_before),
    'approved_without_review_timestamp', (select count(*) from approved where reviewed_at is null),
    'comparison_time_supplied', (select count(*) from params where observed_before is not null)
  )
) as aggregate_counts;
rollback;
