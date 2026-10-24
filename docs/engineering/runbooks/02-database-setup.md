---
runbook: database-setup
applies_to: [local, prod]
who_runs_it: Fred / ITO maintainer
last_verified: unverified; WI-03 source extraction only
status: partial
---

# Runbook 02 — database setup reconciliation

**Incomplete procedure, planned for WI-07.** The old [SUPABASE.md](../../archive/engineering/SUPABASE.md) three-migration setup is historical. The accepted [BRIEF-03 replay](../../work/handover-2026/evidence/audit-migration-replay.md) applied all 36 existing files on local PostgreSQL 17.6 with pinned CLI 2.114.0. That proof does not validate populated data, RLS behavior, hosted parity or application acceptance.

Use the complete ordered migration sequence, never only 0001–0003. Preserve Supabase auth helper/role expectations, pgvector and pgcrypto prerequisites, tenant-scoped RLS and generated contracts. No migration SQL is copied into this procedure.

Lane DB owns the executable local workflow and [database.md](../database.md). It is gated on Fred's hosted Postgres major, then rebases after Lane D and updates references in the post-archive tree. APPROVAL-01 requires numeric filenames unchanged, checksums before/after the move, no edits even to historical SQL comments, two clean `db:verify` runs, fake seed fixtures, and types at the existing `packages/schema/supabase.ts` path. Hosted drift waits for Fred's schema-only dump. No schema/type generation, SQL execution or hosted migration occurred in Lane D.

Still needed: exact approved setup commands after Lane DB, isolation/pre-checks, fixture validation, failure/rollback procedure, RLS/application checks, and a maintainer's verification date/revision/environment. [APPROVAL-01 section 5](../../work/handover-2026/approval-01.md#5-confirmed-amendments-and-standing-scope-rule) overrides the pack's old type-path assumptions.
