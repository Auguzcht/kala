-- WI-26 / INSTR-REQ-009: tighten direct recommendation visibility and writes.
-- Applied predecessors and authorization helper definitions remain unchanged.
begin;

alter policy recs_read on public.recommendations using (
  institution_id = public.current_institution()
  and exists (
    select 1 from public.courses c
    where c.id = recommendations.course_id
      and c.institution_id = recommendations.institution_id
  )
  and (
    (public.current_app_role() = 'student'
      and user_id = auth.uid()
      and status in ('approved', 'modified', 'completed'))
    or (public.current_app_role() = 'instructor'
      and public.teaches(course_id)
      and exists (
        select 1 from public.enrollments e
        where e.course_id = recommendations.course_id
          and e.institution_id = recommendations.institution_id
          and e.user_id = auth.uid() and e.role = 'instructor'
      ))
    or public.is_admin()
  )
);

alter policy recs_insert on public.recommendations with check (
  institution_id = public.current_institution()
  and exists (
    select 1 from public.courses c
    where c.id = recommendations.course_id
      and c.institution_id = recommendations.institution_id
  )
  and (
    (public.current_app_role() = 'instructor'
      and public.teaches(course_id)
      and exists (
        select 1 from public.enrollments e
        where e.course_id = recommendations.course_id
          and e.institution_id = recommendations.institution_id
          and e.user_id = auth.uid() and e.role = 'instructor'
      ))
    or public.is_admin()
  )
);

alter policy recs_update on public.recommendations using (
  institution_id = public.current_institution()
  and exists (
    select 1 from public.courses c
    where c.id = recommendations.course_id
      and c.institution_id = recommendations.institution_id
  )
  and (
    (public.current_app_role() = 'instructor'
      and public.teaches(course_id)
      and exists (
        select 1 from public.enrollments e
        where e.course_id = recommendations.course_id
          and e.institution_id = recommendations.institution_id
          and e.user_id = auth.uid() and e.role = 'instructor'
      ))
    or public.is_admin()
  )
) with check (
  institution_id = public.current_institution()
  and exists (
    select 1 from public.courses c
    where c.id = recommendations.course_id
      and c.institution_id = recommendations.institution_id
  )
  and (
    (public.current_app_role() = 'instructor'
      and public.teaches(course_id)
      and exists (
        select 1 from public.enrollments e
        where e.course_id = recommendations.course_id
          and e.institution_id = recommendations.institution_id
          and e.user_id = auth.uid() and e.role = 'instructor'
      ))
    or public.is_admin()
  )
);

commit;
