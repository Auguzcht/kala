-- Append-only card review history. Flashcard ratings and practice answers
-- share this log; evidence_events remains the research-facing ledger.
create table if not exists public.item_reviews (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null,
  user_id uuid not null,
  course_id uuid not null,
  skill_id uuid,
  item_id uuid not null references public.generated_items(id) on delete no action,
  session_id uuid,
  mode text not null check (mode in ('flashcard', 'quiz')),
  outcome text not null check (outcome in ('again', 'good')),
  was_due boolean not null,
  counted boolean not null,
  idempotency_key text not null,
  created_at timestamptz not null default now(),
  unique (user_id, idempotency_key)
);

create index if not exists item_reviews_user_item_created_idx
  on public.item_reviews (user_id, item_id, created_at);
create index if not exists item_reviews_course_created_idx
  on public.item_reviews (course_id, created_at);
create unique index if not exists item_reviews_first_session_rating_idx
  on public.item_reviews (user_id, item_id, session_id)
  where counted and session_id is not null;

alter table public.item_reviews enable row level security;
drop policy if exists item_reviews_read on public.item_reviews;
create policy item_reviews_read on public.item_reviews for select to authenticated
  using (
    user_id = auth.uid()
    or public.teaches(course_id)
    or (public.is_admin() and institution_id = public.current_institution())
  );
grant select on public.item_reviews to authenticated;
drop trigger if exists t_immutable on public.item_reviews;
create trigger t_immutable before update or delete on public.item_reviews
  for each row execute function public.forbid_mutation();

-- The RPC keeps idempotency, the session guard, row locking, scheduling,
-- evidence logging, and item_reviews insertion in one transaction.
drop function if exists public.review_flashcard(uuid, uuid, uuid, uuid, text, text, uuid, text, integer);
create function public.review_flashcard(
  p_institution_id uuid,
  p_user_id uuid,
  p_course_id uuid,
  p_item_id uuid,
  p_outcome text,
  p_mode text,
  p_session_id uuid,
  p_idempotency_key text,
  p_latency_ms integer default 0
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
  replayed boolean
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
    return query select v_counted, false, v_box, v_ease, v_streak, v_reps, v_lapses, v_last_outcome,
      v_due_at, (v_box >= 5 and v_streak >= 3), true;
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

  insert into public.evidence_events (
    institution_id, user_id, course_id, skill_id, type, correct, latency_ms, hints_used
  ) values (
    p_institution_id, p_user_id, p_course_id, v_skill_id, 'flashcard',
    p_outcome = 'good', p_latency_ms, 0
  );

  select st.last_outcome into v_last_outcome
    from public.srs_state st
   where st.user_id = p_user_id and st.item_id = p_item_id;
  return query select v_counted, v_was_due, v_box, v_ease, v_streak, v_reps, v_lapses, v_last_outcome,
    v_due_at, (v_box >= 5 and v_streak >= 3), v_replayed;
end;
$$;

revoke all on function public.review_flashcard(uuid, uuid, uuid, uuid, text, text, uuid, text, integer)
  from public, anon, authenticated;
grant execute on function public.review_flashcard(uuid, uuid, uuid, uuid, text, text, uuid, text, integer)
  to service_role;
