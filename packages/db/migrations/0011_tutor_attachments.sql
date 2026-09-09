-- =====================================================================
-- Kala — 0011_tutor_attachments.sql
-- Private study-aid uploads for the tutor (AI overhaul Stage 4, see
-- docs/AI_OVERHAUL_TODO.md). A student's own notes/PDF, usable ONLY as
-- extra context inside their own tutor conversation.
--
-- Explicit product decision behind the "private" part: this does NOT
-- feed the shared RAG ingest pipeline (content_items / chunk / embed).
-- That pipeline is for institution-approved course material with a
-- skill-proposal review gate — mixing a student's own uploaded material
-- into it would leak into every other student's tutor retrieval with no
-- review step, and for anything like a scanned textbook page, would be a
-- straightforward copyright problem the moment it's re-served to someone
-- else. Scoped instead to exactly one student's own conversation, same
-- self-only shape as tutor_conversations/tutor_messages (0010).
--
-- Storage: a private Supabase Storage bucket, not a new S3 bucket. Every
-- other piece of this project's data layer already runs through
-- Supabase Postgres + RLS keyed off auth.uid() — Storage buckets use the
-- exact same RLS mechanism against the same auth.uid(), so this is the
-- one option that adds no new access pattern, no new AWS console/
-- Terraform step, just another bucket policy alongside the table
-- policies already here. Extraction happens synchronously in the API on
-- upload (small files, no job queue in this stack for it) — see
-- routers/tutor.py.
-- =====================================================================

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'tutor-attachments',
  'tutor-attachments',
  false,  -- private: never served by a public URL, only through the API
  5242880,  -- 5 MB per file — a study note or a short PDF, not a textbook
  array['text/plain', 'text/markdown', 'application/pdf']
)
on conflict (id) do nothing;

-- Path convention: {user_id}/{conversation_id}/{attachment_id}-{filename}.
-- storage.foldername(name) splits the object path on '/', so
-- (storage.foldername(name))[1] is the user_id segment — the standard
-- documented Supabase pattern for "a user can only touch their own
-- folder," reused here rather than inventing a different shape.
create policy tutor_attachments_object_read on storage.objects for select to authenticated
  using (bucket_id = 'tutor-attachments' and (storage.foldername(name))[1] = auth.uid()::text);

-- Uploads go through the API (service role), not a direct browser upload
-- to Storage — same "writes go through the service role" shape as every
-- table in this project. No authenticated insert/update/delete policy on
-- storage.objects for this bucket, on purpose.


-- ---- tutor_attachments: metadata + extracted text ---------------------
create table public.tutor_attachments (
  id              uuid primary key default gen_random_uuid(),
  institution_id  uuid not null references public.institutions(id) on delete cascade,
  user_id         uuid not null references public.users(id) on delete cascade,
  conversation_id uuid not null references public.tutor_conversations(id) on delete cascade,
  -- Full path inside the tutor-attachments bucket, matching the
  -- {user_id}/{conversation_id}/{id}-{filename} convention above.
  storage_path    text not null,
  filename        text not null,
  mime_type       text not null,
  size_bytes      integer not null,
  -- 'processing' briefly while extraction runs synchronously on upload;
  -- 'ready' once extracted_text is populated; 'failed' if extraction
  -- errored (corrupt PDF, unsupported content) — the file is still kept,
  -- just contributes no context to the conversation.
  status          text not null default 'processing'
                    check (status in ('processing', 'ready', 'failed')),
  -- Plain extracted text, fed into the tutor's prompt alongside the
  -- course-content RAG context when this conversation is asked in.
  -- Null until status = 'ready'.
  extracted_text  text,
  created_at      timestamptz not null default now()
);
create index tutor_attachments_conversation_idx
  on public.tutor_attachments (conversation_id, created_at);

alter table public.tutor_attachments enable row level security;

create policy tutor_attachments_read on public.tutor_attachments for select to authenticated
  using (user_id = auth.uid());

-- Writes go through the service role (the API), never the browser, same
-- as tutor_conversations/tutor_messages. No authenticated insert/update/
-- delete policy on purpose.
grant select on public.tutor_attachments to authenticated;
