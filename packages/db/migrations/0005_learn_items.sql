-- =====================================================================
-- Kala — 0005_learn_items.sql
-- Phase 3 (Learn Loop): server-generated diagnostic/practice/flashcard
-- items. Items are RAG-grounded (see app/learn/items.py) and persisted so
-- grading happens against the stored answer key, never a client claim.
-- Mirrors the content_items access pattern: students never read this table
-- directly (RLS is staff-only); they receive a sanitized view through the
-- API, which uses the service_role key.
-- =====================================================================

create table public.generated_items (
  id                 uuid primary key default gen_random_uuid(),
  institution_id     uuid not null references public.institutions(id) on delete cascade,
  course_id          uuid not null references public.courses(id) on delete cascade,
  skill_id           uuid references public.skills(id) on delete set null,
  kind               text not null check (kind in ('diagnostic','practice','flashcard')),
  bloom_level        text check (bloom_level in
                       ('remember','understand','apply','analyze','evaluate','create')),
  prompt             text not null,          -- question prompt, or flashcard front
  choices            jsonb,                  -- [{id,label}], null for flashcards
  correct_choice_id  text,                   -- null for flashcards; never sent to the client
  explanation        text,
  front              text,                   -- flashcard front (duplicate of prompt for clarity)
  back               text,                   -- flashcard back / answer
  source_content_id  uuid references public.content_items(id) on delete set null,
  created_at         timestamptz not null default now()
);
create index generated_items_course_idx on public.generated_items (course_id, skill_id);
create index generated_items_kind_idx on public.generated_items (kind, created_at);

alter table public.generated_items enable row level security;

create policy items_read on public.generated_items for select to authenticated
  using (public.is_staff() and institution_id = public.current_institution());

grant select on public.generated_items to authenticated;
