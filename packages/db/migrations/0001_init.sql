-- =====================================================================
-- Kala — 0001_init.sql
-- Core schema: extensions, helper functions, tables, triggers.
-- Multi-tenant by institution_id. Identity originates from the LMS via LTI;
-- Supabase stores a pseudonymous mirror + the learning-intelligence layer +
-- governance/audit. SOC 2 / ISO 27001 aligned: default-deny RLS (in 0002),
-- immutable audit + evidence, PII separated and purgeable, least privilege.
-- Target: Supabase (PostgreSQL 15).
-- =====================================================================

create extension if not exists pgcrypto;   -- gen_random_uuid()
create extension if not exists vector;      -- pgvector, RAG embeddings

-- ---------------------------------------------------------------------
-- Helper functions used by RLS and views.
-- security definer where they must read tables regardless of the caller's
-- RLS (prevents recursion). search_path pinned to avoid hijacking.
-- ---------------------------------------------------------------------

create or replace function public.current_institution()
returns uuid language sql stable
set search_path = ''
as $$ select nullif(auth.jwt() ->> 'institution_id', '')::uuid $$;

create or replace function public.current_app_role()
returns text language sql stable
set search_path = ''
as $$ select auth.jwt() ->> 'app_role' $$;

create or replace function public.is_admin()
returns boolean language sql stable
set search_path = ''
as $$ select public.current_app_role() = 'admin' $$;

create or replace function public.is_staff()
returns boolean language sql stable
set search_path = ''
as $$ select public.current_app_role() in ('instructor','admin') $$;

-- NOTE: helpers that read application tables (teaches, has_grant, has_consent)
-- are defined AFTER those tables, further below, because SQL function bodies
-- are validated at creation time.

-- Generic updated_at maintainer.
create or replace function public.set_updated_at()
returns trigger language plpgsql
set search_path = ''
as $$ begin new.updated_at = now(); return new; end $$;

-- Block UPDATE/DELETE on append-only tables (fires for every role, including
-- service_role, so evidence and audit trails are tamper-resistant).
create or replace function public.forbid_mutation()
returns trigger language plpgsql
set search_path = ''
as $$ begin
  raise exception 'append-only table: % not allowed on %', tg_op, tg_table_name;
end $$;

-- ---------------------------------------------------------------------
-- Tenancy + identity
-- ---------------------------------------------------------------------

create table public.institutions (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  lms_type      text not null check (lms_type in ('blackboard','canvas')),
  lms_issuer    text not null,                 -- LTI iss
  deployment_id text not null,                 -- LTI deployment_id
  region        text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (lms_issuer, deployment_id)
);

-- Pseudonymous anchor. NO direct PII here (see user_profiles). id equals the
-- JWT `sub` the backend mints after LTI validation, so auth.uid() = users.id.
create table public.users (
  id             uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  lms_user_id    text not null,                -- LMS-internal id (sensitive)
  role           text not null check (role in ('student','instructor','admin')),
  pseudonym      text not null,                -- used in model calls / analytics
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (institution_id, lms_user_id)
);

-- PII separated so it can be purged on erasure (crypto-shred): deleting this
-- row leaves evidence linked only to a pseudonymous users.id.
create table public.user_profiles (
  user_id      uuid primary key references public.users(id) on delete cascade,
  display_name text,
  email        text,
  updated_at   timestamptz not null default now()
);

-- Security log of LTI launches (append-only). Backend inserts on each launch.
create table public.lti_launches (
  id             uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  user_id        uuid references public.users(id) on delete set null,
  course_id      uuid,
  role           text,
  message_type   text,
  ip             inet,
  user_agent     text,
  occurred_at    timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Academic mirror (thin references to the LMS; not the content system)
-- ---------------------------------------------------------------------

create table public.courses (
  id             uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  lms_course_id  text not null,
  title          text not null,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (institution_id, lms_course_id)
);

create table public.enrollments (
  institution_id uuid not null references public.institutions(id) on delete cascade,
  user_id        uuid not null references public.users(id) on delete cascade,
  course_id      uuid not null references public.courses(id) on delete cascade,
  role           text not null check (role in ('student','instructor')),
  created_at     timestamptz not null default now(),
  primary key (user_id, course_id)
);

create table public.skills (
  id               uuid primary key default gen_random_uuid(),
  institution_id   uuid not null references public.institutions(id) on delete cascade,
  course_id        uuid not null references public.courses(id) on delete cascade,
  name             text not null,
  bloom_level      text not null check (bloom_level in
                     ('remember','understand','apply','analyze','evaluate','create')),
  blueprint_weight numeric not null default 1.0,
  created_at       timestamptz not null default now()
);

-- Minimal chunks + embeddings for RAG. Store only what retrieval needs, with
-- institution permission; the LMS remains the content system of record.
create table public.content_items (
  id             uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  course_id      uuid not null references public.courses(id) on delete cascade,
  skill_id       uuid references public.skills(id) on delete set null,
  lms_ref        text,
  chunk_text     text,
  embedding      vector(1024),                 -- match your embedding model dims
  created_at     timestamptz not null default now()
);
create index content_items_embedding_idx on public.content_items
  using hnsw (embedding vector_cosine_ops);

create table public.assessments (
  id             uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  course_id      uuid not null references public.courses(id) on delete cascade,
  skill_id       uuid references public.skills(id) on delete set null,
  lms_ref        text,
  title          text,
  created_at     timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Learning intelligence (the twin)
-- ---------------------------------------------------------------------

-- APPEND-ONLY. The research dataset and the audit trail of learning.
create table public.evidence_events (
  id             uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  user_id        uuid not null references public.users(id) on delete cascade,
  course_id      uuid not null references public.courses(id) on delete cascade,
  skill_id       uuid references public.skills(id) on delete set null,
  type           text not null check (type in ('diagnostic','practice','flashcard','tutor')),
  correct        boolean,
  latency_ms     integer,
  hints_used     integer not null default 0,
  created_at     timestamptz not null default now()
);
create index evidence_events_user_idx on public.evidence_events (user_id, created_at);
create index evidence_events_course_idx on public.evidence_events (course_id, created_at);

-- Derived state (recomputable from evidence). course_id denormalized for RLS.
create table public.mastery_state (
  institution_id uuid not null references public.institutions(id) on delete cascade,
  user_id        uuid not null references public.users(id) on delete cascade,
  course_id      uuid not null references public.courses(id) on delete cascade,
  skill_id       uuid not null references public.skills(id) on delete cascade,
  estimate       numeric not null default 0,
  attempts       integer not null default 0,
  last_seen      timestamptz,
  updated_at     timestamptz not null default now(),
  primary key (user_id, skill_id)
);

create table public.readiness_snapshots (
  id             uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  user_id        uuid not null references public.users(id) on delete cascade,
  course_id      uuid not null references public.courses(id) on delete cascade,
  score          numeric not null,
  created_at     timestamptz not null default now()
);

create table public.recommendations (
  id             uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  user_id        uuid not null references public.users(id) on delete cascade,
  course_id      uuid not null references public.courses(id) on delete cascade,
  skill_id       uuid references public.skills(id) on delete set null,
  action         text not null,
  rationale      text,
  created_at     timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Governance / compliance
-- ---------------------------------------------------------------------

create table public.consents (
  id             uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  user_id        uuid not null references public.users(id) on delete cascade,
  purpose        text not null default 'research',
  granted        boolean not null,
  policy_version text not null,
  created_at     timestamptz not null default now()
);
create index consents_user_idx on public.consents (user_id, purpose, created_at desc);

-- Researcher accounts use a SEPARATE portal (not LTI). Their JWT sub =
-- researchers.id, app_role='researcher'. No student PII here.
create table public.researchers (
  id           uuid primary key default gen_random_uuid(),
  email        text not null unique,
  display_name text,
  created_at   timestamptz not null default now()
);

create table public.researcher_grants (
  id             uuid primary key default gen_random_uuid(),
  researcher_id  uuid not null references public.researchers(id) on delete cascade,
  institution_id uuid not null references public.institutions(id) on delete cascade,
  scope          text not null default 'aggregate' check (scope in ('aggregate','row_anon')),
  status         text not null default 'active'    check (status in ('active','revoked')),
  granted_by     uuid,                           -- admin users.id
  expires_at     timestamptz not null,
  created_at     timestamptz not null default now()
);

create table public.data_subject_requests (
  id             uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  user_id        uuid not null references public.users(id) on delete cascade,
  kind           text not null check (kind in ('export','erasure')),
  status         text not null default 'pending' check (status in ('pending','processing','done','rejected')),
  requested_at   timestamptz not null default now(),
  resolved_at    timestamptz
);

-- APPEND-ONLY immutable audit trail (SOC 2 CC7 / ISO 27001 A.12.4).
create table public.audit_log (
  id             bigint generated always as identity primary key,
  occurred_at    timestamptz not null default now(),
  institution_id uuid,
  actor_id       uuid,          -- auth.uid()
  actor_role     text,          -- app_role
  action         text not null, -- INSERT | UPDATE | DELETE | EXPORT | LOGIN | GRANT | REVOKE
  table_name     text,
  row_id         text,
  old_data       jsonb,
  new_data       jsonb,
  metadata       jsonb
);
create index audit_log_inst_idx on public.audit_log (institution_id, occurred_at);

-- Table-reading helpers (defined here, after their tables exist).

-- Does the current user teach this course? (security definer reads enrollments)
create or replace function public.teaches(course uuid)
returns boolean language sql stable security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.enrollments e
    where e.course_id = course
      and e.user_id = auth.uid()
      and e.role = 'instructor'
  )
$$;

-- Does the current researcher hold an active grant for this institution?
create or replace function public.has_grant(inst uuid)
returns boolean language sql stable security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.researcher_grants g
    where g.researcher_id = auth.uid()
      and g.institution_id = inst
      and g.status = 'active'
      and now() < g.expires_at
  )
$$;

-- Has this subject consented to research use? (latest consent wins)
create or replace function public.has_consent(subject uuid)
returns boolean language sql stable security definer
set search_path = ''
as $$
  select coalesce((
    select c.granted from public.consents c
    where c.user_id = subject and c.purpose = 'research'
    order by c.created_at desc limit 1
  ), false)
$$;

-- Generic row-change auditor. Attach to sensitive tables.
create or replace function public.audit_row()
returns trigger language plpgsql security definer
set search_path = ''
as $$
declare j_old jsonb; j_new jsonb; inst uuid; rid text;
begin
  j_old := case when tg_op in ('UPDATE','DELETE') then to_jsonb(old) else null end;
  j_new := case when tg_op in ('INSERT','UPDATE') then to_jsonb(new) else null end;
  -- read fields from JSON so this works for any table shape (incl. no `id`)
  inst := nullif(coalesce(j_new ->> 'institution_id', j_old ->> 'institution_id'), '')::uuid;
  rid  := coalesce(j_new ->> 'id', j_old ->> 'id');  -- null for composite-key tables
  insert into public.audit_log(institution_id, actor_id, actor_role, action, table_name, row_id, old_data, new_data)
  values (inst, auth.uid(), public.current_app_role(), tg_op, tg_table_name, rid, j_old, j_new);
  return case when tg_op = 'DELETE' then old else new end;
end $$;

-- ---------------------------------------------------------------------
-- Triggers
-- ---------------------------------------------------------------------

create trigger t_updated_at before update on public.institutions  for each row execute function public.set_updated_at();
create trigger t_updated_at before update on public.users         for each row execute function public.set_updated_at();
create trigger t_updated_at before update on public.user_profiles for each row execute function public.set_updated_at();
create trigger t_updated_at before update on public.courses       for each row execute function public.set_updated_at();
create trigger t_updated_at before update on public.mastery_state for each row execute function public.set_updated_at();

create trigger t_immutable before update or delete on public.evidence_events for each row execute function public.forbid_mutation();
create trigger t_immutable before update or delete on public.lti_launches    for each row execute function public.forbid_mutation();
create trigger t_immutable before update or delete on public.audit_log       for each row execute function public.forbid_mutation();

create trigger t_audit after insert or update or delete on public.consents              for each row execute function public.audit_row();
create trigger t_audit after insert or update or delete on public.researcher_grants     for each row execute function public.audit_row();
create trigger t_audit after insert or update or delete on public.data_subject_requests for each row execute function public.audit_row();
create trigger t_audit after insert or update or delete on public.enrollments           for each row execute function public.audit_row();
