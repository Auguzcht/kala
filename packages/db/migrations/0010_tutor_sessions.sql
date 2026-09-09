-- =====================================================================
-- Kala — 0010_tutor_sessions.sql
-- Tutor conversation persistence (AI overhaul Stage 2, see
-- docs/AI_OVERHAUL_TODO.md). The freeform tutor (/tutor/ask) has been
-- stateless since it was first built: no conversation_id, nothing
-- persisted, each question independent, gone on refresh. This gives it
-- real history, the same way guided lessons already have a persistent
-- record instead of being regenerated per visit.
--
-- Two tables:
--   tutor_conversations — one row per chat thread. Optionally scoped to a
--     skill (a "Ask a question" opened from inside a lesson step, kept
--     scoped to that skill's content) or course-wide freeform (skill_id
--     null).
--   tutor_messages — the turns within a conversation, in order. `style`
--     records which framing produced an assistant turn (default / eli5 /
--     detail — the SAME three values routers/tutor.py's _STYLE_HINTS
--     already supports server-side; this migration doesn't add new
--     styles, it just gives the existing ones somewhere to be recorded).
--
-- Deliberate scope decision: conversations are SELF-ONLY, no course-staff
-- read override. Unlike evidence_events / srs_state (explicitly built for
-- the instructor drill-down), a tutor conversation is a private study
-- session, not evidence the teacher loop currently reads. If a future
-- feature needs instructor visibility into tutor chats, that's a new
-- product decision to make deliberately, not something to default into
-- here by copying the evidence_events policy shape.
-- =====================================================================

create table public.tutor_conversations (
  id             uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  course_id      uuid not null references public.courses(id) on delete cascade,
  user_id        uuid not null references public.users(id) on delete cascade,
  -- Null = general freeform chat for the course. Set when opened as
  -- "Ask a question" from inside a specific lesson step, so retrieval for
  -- every turn in that conversation stays scoped to that skill's content
  -- (same de-identified, RAG-grounded contract tutor.py already enforces
  -- per call — this just lets a whole conversation share one scope
  -- instead of re-deciding it per message).
  skill_id       uuid references public.skills(id) on delete set null,
  -- Derived from the first user message once one exists; nullable until
  -- then rather than defaulting to a placeholder string. The API sets
  -- this, not the client.
  title          text,
  created_at     timestamptz not null default now(),
  -- Bumped on every new message so a conversation list can sort by
  -- "most recently active" without a join into tutor_messages.
  updated_at     timestamptz not null default now()
);
create index tutor_conversations_user_idx
  on public.tutor_conversations (user_id, course_id, updated_at desc);

create table public.tutor_messages (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.tutor_conversations(id) on delete cascade,
  role            text not null check (role in ('user', 'assistant')),
  content         text not null,
  -- Which framing produced this turn. Null for user messages (the style
  -- is a property of the ASK, recorded on the assistant reply it
  -- produced) and for assistant replies predating this column's use.
  style           text check (style in ('default', 'eli5', 'detail')),
  created_at      timestamptz not null default now()
);
create index tutor_messages_conversation_idx
  on public.tutor_messages (conversation_id, created_at);

alter table public.tutor_conversations enable row level security;
alter table public.tutor_messages      enable row level security;

create policy tutor_conversations_read on public.tutor_conversations for select to authenticated
  using (user_id = auth.uid());

create policy tutor_messages_read on public.tutor_messages for select to authenticated
  using (
    exists (
      select 1 from public.tutor_conversations tc
      where tc.id = tutor_messages.conversation_id
        and tc.user_id = auth.uid()
    )
  );

-- Writes go through the service role (the API), never the browser, same
-- as every other learn-loop table. No authenticated insert/update/delete
-- policy on purpose.
grant select on public.tutor_conversations to authenticated;
grant select on public.tutor_messages      to authenticated;
