# Migration 0036 application record

Applied manually by the user in the Supabase SQL editor on 2026-10-18.
The migration adds only nullable embedding columns:

- `generated_items.embedding vector(1024)`
- `generated_items.embedded_at timestamptz`
- `guided_lesson_steps.embedding vector(1024)`

The dimension matches `content_items.embedding vector(1024)` in
`packages/db/migrations/0001_init.sql:153`.

## Read-only verification

After the manual application, the API REST client ran:

```sql
select id, embedding, embedded_at from generated_items limit 1;
select id, embedding from guided_lesson_steps limit 1;
```

Both selects succeeded on 2026-10-18. The sampled `generated_items` row
returned `embedding = null` and `embedded_at = null`; the sampled
`guided_lesson_steps` row returned `embedding = null`.

No migration was applied by the CLI, and no backfill or live data write was
performed as part of verification.
