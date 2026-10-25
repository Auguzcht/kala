# 0039: evidence history index

Owner/executor: Fred. Gate: FG-6 under APPROVAL-07. Agent execution is local-only.
Requirements: TWIN-REQ-010, INSTR-REQ-010; WI-25.

Apply [0039_evidence_history_index.sql](../../packages/db/migrations/0039_evidence_history_index.sql) only after review. It adds a B-tree index on `(user_id, course_id, created_at DESC, id DESC)` without changing rows, policies or columns. Existing separate user/time and course/time indexes do not cover the combined ordered history query. PostgreSQL may briefly block writes while building this ordinary index; choose a maintenance window. No historical migration may be changed.

## Pre-checks

1. Fred confirms the intended hosted environment and reviewed revision privately. Do not paste credentials or data.
2. Confirm 0001–0037 and any reviewed SEC 0038 have their separate acceptance records. This index has no dependency on 0038's policies.
3. Run the definition check below before applying. No rows means the name is free. Exactly the expected definition with `indisvalid=true` and `indisready=true` means already applied. Any different definition, invalid index, or unexpected relation means **stop**: `IF NOT EXISTS` checks only the name and does not repair an incorrect index.

```sql
select pg_get_indexdef(i.indexrelid) as definition,
       i.indisvalid, i.indisready
from pg_index i
join pg_class c on c.oid=i.indexrelid
join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relname='evidence_events_history_idx';
```

Expected definition:

```text
CREATE INDEX evidence_events_history_idx ON public.evidence_events USING btree (user_id, course_id, created_at DESC, id DESC)
```

## Apply and post-check

Fred runs this transaction in the SQL editor. The checks refuse a conflicting pre-existing definition and verify the final exact definition. Record only revision, success/failure and definition/validity results, never user rows.

```sql
begin;
set local lock_timeout = '5s';
set local statement_timeout = '120s';
do $$
begin
  if to_regclass('public.evidence_events_history_idx') is not null and not exists (
    select 1 from pg_index i
    where i.indexrelid=to_regclass('public.evidence_events_history_idx')
      and i.indisvalid and i.indisready
      and pg_get_indexdef(i.indexrelid)='CREATE INDEX evidence_events_history_idx ON public.evidence_events USING btree (user_id, course_id, created_at DESC, id DESC)'
  ) then raise exception '0039 existing index definition mismatch'; end if;
end $$;
create index if not exists evidence_events_history_idx
on public.evidence_events (user_id, course_id, created_at desc, id desc);
do $$
begin
  if not exists (
    select 1 from pg_index i
    where i.indexrelid=to_regclass('public.evidence_events_history_idx')
      and i.indisvalid and i.indisready
      and pg_get_indexdef(i.indexrelid)='CREATE INDEX evidence_events_history_idx ON public.evidence_events USING btree (user_id, course_id, created_at DESC, id DESC)'
  ) then raise exception '0039 post-check failed'; end if;
end $$;
commit;
```

Repeat the definition query after commit. Timeout/error aborts the transaction: roll back and investigate; do not mark FG-6 passed. If execution outcome is unknown, inspect the definition before retrying.

## Recovery

An application rollback does not require removing this additive index. If Fred chooses to remove it after review, first confirm its exact definition with the pre-check, then run `drop index public.evidence_events_history_idx;`. This changes query cost only. Never remove either historical index or edit an applied migration. Record any removal so a later application does not incorrectly assume 0039 is present.

## Local verification

Use only a dedicated throwaway local Docker database with synthetic fixtures, never a shared database or hosted credentials. Replay 0001–0037 byte-for-byte, providing the local Supabase auth/storage bootstrap expected by those files. Run 0039 twice, the transaction above, and [the synthetic query fixture](../../services/api/tests/fixtures/evidence_history_local.sql). The fixture rolls back all rows, compares keyset/tie ordering with native tuple order, and shows index eligibility with `EXPLAIN`. This is not a hosted performance or lock-duration measurement.

## Verified by

[WI-25 evidence](../work/handover-2026/evidence/wi25-evidence-history.md). Hosted execution remains pending Fred's FG-6.
