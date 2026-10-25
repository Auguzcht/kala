# WI-24 synthetic local proof

Use Python 3.10+; the verified repo uv runtime is Python 3.13.14. From repository root:

```sh
uv run --directory services/api --no-sync python ../../scripts/tests/identity_repair/replay.py
uv run --directory services/api --no-sync python ../../scripts/tests/identity_repair/test_local.py
```

Requires Docker with cached `public.ecr.aws/supabase/postgres:17.6.1.158`, and PostgreSQL 17 client `psql`, `pg_dump`, `pg_restore` on PATH. No additional Python dependencies. Neither runner imports app configuration or reads dotenv. They do not require service Python packages.

`replay.py` creates a dedicated random container with no published port, replays 0001–0037 and verifies the full metadata catalog and migration checksums. `test_local.py` creates its own random container with a random **loopback-only** port and three named fresh databases. Synthetic trust auth exists only in that isolated test container. Minimal auth/storage interfaces satisfy migration dependencies; this is not a complete Supabase service or RLS acceptance test. Each runner removes only its own container. Private input/copies/dumps/manifests live under gitignored tmp and are removed in finally.

The public CLI is exercised for read-only dry run, supported one-sided/two-sided merges, safe SRS winners/ties, overlapping attempt numbers, no-op rerun, blocked source keys/sessions and other guards, injected transaction failures, post-worker capture, later-activity refusal and exact restore. Files are private, output has only fixed labels/counts/reasons, and source payload/timestamp invariants are checked by the actual apply SQL. Restore includes schedule losers, original attempt numbers, original derived state and canonical readiness history. New merge/capture/rollback audit records remain; historical audit/launch/decision references remain unchanged.

`application_adapters.py` compiles the unchanged resolver and worker function bodies from their real source files, binding only synthetic local SQL transport and fake worker settings. Resolver profile/alias refresh side effects are stubbed so the test isolates mapping decisions; unexpected identity creation fails. Worker jobs execute their real replay/write logic. This avoids application import/config/network side effects; it is not hosted HTTP or deployment acceptance. Public capture independently rejects wrong estimates even with matching counters/timestamps and requires the confirmed pre-apply worker K. Ambiguous mixed-outcome timestamp ties refuse before apply.

The hidden local failure-test option forces a validated local source endpoint. It cannot inject failure against a hosted source. The ordinary maintainer CLI accepts an explicit source service after coordinator review/Fred gates; it needs no code edit or bypass flag. These tests never supply a hosted service.

The final governance proof executes the real research view/consent helper with a synthetic researcher. Canonical-only consent can expose moved legacy evidence (0 to 1 rows); the hypothetical move is rolled back, then public apply refuses before writes. Non-converged pairs block any consent/DSR on either anchor. Converged no-op remains allowed. Related audit old/new identity references guard later governance activity; exact restore preserves appended audits and proves the original scoped audit prefix unchanged.
