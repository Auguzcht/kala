-- Record the telemetry for opening a practice set in one atomic database call.
-- The previous API path performed a read and an upsert for every item.
create or replace function public.record_practice_set_exposures(
  p_institution_id uuid,
  p_user_id uuid,
  p_course_id uuid,
  p_set_id uuid,
  p_item_ids uuid[]
)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  v_count integer;
begin
  with eligible as (
    select distinct g.id as item_id, g.skill_id
    from public.quiz_sets qs
    join public.generated_items g
      on g.institution_id = qs.institution_id
     and g.course_id = qs.course_id
     and g.id = any(coalesce(p_item_ids, '{}'::uuid[]))
    join public.skills s
      on s.id = g.skill_id
     and s.institution_id = g.institution_id
     and s.course_id = g.course_id
     and s.status = 'approved'
    where qs.id = p_set_id
      and qs.institution_id = p_institution_id
      and qs.course_id = p_course_id
      and g.retired_at is null
      and (g.set_id = qs.id or exists (
        select 1 from public.quiz_set_items qsi
        where qsi.set_id = qs.id and qsi.item_id = g.id
      ))
  ), written as (
    insert into public.item_exposures as existing (
      institution_id, user_id, course_id, skill_id, item_id,
      last_tested_at, times_tested, updated_at
    )
    select p_institution_id, p_user_id, p_course_id, e.skill_id, e.item_id,
           now(), 1, now()
    from eligible e
    on conflict (user_id, item_id) do update
      set last_tested_at = excluded.last_tested_at,
          times_tested = existing.times_tested + 1,
          updated_at = excluded.updated_at
    returning 1
  )
  select count(*) into v_count from written;
  return v_count;
end;
$$;

revoke all on function public.record_practice_set_exposures(uuid, uuid, uuid, uuid, uuid[])
  from public, anon, authenticated;
grant execute on function public.record_practice_set_exposures(uuid, uuid, uuid, uuid, uuid[])
  to service_role;

notify pgrst, 'reload schema';
