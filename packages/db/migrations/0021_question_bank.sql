-- =====================================================================
-- Kala — 0021_question_bank.sql
-- Question-bank storage and on-demand worker coordination state.
--
-- This migration only adds schema/IAM prerequisites. No current API,
-- worker, or frontend path reads or writes these new tables yet.
-- worker_state is intentionally global operational state, not tenant data;
-- it therefore has no institution_id column.
-- =====================================================================

-- ---- generated_items: bank identity and retirement metadata -------------
alter table public.generated_items
  add column if not exists origin text not null default 'legacy',
  add column if not exists retired_at timestamptz,
  add column if not exists generation_version text,
  add column if not exists stem_hash text;

alter table public.generated_items
  add constraint generated_items_origin_check
  check (origin in ('legacy', 'bank'));

create unique index generated_items_bank_stem_uidx
  on public.generated_items (course_id, skill_id, stem_hash)
  where origin = 'bank' and retired_at is null;

create index generated_items_bank_pick_idx
  on public.generated_items (course_id, skill_id, origin)
  where retired_at is null;

-- ---- set membership: preserve legacy set_id, add reusable membership ------
create table public.quiz_set_items (
  set_id    uuid not null references public.quiz_sets(id) on delete cascade,
  item_id   uuid not null references public.generated_items(id) on delete no action,
  position  smallint not null,
  primary key (set_id, position),
  unique (set_id, item_id)
);

-- Keep existing sets readable after the bank cutover. generated_items.set_id
-- remains untouched for legacy rows and is not written for new bank rows.
insert into public.quiz_set_items (set_id, item_id, position)
select set_id, id,
       row_number() over (partition by set_id order by created_at, id)::smallint - 1
from public.generated_items
where set_id is not null;

alter table public.quiz_set_items enable row level security;

create policy quiz_set_items_read on public.quiz_set_items for select to authenticated
  using (
    public.is_staff()
    and exists (
      select 1
      from public.quiz_sets qs
      where qs.id = quiz_set_items.set_id
        and qs.institution_id = public.current_institution()
    )
  );

grant select on public.quiz_set_items to authenticated;

-- ---- per-student study/test exposure state -------------------------------
create table public.item_exposures (
  institution_id    uuid not null references public.institutions(id) on delete cascade,
  user_id           uuid not null references public.users(id) on delete cascade,
  course_id         uuid not null references public.courses(id) on delete cascade,
  skill_id          uuid not null references public.skills(id) on delete cascade,
  item_id           uuid not null references public.generated_items(id) on delete cascade,
  last_studied_at   timestamptz,
  last_tested_at    timestamptz,
  last_answered_at  timestamptz,
  last_correct      boolean,
  times_tested     integer not null default 0,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  primary key (user_id, item_id)
);

create index item_exposures_user_course_skill_idx
  on public.item_exposures (user_id, course_id, skill_id);

alter table public.item_exposures enable row level security;

create policy item_exposures_read on public.item_exposures for select to authenticated
  using (
    user_id = auth.uid()
    or public.teaches(course_id)
    or (public.is_admin() and institution_id = public.current_institution())
  );

grant select on public.item_exposures to authenticated;

-- ---- per-skill bank build state ------------------------------------------
create table public.skill_bank_state (
  institution_id        uuid not null references public.institutions(id) on delete cascade,
  course_id             uuid not null references public.courses(id) on delete cascade,
  skill_id              uuid not null references public.skills(id) on delete cascade,
  status                text not null default 'waiting_content'
                        check (status in ('waiting_content', 'building', 'ready', 'no_material', 'error')),
  mcq_target            integer not null,
  mcq_ready             integer not null default 0,
  depth                 integer not null default 0,
  leased_until          timestamptz,
  next_attempt_at       timestamptz,
  consecutive_failures  integer not null default 0,
  last_error            text,
  updated_at            timestamptz not null default now(),
  unique (course_id, skill_id)
);

alter table public.skill_bank_state enable row level security;
revoke all on public.skill_bank_state from anon, authenticated;

-- ---- global worker coordination state ------------------------------------
create table public.worker_state (
  key        text primary key,
  value      jsonb,
  updated_at timestamptz not null default now()
);

alter table public.worker_state enable row level security;
revoke all on public.worker_state from anon, authenticated;

-- ---- course-level bank lifecycle flags -----------------------------------
alter table public.courses
  add column if not exists bank_kicked_at timestamptz,
  add column if not exists bank_serving boolean not null default false;
