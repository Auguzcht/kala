# WI-24 local inventory and stop-condition proof

Run from repository root:

```sh
python3 scripts/tests/identity_repair/replay.py
```

Requires Docker with cached `public.ecr.aws/supabase/postgres:17.6.1.158`.
Creates a randomly named dedicated container and template0 database with no published port; removes only that container in finally. It does not use application imports, service environments, dotenv or hosted credentials. Docker CLI needs access to the configured local engine. No Python dependencies are required.

The committed catalog contains schema metadata only. `migrations.sha256` covers unchanged 0001–0037. The runner checks the full catalog after a fresh replay. Bootstrap auth/storage interfaces are synthetic scaffolding, not a complete Supabase service stack. Fixture data is generated entirely inside a rolled-back SQL transaction.

This proves actual unique-key/session collision failure, the alias/exact-user disagreement rejected by the current resolver's predicate, narrow-trigger DDL/data rollback after an injected failure and unchanged source counts. It does not call the application resolver, implement the repair, merge supported pairs, test worker jobs, test concurrent writers or prove backup/restore. The runbook remains blocked until those capabilities are approved and implemented. No repair script is deliberately supplied while its design has unresolved stop conditions.
