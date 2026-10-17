# Migration 0035: fix attempt-number ambiguity

## What it fixes

`submit_practice` returns a table whose OUT columns include `attempt_number`. In PL/pgSQL, the first-attempt insert's unqualified `RETURNING attempt_number` conflicts with that OUT variable and raises SQLSTATE `42702`. Migration 0035 replaces only `public.submit_practice(uuid,uuid,uuid,uuid,text,uuid,uuid,text,integer,uuid)` and `public.start_practice_retake(uuid,uuid,uuid,uuid)`. It sets `#variable_conflict use_column` in both bodies and fully qualifies the attempt-row `RETURNING` columns. It uses `CREATE OR REPLACE FUNCTION`, preserving existing grants, and does not replace `review_flashcard`.

## Apply

1. Review `packages/db/migrations/0035_fix_submit_practice_ambiguity.sql`.
2. Open the Supabase SQL editor.
3. Paste the whole migration file and click **Run**. The file contains one transaction and reloads the PostgREST schema at the end.

## Post-apply checks

Run these read-only checks in the Supabase SQL editor.

### Function body directives and qualified `RETURNING`

```sql
select
  position('#variable_conflict use_column' in pg_get_functiondef(
    'public.submit_practice(uuid,uuid,uuid,uuid,text,uuid,uuid,text,integer,uuid)'::regprocedure
  )) > 0 as submit_uses_column_conflict_rule,
  position('returning public.quiz_set_attempts.id' in lower(pg_get_functiondef(
    'public.submit_practice(uuid,uuid,uuid,uuid,text,uuid,uuid,text,integer,uuid)'::regprocedure
  ))) > 0 as submit_qualifies_attempt_returning,
  position('#variable_conflict use_column' in pg_get_functiondef(
    'public.start_practice_retake(uuid,uuid,uuid,uuid)'::regprocedure
  )) > 0 as retake_uses_column_conflict_rule,
  position('returning public.quiz_set_attempts.id' in lower(pg_get_functiondef(
    'public.start_practice_retake(uuid,uuid,uuid,uuid)'::regprocedure
  ))) > 0 as retake_qualifies_attempt_returning;
```

Expected: all four columns are `true`.

### Service-role execute grants remain present

```sql
select
  has_function_privilege(
    'service_role',
    'public.submit_practice(uuid,uuid,uuid,uuid,text,uuid,uuid,text,integer,uuid)'::regprocedure,
    'EXECUTE'
  ) as submit_service_role_can_execute,
  has_function_privilege(
    'service_role',
    'public.start_practice_retake(uuid,uuid,uuid,uuid)'::regprocedure,
    'EXECUTE'
  ) as retake_service_role_can_execute;
```

Expected: both columns are `true`.

### API first-attempt check

Using the dedicated smoke student, submit the first answer for a new practice set through the API. Confirm the request succeeds with HTTP 200 and returns `attemptNumber = 1`; do not submit SQL writes directly or use another account.
