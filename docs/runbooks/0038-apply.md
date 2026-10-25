# Migration 0038: recommendation visibility

WI-26 implements [INSTR-REQ-009](../features/instructor-insights/README.md#instr-req-009-authorize-staff-course-and-learner-access).
Fred is the named hosted operator. Agents prepare and locally verify this file; FG-6 remains required before any hosted application. This runbook does not authorize deployment or hosted inspection.

## Reviewed change

Apply only [0038_recommendation_visibility.sql](../../packages/db/migrations/0038_recommendation_visibility.sql), once, in its existing transaction. It alters `recs_read`, `recs_insert` and `recs_update` on `public.recommendations`. There are no table, grant, helper, index or row changes. Applied 0001–0037 remain immutable.

Reviewed-file SHA-256: `2198f4323a3d722e14b651804dec740aae0a04de0d20db2bbb06ab7e4e56b627`.

All three policies require the token institution to match both the row and course. Instructor branches require the token instructor role and instructor enrollment in that institution/course. Admins remain institution-scoped. Student reads require own identity and approved/modified/completed status. Student writes remain denied, including a student token with a stale instructor enrollment. Staff decision history remains available within its authorized scope.

## Pre-checks — Fred, FG-6

1. Confirm the intended hosted project in the SQL editor, the coordinator-reviewed Git revision and 0001–0037 baseline. Check the migration SHA-256 against the reviewed revision using `shasum -a 256 packages/db/migrations/0038_recommendation_visibility.sql` in the reviewed checkout.
2. Save the following metadata and counts locally. Never export recommendation content, identity values or credentials into the evidence record.
3. Stop if any expected policy, grant, RLS flag or baseline differs. Do not adapt the migration ad hoc.

```sql
select current_setting('server_version');
select relrowsecurity, relforcerowsecurity
from pg_class where oid = 'public.recommendations'::regclass;
select policyname, roles, cmd, permissive, qual, with_check
from pg_policies
where schemaname = 'public' and tablename = 'recommendations'
order by policyname;
select grantee, privilege_type
from information_schema.table_privileges
where table_schema = 'public' and table_name = 'recommendations'
order by grantee, privilege_type;
select count(*) as recommendation_count from public.recommendations;
select pg_get_functiondef('public.teaches(uuid)'::regprocedure);
```

Expected: RLS enabled; `recs_read` SELECT and `recs_insert` INSERT / `recs_update` UPDATE for authenticated. Existing SELECT allows own rows regardless of status. INSERT/UPDATE require institution plus teacher/admin. The teacher helper is unchanged by this migration. Unexpected additional permissive policies can bypass the intended restriction: stop for review if found.

## Apply — Fred only

Run the entire reviewed file once in the SQL editor. It begins and commits one transaction. On error, stop and record only the object/SQLSTATE and sanitized reason. Do not disable RLS, change grants, reapply predecessors or run deployment commands. SQL-editor application does not establish CLI migration history; record this distinction.

## Post-checks — Fred

Repeat every pre-check. Expected:

- RLS flags, grants, helper definition and recommendation count are unchanged, allowing separately explained concurrent ordinary activity.
- Only the three policy expressions changed; no additional policy appears.
- `recs_read` contains own-student identity plus assigned statuses; every staff branch has token institution/course boundaries and explicit role checks.
- INSERT and both UPDATE expressions have matching staff/institution/course restrictions.

Use separately approved synthetic accounts for Data API acceptance. Own student sees assigned rows only and cannot insert/update. The right teacher sees decision history and can perform intended decisions. Another-course teacher, foreign teacher and foreign admin see no rows and cannot write. A same-institution admin retains intended access. Record counts/status outcomes only. No agent performs these hosted checks. A service-role query cannot substitute for authenticated RLS acceptance.

Record operator, environment label, time, filename, reviewed SHA/checksum and all pre/post-check outcomes. FG-8 and live acceptance remain separate Fred gates.

## Recovery

The file is transactional; a failed uncommitted application rolls back. After successful application, retain the tighter policies when rolling back application code: the previous API remains compatible and no rows were changed. Restoring the old overbroad policies would loosen access and is prohibited by this approval. Stop affected rollout and prepare a reviewed forward correction if a legitimate access regression is discovered; Fred decides and executes any further hosted action. Never edit applied 0038.

## Local verification

The dedicated [local verifier](../../services/api/tests/wi26_rls_local.py) creates a fresh named database in an explicitly named, network-disabled Docker container with no published ports. It uses a minimal synthetic Auth/Storage platform fixture and unchanged 0001–0037, then applies 0038. It does not use environment files or hosted credentials. Run it only against a disposable container named `kala-wi26-sec-*`:

```sh
python3 services/api/tests/wi26_rls_local.py --container kala-wi26-sec-2d3d
```

On PostgreSQL 17.6 / Supabase image 17.6.1.158, both complete synthetic replays passed. Final proof covers authenticated read/update/insert matrices, student token with stale teacher enrollment, wrong institution claim, five preserved recommendation rows, before/after policy dumps, policy-only schema/grant comparison and unchanged historical migration checksums. Hosted major, Auth/Storage service integration and actual Data API exposure remain unverified. Details and remaining route limitations are in the lane evidence.

## Historical sources

- [APPROVAL-07](../work/handover-2026/approval-07.md), section 1 and confirmed amendments.
