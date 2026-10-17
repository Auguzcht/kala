-- Attempt-scoped saved quiz runs. Existing set-level counters and answer
-- snapshots become attempt 1; future retakes get independent attempt rows.
begin;

-- Remove the live 9-argument submit function before replacing its dependency.
-- Also drop the draft's 10-argument form so it cannot remain as an overload.
drop function if exists public.submit_practice(uuid, uuid, uuid, uuid, text, uuid, uuid, text, integer);
drop function if exists public.submit_practice(uuid, uuid, uuid, uuid, text, uuid, uuid, text, integer, uuid);

alter table public.quiz_set_attempts
  add column attempt_number smallint not null default 1,
  add column completed_at timestamptz;

alter table public.practice_answer_results
  add column attempt_id uuid references public.quiz_set_attempts(id) on delete cascade;

-- Report any legacy result groups without a counter row before repairing them.
do $$
declare
  v_missing integer;
begin
  select count(*) into v_missing from (
    select distinct par.user_id, par.set_id
      from public.practice_answer_results par
     where par.set_id is not null
       and not exists (
         select 1 from public.quiz_set_attempts qsa
          where qsa.user_id = par.user_id and qsa.set_id = par.set_id
       )
  ) missing_groups;
  raise notice 'missing quiz_set_attempts groups repaired: %', v_missing;
end;
$$;

insert into public.quiz_set_attempts (
  institution_id, user_id, course_id, set_id, attempted_count, correct_count,
  last_attempted_at, attempt_number
)
select par.institution_id, par.user_id, par.course_id, par.set_id,
       count(*)::smallint,
       count(*) filter (where par.correct)::smallint,
       max(par.created_at), 1
  from public.practice_answer_results par
 where par.set_id is not null
   and not exists (
     select 1 from public.quiz_set_attempts qsa
      where qsa.user_id = par.user_id and qsa.set_id = par.set_id
   )
 group by par.institution_id, par.user_id, par.course_id, par.set_id;

-- Correct the old cumulative set counters. Saved answer rows are the exact
-- source where available; otherwise clamp legacy counters to set cardinality.
with item_counts as (
  select qsi.set_id, count(distinct qsi.item_id)::integer as item_count
    from public.quiz_set_items qsi group by qsi.set_id
), saved_counts as (
  select par.user_id, par.set_id, count(*)::integer as answered,
         count(*) filter (where par.correct)::integer as correct
    from public.practice_answer_results par
   where par.set_id is not null group by par.user_id, par.set_id
), attempt_counts as (
  select qsa.id,
         coalesce(sc.answered,
           least(qsa.attempted_count::integer, coalesce(ic.item_count, 0)))::smallint as attempted_count,
         coalesce(sc.correct,
           least(qsa.correct_count::integer, coalesce(ic.item_count, 0)))::smallint as correct_count
    from public.quiz_set_attempts qsa
    left join item_counts ic on ic.set_id = qsa.set_id
    left join saved_counts sc on sc.user_id = qsa.user_id and sc.set_id = qsa.set_id
)
update public.quiz_set_attempts qsa
   set attempted_count = ac.attempted_count,
       correct_count = ac.correct_count
  from attempt_counts ac
 where qsa.id = ac.id;

update public.quiz_set_attempts qsa
   set completed_at = qsa.last_attempted_at
 where qsa.attempted_count >= coalesce(nullif((
         select count(distinct qsi.item_id)::integer
           from public.quiz_set_items qsi where qsi.set_id = qsa.set_id
       ), 0), (
         select count(*)::integer from public.generated_items gi
          where gi.set_id = qsa.set_id and gi.institution_id = qsa.institution_id
       ), 0)
   and qsa.last_attempted_at is not null;

-- The existing snapshot trigger blocks UPDATE. Disable only that trigger for
-- this backfill, and re-enable it before the transaction commits.
alter table public.practice_answer_results
  disable trigger practice_answer_results_immutable;
update public.practice_answer_results par
   set attempt_id = qsa.id
  from public.quiz_set_attempts qsa
 where par.set_id is not null
   and qsa.user_id = par.user_id and qsa.set_id = par.set_id
   and par.attempt_id is null;
alter table public.practice_answer_results
  enable trigger practice_answer_results_immutable;

alter table public.practice_answer_results
  add constraint practice_answer_results_attempt_set_check
  check ((set_id is null) = (attempt_id is null));
alter table public.practice_answer_results
  drop constraint practice_answer_results_user_id_set_id_item_id_key;
alter table public.practice_answer_results
  add constraint practice_answer_results_attempt_item_key unique (attempt_id, item_id);

alter table public.quiz_set_attempts
  drop constraint quiz_set_attempts_user_id_set_id_key;
alter table public.quiz_set_attempts
  add constraint quiz_set_attempts_user_set_number_key
  unique (user_id, set_id, attempt_number);

drop function if exists public.review_flashcard(uuid, uuid, uuid, uuid, text, text, uuid, text, integer);
drop function if exists public.review_flashcard(uuid, uuid, uuid, uuid, text, text, uuid, text, integer, boolean);
create function public.review_flashcard(
  p_institution_id uuid,
  p_user_id uuid,
  p_course_id uuid,
  p_item_id uuid,
  p_outcome text,
  p_mode text,
  p_session_id uuid,
  p_idempotency_key text,
  p_latency_ms integer default 0,
  p_affects_mastery boolean default true
)
returns table (
  counted boolean,
  was_due boolean,
  box smallint,
  ease_milli integer,
  streak smallint,
  reps integer,
  lapses integer,
  last_outcome text,
  due_at timestamptz,
  graduated boolean,
  replayed boolean,
  mastery_estimate numeric
)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_now timestamptz := now();
  v_skill_id uuid;
  v_existing_item uuid;
  v_counted boolean;
  v_was_due boolean;
  v_box smallint;
  v_ease integer;
  v_streak smallint;
  v_reps integer;
  v_lapses integer;
  v_last_outcome text;
  v_due_at timestamptz;
  v_interval_hours numeric;
  v_replayed boolean := false;
  v_prior numeric;
  v_target numeric;
  v_attempts integer;
  v_mastery_estimate numeric;
begin
  if p_outcome is null or p_outcome not in ('again', 'good') then
    raise exception 'invalid outcome' using errcode = '22023';
  end if;
  if p_mode is null or p_mode not in ('flashcard', 'quiz') then
    raise exception 'invalid mode' using errcode = '22023';
  end if;
  if p_idempotency_key is null or length(p_idempotency_key) = 0 then
    raise exception 'idempotency key is required' using errcode = '22023';
  end if;

  -- Serialize a user's reuse of the same request key, even across cards.
  perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || ':' || p_idempotency_key, 0));

  select g.skill_id into v_skill_id
    from public.generated_items g
    join public.skills s on s.id = g.skill_id
   where g.id = p_item_id
     and g.institution_id = p_institution_id
     and g.course_id = p_course_id
     and g.retired_at is null
     and s.institution_id = p_institution_id
     and s.course_id = p_course_id
     and s.status = 'approved';
  if v_skill_id is null then
    raise exception 'card not found' using errcode = 'P0002';
  end if;

  select ir.counted, ir.item_id into v_counted, v_existing_item
    from public.item_reviews ir
   where ir.user_id = p_user_id and ir.idempotency_key = p_idempotency_key;
  if found then
    if v_existing_item <> p_item_id then
      raise exception 'idempotency key already used for another card' using errcode = '23505';
    end if;
    select st.box, st.ease_milli, st.streak, st.reps, st.lapses, st.last_outcome, st.due_at
      into v_box, v_ease, v_streak, v_reps, v_lapses, v_last_outcome, v_due_at
      from public.srs_state st
     where st.user_id = p_user_id and st.item_id = p_item_id;
    if p_mode = 'quiz' then
      select ms.estimate into v_mastery_estimate from public.mastery_state ms
       where ms.user_id = p_user_id and ms.skill_id = v_skill_id;
    end if;
    return query select v_counted, false, v_box, v_ease, v_streak, v_reps, v_lapses, v_last_outcome,
      v_due_at, (v_box >= 5 and v_streak >= 3), true, v_mastery_estimate;
    return;
  end if;

  insert into public.srs_state (
    institution_id, user_id, course_id, item_id, skill_id, due_at
  ) values (
    p_institution_id, p_user_id, p_course_id, p_item_id, v_skill_id, v_now
  ) on conflict (user_id, item_id) do nothing;

  select st.box, st.ease_milli, st.streak, st.reps, st.lapses, st.due_at
    into v_box, v_ease, v_streak, v_reps, v_lapses, v_due_at
    from public.srs_state st
   where st.user_id = p_user_id and st.item_id = p_item_id
   for update;
  v_was_due := v_due_at <= v_now;

  if p_session_id is not null and exists (
    select 1 from public.item_reviews ir
     where ir.user_id = p_user_id and ir.item_id = p_item_id
       and ir.session_id = p_session_id and ir.counted
  ) then
    v_counted := false;
  else
    v_counted := p_outcome = 'again' or v_was_due;
  end if;

  if v_counted then
    v_reps := v_reps + 1;
    if p_outcome = 'again' then
      v_box := 0;
      v_ease := greatest(1300, v_ease - 200);
      v_streak := 0;
      v_lapses := v_lapses + 1;
      v_interval_hours := 4.0 * v_ease / 1000.0;
    else
      v_box := least(v_box + 1, 5);
      v_ease := least(3000, v_ease + 60);
      v_streak := v_streak + 1;
      v_interval_hours := case v_box
        when 0 then 4.0 when 1 then 24.0 when 2 then 72.0
        when 3 then 168.0 when 4 then 384.0 else 840.0
      end * v_ease / 1000.0;
    end if;
    v_due_at := v_now + make_interval(secs => (v_interval_hours * 3600)::double precision);
    update public.srs_state st
       set box = v_box, ease_milli = v_ease, streak = v_streak, reps = v_reps,
           lapses = v_lapses, due_at = v_due_at, last_reviewed_at = v_now,
           last_outcome = p_outcome
     where st.user_id = p_user_id and st.item_id = p_item_id;
  end if;

  insert into public.item_reviews (
    institution_id, user_id, course_id, skill_id, item_id, session_id,
    mode, outcome, was_due, counted, idempotency_key
  ) values (
    p_institution_id, p_user_id, p_course_id, v_skill_id, p_item_id, p_session_id,
    p_mode, p_outcome, v_was_due, v_counted, p_idempotency_key
  );

  if p_mode <> 'quiz' or p_affects_mastery then
    insert into public.evidence_events (
      institution_id, user_id, course_id, skill_id, type, correct, latency_ms, hints_used
    ) values (
      p_institution_id, p_user_id, p_course_id, v_skill_id,
      case when p_mode = 'quiz' then 'practice' else 'flashcard' end,
      p_outcome = 'good', p_latency_ms, 0
    );

  end if;

  if p_mode = 'quiz' and p_affects_mastery then
    -- Match app.twin.tracer.apply_evidence exactly: 0.15 update toward the
    -- graded target, default prior 0.5, and one attempts increment.
    perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || ':' || v_skill_id::text, 0));
    select ms.estimate, ms.attempts into v_prior, v_attempts
      from public.mastery_state ms
     where ms.user_id = p_user_id and ms.skill_id = v_skill_id
     for update;
    if not found then
      v_prior := 0.5;
      v_attempts := 0;
    end if;
    v_target := case when p_outcome = 'good' then 1.0 else 0.0 end;
    v_mastery_estimate := greatest(0.0, least(1.0, v_prior + 0.15 * (v_target - v_prior)));
    insert into public.mastery_state (
      institution_id, user_id, course_id, skill_id, estimate, attempts, last_seen
    ) values (
      p_institution_id, p_user_id, p_course_id, v_skill_id,
      v_mastery_estimate, v_attempts + 1, v_now
    ) on conflict (user_id, skill_id) do update
      set estimate = excluded.estimate,
          attempts = excluded.attempts,
          last_seen = excluded.last_seen
    returning estimate into v_mastery_estimate;
  end if;

  if p_mode = 'quiz' and not p_affects_mastery then
    select ms.estimate into v_mastery_estimate from public.mastery_state ms
     where ms.user_id = p_user_id and ms.skill_id = v_skill_id;
  end if;

  select st.last_outcome into v_last_outcome
    from public.srs_state st
   where st.user_id = p_user_id and st.item_id = p_item_id;
  return query select v_counted, v_was_due, v_box, v_ease, v_streak, v_reps, v_lapses, v_last_outcome,
    v_due_at, (v_box >= 5 and v_streak >= 3), v_replayed, v_mastery_estimate;
end;
$$;

revoke all on function public.review_flashcard(uuid, uuid, uuid, uuid, text, text, uuid, text, integer, boolean)
  from public, anon, authenticated;
grant execute on function public.review_flashcard(uuid, uuid, uuid, uuid, text, text, uuid, text, integer, boolean)
  to service_role;

create function public.submit_practice(
  p_institution_id uuid,
  p_user_id uuid,
  p_course_id uuid,
  p_item_id uuid,
  p_choice_id text,
  p_set_id uuid,
  p_session_id uuid,
  p_idempotency_key text,
  p_latency_ms integer default 0,
  p_attempt_id uuid default null
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
  transaction_ms numeric,
  attempt_id uuid,
  attempt_number smallint
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
  v_attempt_id uuid;
  v_attempt_number smallint;
  v_attempt_completed_at timestamptz;
  v_set_item_count integer := 0;
begin
  if p_idempotency_key is null or length(p_idempotency_key) = 0 then
    raise exception 'idempotency key is required' using errcode = '22023';
  end if;

  -- Serialize set lifecycle transitions (attempt creation/completion) and
  -- preserve the existing per-answer lock used for duplicate submissions.
  if p_set_id is not null then
    perform pg_advisory_xact_lock(hashtextextended(
      p_user_id::text || ':practice-set:' || p_set_id::text, 0));
  end if;
  perform pg_advisory_xact_lock(hashtextextended(
    p_user_id::text || ':practice:' || coalesce(p_set_id::text, p_idempotency_key) || ':' || p_item_id::text, 0));

  -- Idempotency replay precedes attempt resolution and returns the immutable
  -- snapshot from the original request.
  select r.* into v_saved
    from public.practice_answer_results r
   where r.user_id = p_user_id and r.idempotency_key = p_idempotency_key
   limit 1;
  if found then
    if v_saved.item_id <> p_item_id
       or v_saved.set_id is distinct from p_set_id
       or (p_attempt_id is not null and v_saved.attempt_id is distinct from p_attempt_id) then
      raise exception 'idempotency key already used for another answer' using errcode = '23505';
    end if;
    if v_saved.attempt_id is not null then
      select qsa.attempt_number into v_attempt_number
        from public.quiz_set_attempts qsa where qsa.id = v_saved.attempt_id;
    end if;
    return query select v_saved.correct, v_saved.explanation, v_saved.mastery_after, true,
      v_saved.correct_option_id, v_saved.correct_answer_text, v_saved.choice_id,
      v_saved.choice_text, v_saved.prompt, v_saved.choices, v_saved.xp_awarded,
      v_saved.mastery_before, v_saved.mastery_before_level, v_saved.mastery_after,
      v_saved.mastery_after_level, 0::numeric, 0::numeric, 0::numeric, 0::numeric,
      0::numeric, 0::numeric, 0::numeric, v_saved.attempt_id, v_attempt_number;
    return;
  end if;

  if p_set_id is not null then
    if p_attempt_id is not null then
      select qsa.id, qsa.attempt_number, qsa.completed_at
        into v_attempt_id, v_attempt_number, v_attempt_completed_at
        from public.quiz_set_attempts qsa
       where qsa.id = p_attempt_id and qsa.user_id = p_user_id
         and qsa.set_id = p_set_id and qsa.course_id = p_course_id
         and qsa.institution_id = p_institution_id;
      if not found then
        raise exception 'attempt not found' using errcode = 'P0002';
      end if;
    else
      select qsa.id, qsa.attempt_number, qsa.completed_at
        into v_attempt_id, v_attempt_number, v_attempt_completed_at
        from public.quiz_set_attempts qsa
       where qsa.user_id = p_user_id and qsa.set_id = p_set_id
       order by qsa.attempt_number desc limit 1;
      if not found then
        insert into public.quiz_set_attempts (
          institution_id, user_id, course_id, set_id, attempt_number
        ) values (p_institution_id, p_user_id, p_course_id, p_set_id, 1)
        returning id, attempt_number, completed_at
          into v_attempt_id, v_attempt_number, v_attempt_completed_at;
      end if;
    end if;

    -- Completed attempts reject all new submissions. Exact retries with the
    -- original idempotency key were returned above.
    if v_attempt_completed_at is not null then
      raise exception 'attempt_complete' using errcode = 'P0001';
    end if;

    -- A different idempotency key for an already-answered item in this same
    -- in-progress attempt is also a replay; it must not write another review.
    select r.* into v_saved
      from public.practice_answer_results r
     where r.user_id = p_user_id and r.attempt_id = v_attempt_id
       and r.item_id = p_item_id
     limit 1;
    if found then
      return query select v_saved.correct, v_saved.explanation, v_saved.mastery_after, true,
        v_saved.correct_option_id, v_saved.correct_answer_text, v_saved.choice_id,
        v_saved.choice_text, v_saved.prompt, v_saved.choices, v_saved.xp_awarded,
        v_saved.mastery_before, v_saved.mastery_before_level, v_saved.mastery_after,
        v_saved.mastery_after_level, 0::numeric, 0::numeric, 0::numeric, 0::numeric,
        0::numeric, 0::numeric, 0::numeric, v_attempt_id, v_attempt_number;
      return;
    end if;

    select count(*) into v_set_item_count
      from public.quiz_set_items qsi where qsi.set_id = p_set_id;
    if v_set_item_count = 0 then
      select count(*) into v_set_item_count
        from public.generated_items gi
       where gi.set_id = p_set_id and gi.institution_id = p_institution_id
         and gi.retired_at is null;
    end if;
  end if;

  if p_set_id is not null then
    v_stage_started := clock_timestamp();
    if exists (
      select 1 from public.quiz_set_items qsi
      join public.quiz_sets qs on qs.id = qsi.set_id
      where qsi.set_id = p_set_id and qsi.item_id = p_item_id
        and qs.course_id = p_course_id and qs.institution_id = p_institution_id
    ) then
      null;
    elsif exists (
      select 1 from public.quiz_sets qs
      join public.generated_items gi on gi.set_id = qs.id
      where qs.id = p_set_id and qs.course_id = p_course_id
        and qs.institution_id = p_institution_id and gi.id = p_item_id
        and gi.institution_id = p_institution_id and gi.retired_at is null
    ) then
      null;
    else
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
    'quiz', p_session_id, p_idempotency_key, p_latency_ms,
    (v_attempt_number = 1 or p_set_id is null)
  );
  v_review_rpc_ms := extract(epoch from clock_timestamp() - v_stage_started) * 1000;
  v_mastery_after := v_review.mastery_estimate;
  v_mastery_after_level := case
    when v_mastery_after is null then 'No evidence'
    when v_mastery_after < 0.4 then 'Developing'
    when v_mastery_after < 0.7 then 'Proficient'
    else 'Mastered' end;
  v_xp_awarded := case
    when p_set_id is null then case when v_review.counted then 2 + case when v_correct then 10 else 0 end else 0 end
    when v_attempt_number = 1 then 2 + case when v_correct then 10 else 0 end
    else 0 end;

  if p_set_id is not null then
    v_stage_started := clock_timestamp();
    update public.quiz_set_attempts qsa
       set attempted_count = (qsa.attempted_count + 1)::smallint,
           correct_count = (qsa.correct_count + case when v_correct then 1 else 0 end)::smallint,
           last_attempted_at = now(),
           completed_at = case
             when qsa.attempted_count + 1 >= v_set_item_count then now()
             else qsa.completed_at end
     where qsa.id = v_attempt_id and qsa.user_id = p_user_id and qsa.set_id = p_set_id;
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
    institution_id, user_id, course_id, set_id, item_id, skill_id, session_id, attempt_id,
    idempotency_key, prompt, choices, choice_id, choice_text,
    correct_option_id, correct_answer_text, explanation, correct, xp_awarded,
    mastery_before, mastery_before_level, mastery_after, mastery_after_level
  ) values (
    p_institution_id, p_user_id, p_course_id, p_set_id, p_item_id, v_skill_id, p_session_id, v_attempt_id,
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
    extract(epoch from clock_timestamp() - v_started) * 1000, v_attempt_id, v_attempt_number;
end;
$$;

revoke all on function public.submit_practice(uuid, uuid, uuid, uuid, text, uuid, uuid, text, integer, uuid)
  from public, anon, authenticated;
grant execute on function public.submit_practice(uuid, uuid, uuid, uuid, text, uuid, uuid, text, integer, uuid)
  to service_role;


create or replace function public.start_practice_retake(
  p_institution_id uuid,
  p_user_id uuid,
  p_course_id uuid,
  p_set_id uuid
)
returns table(attempt_id uuid, attempt_number smallint)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_latest_id uuid;
  v_latest_number smallint;
  v_completed_at timestamptz;
  v_set_institution_id uuid;
  v_set_course_id uuid;
begin
  perform pg_advisory_xact_lock(hashtextextended(
    p_user_id::text || ':practice-set:' || p_set_id::text, 0));

  select qs.institution_id, qs.course_id into v_set_institution_id, v_set_course_id
    from public.quiz_sets qs
   where qs.id = p_set_id;
  if not found or v_set_institution_id <> p_institution_id or v_set_course_id <> p_course_id then
    raise exception 'set not found' using errcode = 'P0002';
  end if;

  select qsa.id, qsa.attempt_number, qsa.completed_at
    into v_latest_id, v_latest_number, v_completed_at
    from public.quiz_set_attempts qsa
   where qsa.institution_id = p_institution_id and qsa.user_id = p_user_id
     and qsa.course_id = p_course_id and qsa.set_id = p_set_id
   order by qsa.attempt_number desc limit 1;
  if not found then
    raise exception 'no_attempt' using errcode = 'P0001';
  end if;
  if v_completed_at is null then
    raise exception 'attempt_in_progress' using errcode = 'P0001';
  end if;

  return query insert into public.quiz_set_attempts (
    institution_id, user_id, course_id, set_id, attempt_number
  ) values (
    p_institution_id, p_user_id, p_course_id, p_set_id, v_latest_number + 1
  ) returning id, quiz_set_attempts.attempt_number;
end;
$$;

revoke all on function public.start_practice_retake(uuid, uuid, uuid, uuid)
  from public, anon, authenticated;
grant execute on function public.start_practice_retake(uuid, uuid, uuid, uuid)
  to service_role;

notify pgrst, 'reload schema';
commit;
