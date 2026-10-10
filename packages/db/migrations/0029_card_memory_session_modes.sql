-- Atomic tracking for a bounded Study session. The per-day budget is shared
-- by every skill in a course and follows the institution's local calendar.
create or replace function public.claim_study_cards(
  p_institution_id uuid,
  p_user_id uuid,
  p_course_id uuid,
  p_item_ids uuid[],
  p_daily_new_cap integer default 20
)
returns table(item_id uuid, is_new boolean)
language plpgsql
set search_path = public, pg_temp
as $$
declare
  v_timezone text;
  v_local_date date;
  v_day_start timestamptz;
  v_day_end timestamptz;
  v_new_count integer;
  v_candidate record;
  v_inserted uuid;
begin
  select coalesce(i.timezone, 'UTC') into v_timezone
  from public.institutions i where i.id = p_institution_id;
  if not found then
    raise exception 'institution not found';
  end if;

  v_local_date := (now() at time zone v_timezone)::date;
  v_day_start := v_local_date::timestamp at time zone v_timezone;
  v_day_end := (v_local_date + 1)::timestamp at time zone v_timezone;

  -- Serialize only the same student's course/day, so parallel requests cannot
  -- spend the daily new-card allowance twice.
  perform pg_advisory_xact_lock(hashtextextended(
    p_institution_id::text || ':' || p_user_id::text || ':' || p_course_id::text || ':' || v_local_date::text,
    0
  ));

  select count(*)::integer into v_new_count
  from public.srs_state s
  where s.institution_id = p_institution_id and s.user_id = p_user_id
    and s.course_id = p_course_id
    and s.created_at >= v_day_start and s.created_at < v_day_end;

  for v_candidate in
    select distinct candidate.item_id, candidate.ordinality
    from unnest(coalesce(p_item_ids, '{}'::uuid[])) with ordinality as candidate(item_id, ordinality)
    order by candidate.ordinality
  loop
    if exists (
      select 1 from public.srs_state s
      where s.institution_id = p_institution_id and s.user_id = p_user_id
        and s.course_id = p_course_id and s.item_id = v_candidate.item_id
    ) then
      item_id := v_candidate.item_id;
      is_new := false;
      return next;
      continue;
    end if;

    if v_new_count >= greatest(0, least(p_daily_new_cap, 20)) then
      continue;
    end if;

    insert into public.srs_state as stored (
      institution_id, user_id, course_id, item_id, skill_id, module_ref
    )
    select p_institution_id, p_user_id, p_course_id, gi.id, gi.skill_id, gi.module_ref
    from public.generated_items gi
    join public.skills sk on sk.id = gi.skill_id and sk.status = 'approved'
    where gi.id = v_candidate.item_id and gi.institution_id = p_institution_id
      and gi.course_id = p_course_id and gi.retired_at is null
      and ((gi.kind = 'practice' and gi.origin = 'bank') or gi.kind = 'flashcard')
    on conflict on constraint srs_state_pkey do nothing
    returning stored.item_id into v_inserted;

    if v_inserted is not null then
      v_new_count := v_new_count + 1;
      item_id := v_inserted;
      is_new := true;
      return next;
    elsif exists (
      select 1 from public.srs_state s
      where s.institution_id = p_institution_id and s.user_id = p_user_id
        and s.course_id = p_course_id and s.item_id = v_candidate.item_id
    ) then
      item_id := v_candidate.item_id;
      is_new := false;
      return next;
    end if;
    v_inserted := null;
  end loop;
end;
$$;

revoke all on function public.claim_study_cards(uuid, uuid, uuid, uuid[], integer) from public, anon, authenticated;
grant execute on function public.claim_study_cards(uuid, uuid, uuid, uuid[], integer) to service_role;
