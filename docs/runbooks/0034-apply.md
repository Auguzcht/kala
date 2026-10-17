# Migration 0034: attempt-aware practice

This runbook is for applying `packages/db/migrations/0034_attempt_aware_practice.sql` after review and approval. The migration has **not** been applied by this task. Run all checks below in the Supabase SQL editor immediately before applying; every query is read-only.

## Pre-apply checks, results 2026-10-17

The expected results below were supplied from the user's read-only Supabase SQL editor audit on 2026-10-17. They were not independently queried by this task.

### 1. Applied migrations and 0033 function

```sql
select
  (select count(*)
     from supabase_migrations.schema_migrations
    where version between '0001' and '0033') as applied_migrations_0001_0033,
  (select count(*)
     from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'record_practice_set_exposures') as record_practice_set_exposures_count;
```

Expected: `applied_migrations_0001_0033 = 33`; `record_practice_set_exposures_count = 1`.

### 2. Existing constraint names

```sql
select expected.constraint_name, count(c.oid) as found_count
  from (values
    ('quiz_set_attempts_user_id_set_id_key'),
    ('practice_answer_results_user_id_set_id_item_id_key')
  ) as expected(constraint_name)
  left join pg_constraint c on c.conname = expected.constraint_name
  left join pg_namespace n on n.oid = c.connamespace and n.nspname = 'public'
 group by expected.constraint_name
 order by expected.constraint_name;
```

Expected: each named constraint has `found_count = 1`. These are the exact names dropped by migration 0034.

### 3. Sets without `quiz_set_items`

```sql
select count(*) as sets_without_quiz_set_items
  from public.quiz_sets qs
 where not exists (
   select 1 from public.quiz_set_items qsi where qsi.set_id = qs.id
 );
```

Expected: `sets_without_quiz_set_items = 0`. The generated-items fallback in migration 0034 remains as a safety net.

### 4. Function overloads and `review_flashcard` callers

```sql
select
  array(
    select pg_get_function_identity_arguments(p.oid)
      from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public' and p.proname = 'review_flashcard'
     order by 1
  ) as review_flashcard_overloads,
  array(
    select pg_get_function_identity_arguments(p.oid)
      from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public' and p.proname = 'submit_practice'
     order by 1
  ) as submit_practice_overloads,
  array(
    select p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')'
      from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public' and p.prokind = 'f'
       and p.prosrc ilike '%review_flashcard%'
     order by 1
  ) as functions_calling_review_flashcard;
```

Expected: one `review_flashcard(uuid,uuid,uuid,uuid,text,text,uuid,text,integer)` overload; one `submit_practice(uuid,uuid,uuid,uuid,text,uuid,uuid,text,integer)` overload; only `submit_practice` calls `review_flashcard`. Migration 0034 explicitly drops the old 9-argument `submit_practice` before replacing `review_flashcard`.

### 5. Historical XP equivalence

```sql
with before_by_user as (
  select ir.user_id,
         sum(2 + case when ir.outcome = 'good' then 10 else 0 end)::bigint as xp
    from public.item_reviews ir
   where ir.counted
   group by ir.user_id
), after_rows as (
  select par.user_id, par.xp_awarded::bigint as xp
    from public.practice_answer_results par
  union all
  select ir.user_id,
         (2 + case when ir.outcome = 'good' then 10 else 0 end)::bigint as xp
    from public.item_reviews ir
   where ir.counted and ir.mode <> 'quiz'
  union all
  select ir.user_id,
         (2 + case when ir.outcome = 'good' then 10 else 0 end)::bigint as xp
    from public.item_reviews ir
   where ir.counted and ir.mode = 'quiz'
     and not exists (
       select 1 from public.practice_answer_results par
        where par.user_id = ir.user_id
          and par.idempotency_key = ir.idempotency_key
     )
), after_by_user as (
  select user_id, sum(xp)::bigint as xp
    from after_rows group by user_id
), all_users as (
  select user_id from before_by_user
  union
  select user_id from after_by_user
), comparisons as (
  select u.user_id, coalesce(b.xp, 0)::bigint as before_xp,
         coalesce(a.xp, 0)::bigint as after_xp
    from all_users u
    left join before_by_user b using (user_id)
    left join after_by_user a using (user_id)
), mismatches as (
  select * from comparisons where before_xp <> after_xp
), samples as (
  select jsonb_agg(jsonb_build_object(
           'user_id', user_id, 'before_xp', before_xp, 'after_xp', after_xp
         ) order by user_id) as rows
    from (select * from mismatches order by user_id limit 5) first_five
)
select (select count(*) from comparisons) as user_count,
       (select count(*) from mismatches) as mismatches,
       coalesce((select rows from samples), '[]'::jsonb) as mismatching_users;
```

Expected from the user's 2026-10-17 audit: `user_count = 3`, `mismatches = 0`, `mismatching_users = []`. The equivalence works because migration 0032 passes the same `p_idempotency_key` into `review_flashcard` at `packages/db/migrations/0032_practice_answer_recap.sql:188-192`, allowing saved practice answers to be matched to their quiz review rows. The only pre-0032 quiz reviews without a saved answer snapshot remain included in the after-formula.

## `review_flashcard` write map

The latest pre-0034 definition is in `packages/db/migrations/0028_practice_item_reviews.sql`. It inserts `srs_state` (`INSERT` at line 100), locks and conditionally updates it (`UPDATE` at line 141), inserts `item_reviews` (line 148), inserts `evidence_events` (line 156), and upserts `mastery_state` (line 178). Migration 0034 keeps the schedule and review-log statements active for retakes while skipping evidence and mastery writes when `p_affects_mastery` is false. Existing callers retain the default `true` behavior.

## Manual post-apply checks

After applying 0034, run these checks in a transaction that is rolled back:

1. Confirm `quiz_set_attempts` has unique `(user_id, set_id, attempt_number)` and no longer has unique `(user_id, set_id)`.
2. Confirm saved set answers have non-null `attempt_id`, `attempt_id` matches the same user's/set's attempt 1, and set-null answers retain null `attempt_id`.
3. Confirm the immutable trigger is enabled after migration and still rejects an update to `practice_answer_results`.
4. Call `submit_practice` for attempt 1: first answer earns 2 XP plus 10 if correct, updates mastery/evidence, and repeated same-key submission returns its original snapshot.
5. Complete attempt 1, call `start_practice_retake`, and submit an answer for attempt 2: XP is zero, mastery and evidence do not change, and SRS plus `item_reviews` still follow the existing quiz schedule behavior.
6. Submit a new answer to the completed attempt and confirm `P0001` / `attempt_complete`; call retake before completion and confirm `P0001` / `attempt_in_progress`; call retake before any attempt and confirm `P0001` / `no_attempt`.
7. Submit a `set_id IS NULL` answer and confirm its existing counted-based XP, mastery, evidence, schedule, and response behavior remain unchanged.
8. Confirm API reads return the latest attempt by default, explicit `attempt_id` scopes the recap, and retake XP note and set scores match the selected attempt.

Do not run the reset script with `--apply` against production data.
