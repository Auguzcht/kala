-- Embedding dimension matches public.content_items.embedding vector(1024)
-- (packages/db/migrations/0001_init.sql:153; also used by 0004_rag.sql).
begin;

alter table public.generated_items
  add column if not exists embedding vector(1024) null,
  add column if not exists embedded_at timestamptz null;

alter table public.guided_lesson_steps
  add column if not exists embedding vector(1024) null;

notify pgrst, 'reload schema';
commit;
