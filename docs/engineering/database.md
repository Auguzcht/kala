# Database operating boundary

This is the current policy and source map, checked for DOCS-HYGIENE on 2026-10-25. It does not install the pending local database workflow. Use [runbook 02](runbooks/02-database-setup.md) for setup gates and [the 0037 procedure](../runbooks/0037-apply.md) for that migration's exact pre/post-checks.

## Migration ownership

The repository currently has 37 numeric SQL migrations in [packages/db/migrations](../../packages/db/migrations/), 0001 through 0037. Apply the complete reviewed sequence to a fresh database, never only the initial three files. Existing hosted databases need a reviewed forward delta. Applied migrations are immutable byte for byte, including comments; historical references inside them keep their old paths. Never rename, reformat or amend an applied file. A named maintainer applies hosted SQL and records results; agents may prepare and locally verify SQL only.

0037 adds nullable `tutor_conversations.pinned_at` without a default. Fred reported application and read-only post-checks passed on 2026-10-25. Do not reapply it. SQL-editor delivery and CLI migration history are separate: the incomplete hosted history remains a database-stream reconciliation item and does not block this approved backend deployment. Neither an empty-schema replay nor a service-role request proves tenant/owner RLS.

## Local tooling and package scripts

The pinned dependency is resolved from the root pnpm lockfile. Use `pnpm exec supabase`, not a global CLI. Record both versions and the actual local Postgres version in replay evidence. The local workflow's relocation, `supabase/config.toml` major, fake seed and `db:*` commands remain pending; do not assume they exist. The hosted major needs maintainer confirmation before that implementation. Generated types keep the imported path [packages/schema/supabase.ts](../../packages/schema/supabase.ts).

Every future `db:*` package script is strictly local: no `--linked`, project reference or hosted credentials. `db:types:linked` is prohibited. The current root `schema:types` script still targets a hosted project reference and must not be used by agents; replacing it belongs to the database lane. Do not substitute it for local verification.

For approved local replay use throwaway Docker databases, fake fixtures and the pinned CLI's default image until a major is configured. The approved workflow must prove two clean verifies and no second-run schema/type diff. Command implementation and execution remain pending, so this page supplies no invented reset command. New SQL must run against real local Postgres before acceptance; mocks alone are insufficient.

## Hosted drift inspection

Maintainer only: Fred takes a schema-only dump of dev-hosted and places it at `.tmp/hosted_schema.sql` (gitignored). Agents only compare that supplied file against `supabase/schema.sql` after the local workflow creates the latter. Neither path is a current checked-in artifact. No agent connects to hosted Postgres for this inspection. Do not send keys, connection strings or raw dumps into chats or commit them. Record only sanitized differences, revision, versions and verifier.

## Access verification and recovery

Check Data API exposure/grants separately from RLS; exercise own-student, course-instructor and cross-institution denial with approved synthetic identities. Preserve backups and a per-migration pre/post-check plan before a hosted change. On a failed migration stop at the failed file, record SQLSTATE/object without payloads, inspect transaction boundaries and prepare a forward fix. Never disable RLS or reset a hosted database to make replay pass.

## Change log

- 2026-10-25 — DOCS-HYGIENE: make the confirmed local-only policy and current missing tooling explicit; consolidate setup limits without changing SQL or commands.
