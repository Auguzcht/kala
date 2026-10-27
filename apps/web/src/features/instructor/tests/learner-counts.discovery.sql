-- INSTR-REQ-012 / WI-34: read-only counts, no identifiers or profile rows.
-- These profile labels locate candidates only. They do not prove a WI-24 pair.
-- A canonical candidate also requires unique current course membership.
-- A legacy pair requires its LMS identifier alias to point to that canonical.
-- If candidates or course are ambiguous, do not fill the main query by guess.
begin transaction isolation level repeatable read read only;
with candidates as (
  select u.id, u.institution_id, u.lms_user_id,
    case lower(trim(p.display_name)) when 'hanna sato' then 'hanna' else 'alfred' end as family
  from public.users u join public.user_profiles p on p.user_id = u.id
  where u.role = 'student' and lower(trim(p.display_name)) in ('hanna sato','alfred nodado')
), scoped as (
  select c.*, en.course_id from candidates c join public.enrollments en
    on en.user_id = c.id and en.institution_id = c.institution_id and en.role = 'student'
), courses as (
  select institution_id, course_id from scoped group by institution_id, course_id
  having count(distinct family) = 2
)
select jsonb_build_object(
  'hanna_candidate_anchors', (select count(*) from candidates where family = 'hanna'),
  'alfred_candidate_anchors', (select count(*) from candidates where family = 'alfred'),
  'shared_current_course_scopes', (select count(*) from courses),
  'hanna_current_anchors', (select count(*) from scoped s join courses c using(institution_id,course_id) where family = 'hanna'),
  'alfred_current_anchors', (select count(*) from scoped s join courses c using(institution_id,course_id) where family = 'alfred'),
  'hanna_legacy_alias_links_to_current', (select count(*) from candidates a
    join public.lms_identity_aliases la on la.institution_id = a.institution_id and la.lms_user_id = a.lms_user_id
    join scoped s on s.id = la.user_id and s.institution_id = a.institution_id and s.family = a.family
    join courses c on c.institution_id = s.institution_id and c.course_id = s.course_id
    where a.family = 'hanna' and a.id <> s.id),
  'alfred_legacy_alias_links_to_current', (select count(*) from candidates a
    join public.lms_identity_aliases la on la.institution_id = a.institution_id and la.lms_user_id = a.lms_user_id
    join scoped s on s.id = la.user_id and s.institution_id = a.institution_id and s.family = a.family
    join courses c on c.institution_id = s.institution_id and c.course_id = s.course_id
    where a.family = 'alfred' and a.id <> s.id),
  'cross_family_alias_owners', (select count(*) from candidates a
    join public.lms_identity_aliases la on la.institution_id = a.institution_id and la.lms_user_id = a.lms_user_id
    join candidates b on b.id = la.user_id and b.institution_id = a.institution_id
    where a.family <> b.family)
) as candidate_counts;
rollback;
