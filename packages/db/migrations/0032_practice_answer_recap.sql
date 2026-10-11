-- Persist immutable, server-graded results so practice retries and end-of-set
-- recaps do not depend on client memory or re-grade an answer.
create table if not exists public.practice_answer_results (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null,
  user_id uuid not null,
  course_id uuid not null,
  set_id uuid,
  item_id uuid not null references public.generated_items(id) on delete no action,
  skill_id uuid,
  session_id uuid,
  idempotency_key text not null,
  prompt text not null,
  choices jsonb not null default '[]'::jsonb,
  choice_id text not null,
  choice_text text,
  correct_option_id text not null,
  correct_answer_text text,
  explanation text not null default '',
  correct boolean not null,
  xp_awarded integer not null default 0 check (xp_awarded >= 0),
  mastery_before numeric,
  mastery_before_level text not null,
  mastery_after numeric,
  mastery_after_level text not null,
  created_at timestamptz not null default now(),
  unique (user_id, idempotency_key),
  unique (user_id, set_id, item_id)
);

create index if not exists practice_answer_results_user_set_created_idx
  on public.practice_answer_results (user_id, set_id, created_at);
alter table public.practice_answer_results enable row level security;
revoke all on public.practice_answer_results from public, anon, authenticated;
grant select, insert on public.practice_answer_results to service_role;
drop trigger if exists practice_answer_results_immutable on public.practice_answer_results;
create trigger practice_answer_results_immutable
  before update or delete on public.practice_answer_results
  for each row execute function public.forbid_mutation();

-- Return shape is internal to the service-role API. The public HTTP response
-- remains additive and preserves the legacy fields.
drop function if exists public.submit_practice(uuid, uuid, uuid, uuid, text, uuid, uuid, text, integer);
create function public.submit_practice(
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
  correct_option_id text,
  correct_answer_text text,
  choice_id text,
  choice_text text,
  prompt text,
  choices jsonb,
  xp_awarded integer,
  mastery_before numeric,
  mastery_before_level text,
  mastery_after numeric,
  mastery_after_level text,
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
set search_path = ''
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
  v_item_course_id uuid;
  v_correct_option_id text;
  v_correct_answer_text text;
  v_choice_text text;
  v_prompt text;
  v_choices jsonb;
  v_explanation text;
  v_correct boolean;
  v_xp_awarded integer;
  v_mastery_before numeric;
  v_mastery_after numeric;
  v_mastery_before_level text;
  v_mastery_after_level text;
  v_review record;
  v_saved public.practice_answer_results%rowtype;
  v_replayed boolean := false;
begin
  if p_idempotency_key is null or length(p_idempotency_key) = 0 then
    raise exception 'idempotency key is required' using errcode = '22023';
  end if;

  -- Serialize both client-key retries and the legacy frontend's retries,
  -- which omit the optional key and are identified by (user, set, item).
  perform pg_advisory_xact_lock(hashtextextended(
    p_user_id::text || ':practice:' || coalesce(p_set_id::text, p_idempotency_key) || ':' || p_item_id::text, 0));
  select r.* into v_saved
    from public.practice_answer_results r
   where r.user_id = p_user_id
     and (r.idempotency_key = p_idempotency_key
          or (p_set_id is not null and r.set_id = p_set_id and r.item_id = p_item_id))
   order by (r.idempotency_key = p_idempotency_key) desc
   limit 1;
  if found then
    if v_saved.item_id <> p_item_id or v_saved.set_id is distinct from p_set_id then
      raise exception 'idempotency key already used for another answer' using errcode = '23505';
    end if;
    return query select v_saved.correct, v_saved.explanation, v_saved.mastery_after, true,
      v_saved.correct_option_id, v_saved.correct_answer_text, v_saved.choice_id,
      v_saved.choice_text, v_saved.prompt, v_saved.choices, v_saved.xp_awarded,
      v_saved.mastery_before, v_saved.mastery_before_level, v_saved.mastery_after,
      v_saved.mastery_after_level, 0::numeric, 0::numeric, 0::numeric, 0::numeric,
      0::numeric, 0::numeric, 0::numeric;
    return;
  end if;

  if p_set_id is not null then
    v_stage_started := clock_timestamp();
    if not exists (
      select 1 from public.quiz_set_items qsi
      join public.quiz_sets qs on qs.id = qsi.set_id
      where qsi.set_id = p_set_id and qsi.item_id = p_item_id
        and qs.course_id = p_course_id and qs.institution_id = p_institution_id
    ) then
      raise exception 'item is not in this set' using errcode = 'P0002';
    end if;
    v_set_membership_ms := extract(epoch from clock_timestamp() - v_stage_started) * 1000;
  end if;

  v_stage_started := clock_timestamp();
  select gi.skill_id, gi.course_id, gi.correct_choice_id, gi.explanation,
         gi.prompt, coalesce(gi.choices, '[]'::jsonb)
    into v_skill_id, v_item_course_id, v_correct_option_id, v_explanation,
         v_prompt, v_choices
    from public.generated_items gi
    join public.skills sk on sk.id = gi.skill_id
   where gi.id = p_item_id and gi.institution_id = p_institution_id
     and gi.retired_at is null and sk.institution_id = p_institution_id
     and sk.course_id = gi.course_id and sk.status = 'approved';
  v_item_lookup_ms := extract(epoch from clock_timestamp() - v_stage_started) * 1000;
  if v_skill_id is null or v_item_course_id <> p_course_id then
    raise exception 'item not found' using errcode = 'P0002';
  end if;

  select c.value->>'label' into v_correct_answer_text
    from jsonb_array_elements(v_choices) as c(value)
   where c.value->>'id' = v_correct_option_id;
  select c.value->>'label' into v_choice_text
    from jsonb_array_elements(v_choices) as c(value)
   where c.value->>'id' = p_choice_id;

  -- Match the existing mastery lock order before taking the baseline snapshot.
  perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || ':' || v_skill_id::text, 0));
  select ms.estimate into v_mastery_before from public.mastery_state ms
   where ms.user_id = p_user_id and ms.skill_id = v_skill_id;
  v_mastery_before_level := case
    when v_mastery_before is null then 'No evidence'
    when v_mastery_before < 0.4 then 'Developing'
    when v_mastery_before < 0.7 then 'Proficient'
    else 'Mastered' end;

  v_stage_started := clock_timestamp();
  v_correct := p_choice_id = v_correct_option_id;
  v_grading_ms := extract(epoch from clock_timestamp() - v_stage_started) * 1000;

  v_stage_started := clock_timestamp();
  select * into v_review from public.review_flashcard(
    p_institution_id, p_user_id, p_course_id, p_item_id,
    case when v_correct then 'good' else 'again' end,
    'quiz', p_session_id, p_idempotency_key, p_latency_ms
  );
  v_review_rpc_ms := extract(epoch from clock_timestamp() - v_stage_started) * 1000;
  v_mastery_after := v_review.mastery_estimate;
  v_mastery_after_level := case
    when v_mastery_after is null then 'No evidence'
    when v_mastery_after < 0.4 then 'Developing'
    when v_mastery_after < 0.7 then 'Proficient'
    else 'Mastered' end;
  v_xp_awarded := case when v_review.counted then 2 + case when v_correct then 10 else 0 end else 0 end;

  if p_set_id is not null then
    v_stage_started := clock_timestamp();
    insert into public.quiz_set_attempts as existing (
      institution_id, user_id, course_id, set_id, attempted_count, correct_count, last_attempted_at
    ) values (p_institution_id, p_user_id, p_course_id, p_set_id, 1,
      case when v_correct then 1 else 0 end, now())
    on conflict (user_id, set_id) do update
      set attempted_count = (existing.attempted_count + 1)::smallint,
          correct_count = (existing.correct_count + case when v_correct then 1 else 0 end)::smallint,
          last_attempted_at = excluded.last_attempted_at;
    v_attempts_ms := extract(epoch from clock_timestamp() - v_stage_started) * 1000;
  end if;

  v_stage_started := clock_timestamp();
  begin
    insert into public.item_exposures as existing (
      institution_id, user_id, course_id, skill_id, item_id, last_tested_at,
      last_answered_at, last_correct, times_tested, updated_at
    ) values (p_institution_id, p_user_id, p_course_id, v_skill_id, p_item_id,
      case when p_set_id is not null then now() else null end, now(), v_correct,
      case when p_set_id is not null then 1 else 0 end, now())
    on conflict (user_id, item_id) do update
      set last_tested_at = case when p_set_id is not null then excluded.last_tested_at else existing.last_tested_at end,
          last_answered_at = excluded.last_answered_at, last_correct = excluded.last_correct,
          times_tested = existing.times_tested + case when p_set_id is not null then 1 else 0 end,
          updated_at = excluded.updated_at;
  exception when others then
    null;
  end;
  v_exposure_ms := extract(epoch from clock_timestamp() - v_stage_started) * 1000;

  insert into public.practice_answer_results (
    institution_id, user_id, course_id, set_id, item_id, skill_id, session_id,
    idempotency_key, prompt, choices, choice_id, choice_text,
    correct_option_id, correct_answer_text, explanation, correct, xp_awarded,
    mastery_before, mastery_before_level, mastery_after, mastery_after_level
  ) values (
    p_institution_id, p_user_id, p_course_id, p_set_id, p_item_id, v_skill_id, p_session_id,
    p_idempotency_key, v_prompt, v_choices, p_choice_id, v_choice_text,
    v_correct_option_id, coalesce(v_correct_answer_text, ''), coalesce(v_explanation, ''),
    v_correct, v_xp_awarded, v_mastery_before, v_mastery_before_level,
    v_mastery_after, v_mastery_after_level
  ) returning * into v_saved;

  return query select v_correct, v_saved.explanation, v_mastery_after, v_replayed,
    v_saved.correct_option_id, v_saved.correct_answer_text, v_saved.choice_id,
    v_saved.choice_text, v_saved.prompt, v_saved.choices, v_saved.xp_awarded,
    v_saved.mastery_before, v_saved.mastery_before_level, v_saved.mastery_after,
    v_saved.mastery_after_level, v_item_lookup_ms, v_grading_ms, v_set_membership_ms,
    v_review_rpc_ms, v_attempts_ms, v_exposure_ms,
    extract(epoch from clock_timestamp() - v_started) * 1000;
end;
$$;

revoke all on function public.submit_practice(uuid, uuid, uuid, uuid, text, uuid, uuid, text, integer)
  from public, anon, authenticated;
grant execute on function public.submit_practice(uuid, uuid, uuid, uuid, text, uuid, uuid, text, integer)
  to service_role;
notify pgrst, 'reload schema';
