-- Grade and record a practice answer with one service-role PostgREST call.
-- The existing review RPC remains the single source for SRS, review ledger,
-- research evidence, and mastery transitions.
create or replace function public.submit_practice(
  p_institution_id uuid,
  p_user_id uuid,
  p_course_id uuid,
  p_item_id uuid,
  p_choice_id text,
  p_set_id uuid,
  p_session_id uuid,
  p_idempotency_key text,
  p_latency_ms integer default 0
)
returns table(
  correct boolean,
  explanation text,
  mastery_estimate numeric,
  replayed boolean,
  item_lookup_ms numeric,
  grading_ms numeric,
  set_membership_ms numeric,
  review_rpc_ms numeric,
  attempts_ms numeric,
  exposure_ms numeric,
  transaction_ms numeric
)
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_started timestamptz := clock_timestamp();
  v_stage_started timestamptz;
  v_item_lookup_ms numeric := 0;
  v_grading_ms numeric := 0;
  v_set_membership_ms numeric := 0;
  v_review_rpc_ms numeric := 0;
  v_attempts_ms numeric := 0;
  v_exposure_ms numeric := 0;
  v_skill_id uuid;
  v_course_id uuid;
  v_correct_choice_id text;
  v_explanation text;
  v_correct boolean;
  v_review record;
begin
  v_stage_started := clock_timestamp();
  select gi.skill_id, gi.course_id, gi.correct_choice_id, coalesce(gi.explanation, '')
    into v_skill_id, v_course_id, v_correct_choice_id, v_explanation
    from public.generated_items gi
    join public.skills sk on sk.id = gi.skill_id
   where gi.id = p_item_id
     and gi.institution_id = p_institution_id
     and gi.retired_at is null
     and sk.institution_id = p_institution_id
     and sk.course_id = gi.course_id
     and sk.status = 'approved';
  v_item_lookup_ms := extract(epoch from clock_timestamp() - v_stage_started) * 1000;
  if v_skill_id is null or v_course_id <> p_course_id then
    raise exception 'item not found' using errcode = 'P0002';
  end if;

  v_stage_started := clock_timestamp();
  v_correct := p_choice_id = v_correct_choice_id;
  v_grading_ms := extract(epoch from clock_timestamp() - v_stage_started) * 1000;

  if p_set_id is not null then
    v_stage_started := clock_timestamp();
    if not exists (
      select 1
        from public.quiz_set_items qsi
        join public.quiz_sets qs on qs.id = qsi.set_id
       where qsi.set_id = p_set_id and qsi.item_id = p_item_id
         and qs.course_id = p_course_id and qs.institution_id = p_institution_id
    ) then
      raise exception 'item is not in this set' using errcode = 'P0002';
    end if;
    v_set_membership_ms := extract(epoch from clock_timestamp() - v_stage_started) * 1000;
  end if;

  v_stage_started := clock_timestamp();
  select * into v_review
    from public.review_flashcard(
      p_institution_id, p_user_id, p_course_id, p_item_id,
      case when v_correct then 'good' else 'again' end,
      'quiz', p_session_id, p_idempotency_key, p_latency_ms
    );
  v_review_rpc_ms := extract(epoch from clock_timestamp() - v_stage_started) * 1000;

  if p_set_id is not null and not v_review.replayed then
    v_stage_started := clock_timestamp();
    insert into public.quiz_set_attempts as existing (
      institution_id, user_id, course_id, set_id, attempted_count, correct_count,
      last_attempted_at
    ) values (
      p_institution_id, p_user_id, p_course_id, p_set_id, 1,
      case when v_correct then 1 else 0 end, now()
    ) on conflict (user_id, set_id) do update
      set attempted_count = (existing.attempted_count + 1)::smallint,
          correct_count = (existing.correct_count + case when v_correct then 1 else 0 end)::smallint,
          last_attempted_at = excluded.last_attempted_at;
    v_attempts_ms := extract(epoch from clock_timestamp() - v_stage_started) * 1000;
  end if;

  if not v_review.replayed then
    v_stage_started := clock_timestamp();
    begin
      insert into public.item_exposures as existing (
        institution_id, user_id, course_id, skill_id, item_id, last_tested_at,
        last_answered_at, last_correct, times_tested, updated_at
      ) values (
        p_institution_id, p_user_id, p_course_id, v_skill_id, p_item_id,
        case when p_set_id is not null then now() else null end,
        now(), v_correct, case when p_set_id is not null then 1 else 0 end, now()
      ) on conflict (user_id, item_id) do update
        set last_tested_at = case when p_set_id is not null then excluded.last_tested_at
                                  else existing.last_tested_at end,
            last_answered_at = excluded.last_answered_at,
            last_correct = excluded.last_correct,
            times_tested = existing.times_tested + case when p_set_id is not null then 1 else 0 end,
            updated_at = excluded.updated_at;
    exception when others then
      -- Exposure is auxiliary telemetry and was best-effort before this RPC.
      null;
    end;
    v_exposure_ms := extract(epoch from clock_timestamp() - v_stage_started) * 1000;
  end if;

  return query select v_correct, v_explanation, v_review.mastery_estimate,
    v_review.replayed, v_item_lookup_ms, v_grading_ms, v_set_membership_ms,
    v_review_rpc_ms, v_attempts_ms, v_exposure_ms,
    extract(epoch from clock_timestamp() - v_started) * 1000;
end;
$$;

revoke all on function public.submit_practice(uuid, uuid, uuid, uuid, text, uuid, uuid, text, integer)
  from public, anon, authenticated;
grant execute on function public.submit_practice(uuid, uuid, uuid, uuid, text, uuid, uuid, text, integer)
  to service_role;
notify pgrst, 'reload schema';
