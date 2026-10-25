# Migration 0038: staff course and learner visibility

WI-26 implements [INSTR-REQ-009](../features/instructor-insights/README.md#instr-req-009-authorize-staff-course-and-learner-access). Fred is the named hosted operator. FG-6 remains required; this runbook authorizes no agent hosted inspection, application or deployment.

## Reviewed change

Apply only [0038_recommendation_visibility.sql](../../packages/db/migrations/0038_recommendation_visibility.sql), once, in its existing transaction. The filename is retained from the initial recommendation-only checkpoint; the final scope is 22 existing policies on 20 tables. There are no row, table, grant, index, helper or view changes. Applied 0001–0037 remain byte-for-byte immutable.

Reviewed-file SHA-256: `aef2053f98368d691bb2735ec6ffbeafc603426b10eef6b24b516f076ad83485`.

| Policy group | Tightening |
| --- | --- |
| recommendations SELECT/INSERT/UPDATE | Token institution/course admission, explicit instructor role and enrollment, enrolled target student for staff access; own student reads only approved/modified/completed |
| evidence, mastery, readiness, SRS, quiz attempts, exposures, reviews | Preserve own non-staff history; staff require authorized course and current target student enrollment/user role |
| enrollments | Token institution and role; instructors retain their own instructor enrollment for admission and student enrollments for courses they teach; institution admins retain enrollment oversight |
| users, identity aliases, profiles | Preserve own identity; instructors see enrolled learner identities in taught courses; admins retain institutional staff oversight and enrolled learner access; peer profiles remain admin-only |
| courses, skills, assessments, guided lessons | Preserve existing non-staff curriculum/granted-research access; restrict staff to taught courses or their admin institution |
| content items, generated items, quiz sets, ingest jobs | Explicit staff role, token institution and matching course enrollment/admin admission |

The unchanged lesson-step and quiz-set-item policies inherit their parent's narrowed staff visibility. Unchanged research views retain their existing grant/consent behavior. Enrollment policies avoid querying users/courses recursively; current instructor enrollment remains readable so dependent policy admission can work. No helper is replaced.

## Pre-checks — Fred, FG-6

Confirm the intended hosted project in the SQL editor, coordinator-reviewed Git revision, checksum and 0001–0037 baseline. Keep output to schema metadata and counts; never paste student rows, identity values, content or credentials. Save the following before application:

```sql
select current_setting('server_version');
select p.tablename, c.relrowsecurity, c.relforcerowsecurity
from pg_tables p join pg_class c
  on c.oid = format('%I.%I',p.schemaname,p.tablename)::regclass
where p.schemaname='public' order by p.tablename;
select tablename, policyname, roles, cmd, permissive, qual, with_check
from pg_policies where schemaname='public' order by tablename,policyname;
select table_name, grantee, privilege_type
from information_schema.table_privileges
where table_schema='public' order by table_name,grantee,privilege_type;
select p.oid::regprocedure as helper,
       md5(pg_get_functiondef(p.oid)) as definition_checksum
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where n.nspname='public' and p.prokind='f' order by p.oid::regprocedure::text;
select count(*) as recommendation_count from public.recommendations;
```

Compare policies against the complete reviewed baseline. Stop if prerequisites differ, RLS is disabled, unexpected permissive policies exist, or privileges differ unexpectedly. Do not adapt this file ad hoc. Verify the local file checksum with `shasum -a 256 packages/db/migrations/0038_recommendation_visibility.sql` in the reviewed checkout.

The local replay has no authenticated SELECT grant on ingest_jobs. Its policy was tested with a temporary grant inside rolled-back transactions; 0038 does not add that grant. Hosted grants/exposure must be checked by Fred and never inferred from this local fixture.

## Apply — Fred only

Run the entire reviewed file once in the SQL editor. It begins and commits one transaction. On error, stop and record only sanitized object/SQLSTATE/reason. Never disable RLS, change grants, amend predecessors or run deployment commands to make it pass. Record filename, reviewed SHA/checksum, operator, environment label, time and pre/post-check outcomes. SQL-editor application does not establish CLI migration history.

## Post-checks — Fred

Repeat the pre-check queries. Only the 22 reviewed policy expressions may differ. Policy names, roles/commands, RLS flags, grants, helper definitions, views and indexes remain unchanged. No rows are changed; investigate unexplained count differences while allowing separately explained ordinary concurrent activity.

Using separately approved synthetic accounts, confirm authenticated access (a service-role success is not RLS acceptance):

- Owning student retains own learning history and permitted curriculum reads. Suggested/rejected recommendations are hidden; student cannot write recommendations.
- Correct instructor sees the current enrolled learner in the taught course; another-course teacher and foreign instructor/admin cannot.
- Same-institution admin retains authorized course/learner access and staff oversight.
- Removed learner: teacher/admin cannot read that learner's learning records or recommendations or create/decide recommendations. The student's own retained history and assigned plan remain readable.
- Removed instructor or stale instructor enrollment with a student token grants no teacher access. Wrong institution claims grant no staff access.
- Existing researcher grant/consent views retain their intended behavior. This migration does not alter their definitions or grant scope semantics.

Record counts/statuses only. FG-8 deployment and FG-9 live role/course acceptance remain separate Fred gates.

## Recovery

A failed uncommitted application rolls back transactionally. After success, retain the tighter policies during an application rollback; no data or response schema changed. Restoring old overbroad policies would loosen access and is prohibited by this approval. Stop the rollout and prepare a reviewed forward correction for any legitimate access regression; Fred decides and executes further hosted action. Never edit applied 0038.

## Local verification

The [local verifier](../../services/api/tests/wi26_rls_local.py) creates a fresh database in a disposable `kala-wi26-sec-*` Docker container with network `none` and no published ports. It uses minimal synthetic Auth/Storage platform fixtures, unchanged 0001–0037, then 0038. No environment files or hosted credentials are used.

```sh
python3 services/api/tests/wi26_rls_local.py --container kala-wi26-sec-policy-2d3d
```

Final proof on PostgreSQL 17.6 / Supabase image 17.6.1.158 passed: ten actors × 35 read boundaries (including temporary-grant ingest policy probes), recommendation writes, removed learner/instructor cases, preserved self/curriculum/research access, policy dumps, unchanged schema/grants/helpers/views/indexes after excluding policies, preserved fixture counts and unchanged historical migration checksums. Full Supabase service integration, hosted major/exposure and hosted acceptance remain unverified.

## Historical sources

- [APPROVAL-07](../work/handover-2026/approval-07.md), section 1 and confirmed amendments.
