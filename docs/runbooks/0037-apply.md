# Migration 0037: Tutor conversation pins

Authority: [APPROVAL-05](../work/handover-2026/approval-05.md), section 2 and
confirmed coordinator amendments; [WI-21](../work/handover-2026/work-items/WI-21-tutor-conversation-management.md);
[TUTOR-REQ-002/003](../features/tutor/README.md#conversation-management-lane-b).

Prepared by Lane B. **Hosted application is not performed or verified. Fred is
the named operator and applies the reviewed migration in the SQL editor.**
Agents do not apply it to hosted projects, deploy the API or change hosted grants.

## Change and application order

The reviewed file is
[`0037_tutor_conversation_pin.sql`](../../packages/db/migrations/0037_tutor_conversation_pin.sql).
It adds `public.tutor_conversations.pinned_at timestamptz null`, without a
default or backfill. Existing rows begin unpinned. It changes no policies,
grants, indexes, functions or existing columns. Historical migration files
remain byte for byte unchanged, including comments.

Reviewed-file SHA-256:
`82c9297ea08b4c16c3ba03bb2cc64eb222e67dd4276e9b4f7a8db22efe873450`.
Verify it against the reviewed revision before application.

1. Coordinator reviews Lane B's code, tests and local replay evidence.
2. Fred applies 0037 and records the pre-checks and post-checks below.
3. Only after these checks pass may the separately approved new API deploy
   select or update `pinned_at`. The old API continues to work with the added
   column. Applying the new API before the column exists breaks its list route.
4. Fred checks the deployed API; Lane U owns frontend wiring and its rollout.

The SQL-editor operation does not automatically record CLI migration history.
Record the applied filename, reviewed Git revision, checksum, environment,
operator, time and verification results in the coordinator's delivery evidence.
Lane DB carries 0037 with the other migrations when its separate gate opens.

## Pre-checks — Fred, correct hosted project

Confirm the project in the SQL editor, approval of the exact migration and
the 0001–0036 baseline. Keep query results to schema metadata and counts;
do not paste conversation titles, messages, credentials or provider bodies.
Save these results for comparison after application:

```sql
select current_setting('server_version');

select column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = 'public' and table_name = 'tutor_conversations'
  and column_name = 'pinned_at';

select relrowsecurity, relforcerowsecurity
from pg_class where oid = 'public.tutor_conversations'::regclass;

select policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public' and tablename = 'tutor_conversations'
order by policyname;

select grantee, privilege_type
from information_schema.table_privileges
where table_schema = 'public' and table_name = 'tutor_conversations'
order by grantee, privilege_type;

select has_table_privilege('service_role', 'public.tutor_conversations', 'SELECT') as service_select,
       has_table_privilege('service_role', 'public.tutor_conversations', 'UPDATE') as service_update;

select count(*) as conversation_count from public.tutor_conversations;
```

Expected: no `pinned_at` column; RLS enabled; existing owner-read policy;
`service_select` and `service_update` true in the environment serving the API.
RLS bypass does not itself grant table privileges. If a prerequisite is missing,
stop and report it to the coordinator; this migration does not repair grants.

If `pinned_at` already exists, stop and reconcile the recorded application.
Do not drop the column or rerun the file blindly. The migration intentionally
fails on an already-present column rather than hiding unexpected schema state.

## Apply — Fred only

Paste the complete reviewed migration file into the SQL editor and run it
once. Do not edit an older migration or add a default, data update or policy.
Record success or the sanitized error and stop on failure. Use the separately
approved deployment process only after the following checks pass.

## Post-checks — Fred

Repeat the column, RLS, policy, grant and service-privilege queries above.
The new column must be `timestamp with time zone`, nullable (`YES`), with
`column_default` null. RLS flags, policies and grants must match the saved
pre-checks. Check counts before the new API starts pinning conversations:

```sql
select count(*) as conversation_count, count(pinned_at) as pinned_count
from public.tutor_conversations;
```

Expected: existing rows are preserved and `pinned_count` is zero. Concurrent
ordinary use can change the total count; investigate unexplained differences.
If metadata or subsequent API responses indicate a stale Data API schema cache,
stop the rollout and have the maintainer resolve it before continuing.

After the separately approved API deployment, Fred uses his own test account:

- List conversations: existing fields and envelope remain; every row includes
  `pinnedAt` as a timestamp or null.
- Rename an owned conversation; refresh and confirm the title persists.
- Pin two conversations at different times: the newer pin appears first, both
  precede unpinned conversations. Unpin one and confirm its existing activity
  time determines its place among recents.
- Rename and pin together. Verify `updatedAt` remains unchanged by management
  actions; asking a new message retains its existing activity behavior.
- Confirm unavailable conversations return 404 and empty/invalid PATCH bodies
  return 422. No unsupported-field or null update is accepted.
- Check existing create, detail and stateless ask flows still work. Frontend
  pin/rename controls are Lane U's responsibility; old APIs lack the list flag.

Record results without conversation content or identifiers. A failing live
check is a new evidence entry, not a reason to overwrite a prior pass.

## Recovery

Stop the rollout on failure. The previous API can run with the extra nullable
column, so an approved API rollback leaves the column and stored pin values
in place. Do not drop the column or edit 0037 after application. Any schema
correction is a reviewed forward migration run by Fred.

## Local verification — 2026-10-25

Base: coordinator spec commit `ab4cefc` plus Lane B's owned working files.
This section is local evidence, not hosted application or version-parity proof.

- Worktree-installed Supabase CLI 2.114.0, resolved as
  `./node_modules/.bin/supabase` through `pnpm exec`; global 2.111.0 was not used
  for replay. CLI help was checked before init, migration new, db start,
  migration up and stop. The CLI-created scratch migration was given the
  explicitly approved numeric filename before entering the repository.
- Unique scratch project `kala_wi21_bab4_cca7b72a7b`, database port 57422;
  candidate ports 57420–57429 were checked free. Only the database component
  started. Repository Supabase configuration and existing services were untouched.
- Runtime: PostgreSQL 17.6 on aarch64, image
  `public.ecr.aws/supabase/postgres:17.6.1.158`. Hosted major remains unconfirmed.
- All 36 historical migration copies matched the spec-base Git bytes and
  SHA-256 hashes. `migration up --local` replayed 0001–0036; history contained
  every version in sequence. Six synthetic conversations were then inserted.
- 0037 applied once in a separate `migration up --local` call. History contained
  0001–0037. The column type/nullability/no-default checks passed; all six
  existing rows were preserved with null pins. RLS flags, policies, table grants
  and index definitions compared equal before/after. All 37 source/copy hashes
  matched after verification.
- Real SQL checks passed for rename, owner/institution denial, combined update,
  pin, unpin, preserved activity time and actual four-row pinned/recents ordering.
  Parameterized JSON-record timestamp conversion resolved `"now"` to transaction
  time, and repeating a prepared update in a later transaction refreshed it.
  Authenticated owner reads exposed only the four owned fixture conversations.
- Limitation discovered: this database-only replay has no `service_role` table
  SELECT/UPDATE privileges. The initial role probe failed before mutation.
  Behavior checks used temporary SELECT/UPDATE fixture grants inside a rolled-back
  transaction. Afterwards the original grants again matched. This is not a
  production grant change or proof of an unconfigured local REST stack working.
- API tests use the committed shared isolation: dotenv disabled, fake settings,
  generated test signing material, network sockets blocked. They exercise PATCH
  through FastAPI with mocked persistence; SQL checks separately exercise the
  real database. No live PostgREST, LMS or provider smoke test is claimed.
- Scoped `stop --no-backup` succeeded. No scratch containers, volumes or networks
  remain. Every pre-existing resource name was preserved; no unrelated resource,
  port-5173 process, image or worktree was removed. Raw synthetic SQL/probe
  outputs and the 37-file checksum manifest remain in the temporary
  `kala-wi21-bab4-12a5dmak` scratch directory for local review.
- `cd services/api && uv run pytest -q`: 464 passed, including 33 new management
  cases. The first focused run found an explicit-null title validation defect;
  the corrected implementation passed the focused and full suites. Existing
  dependency deprecation warnings remain.
- `uv run ruff check tests/test_tutor_conversation_management.py`: passed.
  Strict lint of the whole `tutor.py` retains ten baseline findings (eight B008,
  one BLE001, one UP017); comparison against `ab4cefc` found no new findings.
- Web lint passed with zero errors and 18 existing warnings. Web typecheck passed
  after type generation. Web build passed after type generation, retaining its
  existing large-chunk warning. `git diff --check` passed. No UI server started.

Generated-file grants: coordinator authorized `services/api/openapi.json` and
`apps/web/src/lib/api/types.gen.ts` for PATCH/list contracts only. Export ran
under shared test isolation. Existing unrelated contracts were preserved,
including unrelated drift exposed by full generation. `packages/schema/supabase.ts`
was not edited; local regeneration remains a dependency owned by gated Lane DB.
