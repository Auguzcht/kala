# WI-24 local inventory evidence

Date: 2026-10-25. Lane M, base `d75284ec748ce562c1fe85a223ed5bef4ac53c13`, branch `codex/wi24-identity-repair`.

Design precedes script code. [Runbook](../../../runbooks/identity-repair.md) records unresolved policy and rollback decisions; FG-7a is blocked. No hosted access, real pair input, credentials, application mutation or repair execution occurred.

Initial local replay: Docker server 29.9.1; cached image `public.ecr.aws/supabase/postgres:17.6.1.158`; server PostgreSQL 17.6 aarch64. Dedicated container `kala-wi24-repair-125c`, database `wi24_synthetic`, no published port. Database created from template0. Minimal synthetic auth.jwt/auth.uid and storage bucket/object/foldername scaffolding supplied only to satisfy migration dependencies; not full GoTrue/Storage services or an RLS acceptance claim. All 37 migrations replayed in filename order with ON_ERROR_STOP and passed unchanged.

Two setup failures were corrected before replay: cloning postgres failed due to image-owned sessions; first synthetic auth.uid definition preceded auth.jwt and failed, then functions were created in dependency order. Neither involved hosted systems.

Catalog inspection includes public identity-bearing columns, all PK/unique/FK constraints, unique index predicates and all non-internal triggers. Five append-only tables were found: evidence_events, audit_log, lti_launches, item_reviews, practice_answer_results. Derived XP has no persisted reward table; source reviews/results must survive repair.

Current official Supabase changelog retrieved 2026-10-25: recent breaking change concerns HTTP API TLS ciphers, not this local SQL design. PostgreSQL current ALTER TABLE and pg_dump documentation checked: explicit trigger suspension is table-scoped, and pg_dump has no WHERE row filter. Sources are linked below; no hosted project was queried.

## Not yet proved

No apply implementation, one-sided/two-sided successful merge, no-op rerun, exact backup/restore, worker recompute integration or hosted readiness is claimed. Findings that prevent safe generic source-key collision handling are explicit stop conditions under APPROVAL-07 section 3.

## Sources

- [Supabase changelog](https://supabase.com/changelog)
- [PostgreSQL ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)
- [PostgreSQL pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html)

## Reproducible local proof

Design commit: `ce58ee6881105ead01a2343ecaad2411a731f49a`, before any test/script code. Dedicated [runner](../../../../scripts/tests/identity_repair/replay.py), [synthetic SQL](../../../../scripts/tests/identity_repair/blockers.sql), [full schema catalog](../../../../scripts/tests/identity_repair/catalog.txt) and [migration digests](../../../../scripts/tests/identity_repair/migrations.sha256) are retained. No application or migration changes.

`python3 scripts/tests/identity_repair/replay.py` passed on a fresh randomly named container/database:

```text
PASS 37 immutable migrations; schema catalog matches
PASS source-key/session collisions and exact resolver conflict reproduced
PASS injected transaction failure restores evidence and immutable trigger
PASS synthetic source row counts conserved; fixture transaction rolled back
```

The collision tests cover item_reviews idempotency, its partial session uniqueness and practice_answer_results idempotency. Every source pair still has two original rows after failed mutation; a narrowly suspended evidence update and injected exception restore original attribution and trigger state. The resolver conflict test reproduces its exact SQL predicate, not an application call.

Runner startup initially sampled the image's temporary init server; replaced readiness sampling with its configured healthy state. An intermediate docker top attempt lacked a PID column and was removed. Final fresh replay passes; failures did not change retained migrations or reach hosted data.

Documentation checks: `python3 scripts/docs_check.py` passed; `python3 -m unittest discover -s scripts -p 'test_docs_check.py'` passed 18 tests. These results do not close WI-24 or release FG-7a. Safe one-sided/two-sided apply, no-op rerun, exact backup/restore, derived recomputation and concurrency remain unimplemented because the design explicitly stops on unresolved source/provenance decisions.
