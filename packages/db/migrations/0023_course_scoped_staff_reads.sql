-- Kala — 0023_course_scoped_staff_reads.sql
-- Restrict staff reads of shared learning content to courses they teach.
-- Students retain no read policy on these tables.

drop policy content_read on public.content_items;
create policy content_read on public.content_items for select to authenticated
  using (
    public.teaches(course_id)
    or (public.is_admin() and institution_id = public.current_institution())
  );

drop policy items_read on public.generated_items;
create policy items_read on public.generated_items for select to authenticated
  using (
    public.teaches(course_id)
    or (public.is_admin() and institution_id = public.current_institution())
  );

drop policy quiz_sets_read on public.quiz_sets;
create policy quiz_sets_read on public.quiz_sets for select to authenticated
  using (
    public.teaches(course_id)
    or (public.is_admin() and institution_id = public.current_institution())
  );

drop policy quiz_set_items_read on public.quiz_set_items;
create policy quiz_set_items_read on public.quiz_set_items for select to authenticated
  using (
    exists (
      select 1
      from public.quiz_sets qs
      where qs.id = quiz_set_items.set_id
        and (
          public.teaches(qs.course_id)
          or (public.is_admin() and qs.institution_id = public.current_institution())
        )
    )
  );
