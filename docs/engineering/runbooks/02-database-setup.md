---
runbook: database-setup
applies_to: [local, prod]
who_runs_it: Fred / ITO database maintainer
time_needed: "[Fred to confirm]"
last_verified: "unverified; source review at 4f3ec29 on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 02 — database setup and migration gates

## When to use it

Prepare a fresh institutional Supabase project or validate a throwaway local stack. This WI-07 draft replaces the partial extraction. It does not supply the pending Lane DB implementation or authorize agents to apply hosted SQL. A named human executes approved hosted operations.

## Before you start

- Read [APPROVAL-01](../../work/handover-2026/approval-01.md), including section 5, and [environment boundaries](../environments.md). Production is a fresh institutional project, with no personal data/account transfer.
- Obtain project administration, approved plan/region, backups and credential custody through [secrets.md](../secrets.md). Exact choices: [Fred to confirm].
- **Local gate:** hosted Postgres major is unconfirmed. Lane DB owns major configuration, relocation, seed, schema/types and package scripts. Its executable guide is pending at this revision. Do not run the router's future `db:*` commands as if installed.

## Steps

1. Record revision and migration manifest with read-only filesystem checks. At this draft's base, **36** SQL files, `0001`–`0036`, live in [packages/db/migrations](../../../packages/db/migrations/). Preserve numeric names and bytes, including 0036's historical path comment. Lane B's proposed 0037 is pending and has a separately owned apply note; it is not part of the 36-file proof.
2. Fred reports only the hosted Postgres major, then Lane DB supplies the approved local workflow. Required accepted results: two clean `db:verify` runs, no second-run schema/type diff, fake fixtures, types at [packages/schema/supabase.ts](../../../packages/schema/supabase.ts). Do not substitute the existing hosted-ref `schema:types` command. Local reset/replay waits for that lane and its guide.
3. Review [accepted replay evidence](../../work/handover-2026/evidence/audit-migration-replay.md): 36 unchanged files passed two CLI replays and an independent psql replay on PostgreSQL 17.6 / CLI 2.114.0; all 13 notices are enumerated. This proves empty-schema SQL replay, not hosted parity, RLS behavior, populated-data repair or current version suitability.
4. For a fresh hosted environment, the human creates the approved empty institutional project. Current create-project console path, plan/region/database-major selection: [Fred to confirm]. Check the target before writes; never reset/replay an existing hosted database.
5. Before SQL application, prepare a reviewed manifest and per-migration pre/post-check plan, local replay on the selected major, backup/restore procedure and checks for Supabase roles/auth helpers, extensions and Data API exposure/grants. `0001` establishes `vector` and `pgcrypto`; include every later migration in order. Approved full-bootstrap application method and migration-history reconciliation for SQL-editor use: [Fred to confirm]. **Stop until reviewed.** Do not guess linked CLI operations or apply only the old first three files.
6. The human applies only the reviewed manifest and records each file's result. Existing [0034](../../runbooks/0034-apply.md), [0035](../../runbooks/0035-apply.md) and [0036](../../runbooks/0036-apply.md) notes are dated evidence, not blanket reapply authorization. Applied files are immutable; repair goes forward in a new file.
7. Verify the existing HS256 session-signing compatibility with the API owner before [05](secrets-manager.md). Do not substitute asymmetric signing or different key types without an approved application change. Service credentials stay server-side; browser keys are public-only. Verify tenant/owner RLS, role grants and embedding model/schema dimensions separately.
8. Establish institutional mapping through the reviewed setup/launch. Source creates/resolves institution from validated issuer plus deployment; do not reuse old UUIDs. Required institution name/timezone and any seed operation: [Fred to confirm]. Complete [08](lti-tool-registration.md) and [10](first-launch-smoke.md) using synthetic users.

## Verify it worked

Record environment (host only publicly), major/extension versions, manifest checksums, migration outcomes, date and verifier. Test Data API visibility/grants separately from row-level authorization. Exercise own-student, course-instructor and cross-institution denial with approved synthetic fixtures; service-role success alone does not prove RLS. Exact post-Lane-DB command transcript and hosted acceptance results: [Fred to confirm]. No SQL was written or executed by Lane R.

## Undo / roll back

Never edit/delete applied history. On failure stop at the file and record sanitized SQLSTATE/object; the maintainer prepares an approved forward fix. Check transaction boundaries before assuming no partial changes. Restore only through the approved backup procedure; recovery rehearsal: [Fred to confirm]. Throwaway local reset uses the approved Lane DB workflow, never a linked/hosted target.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Missing `db:*` scripts/guide | Lane DB not integrated | Await that lane; do not invent commands. |
| Replay passes, API sees no rows | Exposure/grant, JWT or RLS mismatch | Check each layer with synthetic identities; never disable RLS. |
| Practice submit SQLSTATE 42702 | Historical 0034 ambiguity / missing correction | Inspect approved 0035 evidence and installed function; never edit 0034. |
| Vector mismatch | Model/schema mismatch | Review configuration and 0036; no ad hoc ALTER/backfill. |

## Sources and evidence gaps

[Archived SUPABASE guide](../../archive/engineering/SUPABASE.md) is historical; its three-file setup is obsolete. [Official environment guidance](https://supabase.com/docs/guides/deployment/managing-environments) describes local migration verification before deployment. The [Postgres minor-release warning](https://supabase.com/changelog/postgres-15-19-17-11-breaking-changes) was consulted through the official changelog; current hosted version/extension compatibility still needs confirmation. Upstream guidance does not override Kala's accepted numeric-filename/local-package policy.

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-24 | Preserve partial 36-file reconciliation | WI-03 extraction. |
| 2026-10-25 | Draft setup checks and local/hosted execution gates | APPROVAL-05 rev 2, Lane R, WI-07; relocation and 0037 pending. |
