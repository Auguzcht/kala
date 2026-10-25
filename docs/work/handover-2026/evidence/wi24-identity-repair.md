# WI-24 local implementation evidence

Date: 2026-10-25. Lane M, branch `codex/wi24-identity-repair`. Initial base `d75284ec748ce562c1fe85a223ed5bef4ac53c13`; coordinator integration base is recorded in the final audit. Owner remains ITO. **Local proof only: no hosted query, real pair input, credentials, repair, deployment, merge or push. FG-7a/7b/9 remain unreleased.**

## Design before implementation

Original design commit `ce58ee6` (rewritten by integration rebase) preceded inventory test code. Bounded implementation design `c048038` preceded repair script code; post-worker exact-capture design `22f15f4` preceded capture code; estimate-verification design `bb531bc` preceded numerical verifier code. Coordinator AUTH manual exception `bf750f7184c1e0ec718aba686d607f26ed08caff` was read before alias-changing code. The initial blocked design was resolved by the coordinator's explicit bounded choices, not by rewriting source history.

[Runbook](../../../runbooks/identity-repair.md) describes the current procedure, exact six-field JSON input, checked retired LMS marker, deterministic collisions, private backup, source transaction, worker verification/capture and exact restore. Public commands are reviewable but unexecuted against hosted services. Both profiles remain unchanged metadata; legacy actor/launch/audit references remain historical. Unsafe pairs block the whole transaction.

## Runtime and isolation

- Python **3.13.14**, invoked through repo `uv run --directory services/api --no-sync python`; Python 3.10+ required. No new Python dependency, app import/configuration, dotenv or package/lock change.
- Docker server **29.9.1**; cached `public.ecr.aws/supabase/postgres:17.6.1.158`; PostgreSQL **17.6**, aarch64. PostgreSQL client tools **17.10**.
- Catalog runner: own random container, no published port, template0 database. Full CLI runner: own random container, random **127.0.0.1-only** port, fresh `wi24_source`, `wi24_backup`, `wi24_restore` databases. Neither runner resets/reuses another lane's database. Fixtures remove only their own containers/private synthetic artifacts.
- Minimal synthetic auth/storage SQL interfaces satisfy migration dependencies; this is not full GoTrue/Storage service or tenant RLS acceptance. All **0001–0037** migrations replay unchanged; full public column/PK/unique/FK/index-predicate/trigger metadata is compared with the retained catalog.
- No application runtime is bootstrapped. The unchanged resolver and worker function bodies are compiled from their real files into isolated namespaces with synthetic local SQL transport; resolver profile/alias-refresh writes are stubbed to isolate mapping decisions. Worker jobs execute their real write/replay logic with synthetic K=0.15. This is not deployed-worker/HTTP acceptance.

## Commands and observed results

From repository root:

```sh
uv run --directory services/api --no-sync python ../../scripts/tests/identity_repair/replay.py
uv run --directory services/api --no-sync python ../../scripts/tests/identity_repair/test_local.py
uv run --directory services/api --no-sync python ../../scripts/docs_check.py
uv run --directory services/api --no-sync python -m unittest discover -s ../../scripts -p test_docs_check.py
uv run --directory services/api --no-sync python -m py_compile ../../scripts/repair_identity_split.py ../../scripts/tests/identity_repair/test_local.py ../../scripts/tests/identity_repair/application_adapters.py
git diff --check
```

The real-PG inventory proof passes all 37 migration replays, catalog/checksum comparison, immutable review/result key/session collisions, exact resolver-conflict predicate, and narrow-trigger failure rollback/source conservation.

The full CLI proof passes these **14 groups**:

```text
PASS canonical-only consent exposure counterexample; governance refusal and converged no-op
PASS canonical/legacy schedule winners and exact ties; multiple attempt renumbering and restore
PASS public CLI dry-run/apply/no-op/unsafe collision refusal; counts-only stdout
PASS unchanged resolver function body before/after tombstone and alias transition
PASS unchanged worker job bodies; exact post-worker derived capture and restore
PASS uncaptured worker changes refuse restore; source unchanged by refusal
PASS scoped local pg_dump/pg_restore; collision losers, attempt numbers, derived preimages restored
PASS public CLI injected apply/restore failure rollback; trigger states restored
PASS concurrent source access blocked; incomplete worker replay refused
PASS later activity refuses restore; exact postimage required
PASS mixed-outcome timestamp ties refused; wrong estimates refused despite correct counters
PASS profiles/consent/DSR/attachments/roles/aliases/stale mastery and unconstrained tenant guards
PASS remote/option/same-source staging refused before staging writes
PASS libpq endpoint override environment discarded; no hosted connection
```

Representative main fixture counts (synthetic only):

| Check | Before | After apply | After worker/capture | After exact restore |
| --- | --- | --- | --- | --- |
| Evidence rows | 3 | 3, all canonical | 3 | exact original IDs/payloads/owners/timestamps |
| Saved answer XP sum | 36 | 36 | 36 | 36 |
| Readiness snapshots | 3 | 1 canonical historical | 3 (old + two new current) | exact original 3 |
| Mastery rows | 3 split | 1 canonical | 2 verified replay pairs | exact original 3 |
| Evidence timestamp mismatches | 0 | 0 | 0 | 0 |

Additional actual CLI roundtrips cover legacy/latest schedule win, canonical/newer win, canonical exact-tie win and multiple legacy attempts renumbered after canonical max without transient uniqueness conflicts; all original attempt numbers and collision losers restore exactly. Unsafe key/session collisions preserve every source row and prevent the safe pair from being partially applied. No-op apply preserves post-worker derived state and adds no merge audit.

Private binary scoped copies are loaded into typed local tables and dumped there; no hosted staging object or fictitious pg_dump WHERE flag. Archive restoration into a fresh local database and exact PK-delta restore prove the preimages, including derived state. Original affected.dump remains unchanged when exact post-worker rows are captured separately in recompute.dump. Manifest/audits retain archive hashes and confirmed K/source digest. Restore refuses uncaptured recompute and later activity; injected failures roll back source and trigger state. Old audits remain immutable; new merge/capture/rollback audits remain as history.

The public hidden failure option validates a loopback source before connection, even for failure tests. Ordinary maintainer commands accept a named source service after planner release and Fred gates; no code-edit bypass is required. Staging rejects remote endpoints, option indirection and source database reuse before staging writes; inherited PG connection overrides are removed. Server major/encoding must match for binary transport; session formatting and hash ordering are normalized. Public stdout contains no IDs, names, emails, content, raw errors or private paths.

Documentation checker and **18** checker unit tests pass; Python compilation and diff whitespace checks pass. No frontend/API/worker suite claim is made by this script-only lane; coordinator owns integration suites. No additional lint tool was installed.

## Verification limits and gates

- Full canonical replay estimates are verified with the existing worker `_replay` body, not merged/written by the repair. Fred must confirm the actual deployed worker revision/K at FG-7b; local K=0.15 does not establish hosted configuration.
- The worker's 50,000 code ceiling is distinct from a lower PostgREST row cap. Apply refuses institutions at/above the code ceiling; capture checks all affected evidence groups, exact attempts/last_seen/estimates and readiness against direct SQL, detecting incomplete affected-pair reads. Mixed-outcome equal timestamps refuse because worker replay has no ID tiebreak.
- Capture requires one controlled readiness pass while learner writes remain quiesced. Multiple runs, changed canonical history or later activity refuse; no general rollback after resumed live use is claimed.
- Readiness jobs append current snapshots and do not recreate historical readiness. Only legacy derived rows are deleted; canonical history survives. Legacy attachments, consent/DSR records on either anchor for non-converged pairs, unequal profiles, ambiguous identities/roles and stale canonical mastery refuse instead of guessing.
- Actual hosted mappings/counts, local/hosted server compatibility, human gate review, repair, deployed worker result and live acceptance remain unverified. WI-24 stays open.

## Earlier setup findings

Initial manual fixture cloning failed because the image had active sessions; template0 solved it. An initial auth scaffold defined uid before jwt; creation order was corrected. A temporary readiness probe sampled the image's init server; the final runner waits for the image health check. An intermediate docker top probe lacked a PID column and was removed. Full CLI fixture host authentication was explicitly synthetic-only in its isolated container. Final fresh runners pass; no real values were used.

## Sources

Current official Supabase changelog was checked on 2026-10-25; the recent breaking TLS-cipher change concerns HTTP APIs, not this local SQL procedure. PostgreSQL docs informed explicit trigger locking, scoped client COPY, local dump/restore and service/environment precedence.

- [Supabase changelog](https://supabase.com/changelog)
- [PostgreSQL ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)
- [PostgreSQL pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html)
- [PostgreSQL 17 COPY](https://www.postgresql.org/docs/17/sql-copy.html)
- [PostgreSQL 17 connection services](https://www.postgresql.org/docs/17/libpq-pgservice.html)
- [PostgreSQL 17 environment settings](https://www.postgresql.org/docs/17/libpq-envars.html)

## Focused final governance finding

Coordinator identified that canonical-only consent could broaden research reach without changing a consent row. Design boundary was committed at `83dafa1` before the guard change. A synthetic researcher/grant/canonical-consent fixture uses the real has_consent/research_evidence_anon logic: visible rows are **0**, a narrowly scoped attribution inside an isolated transaction makes them **1**, and rollback restores **0**. Public apply then refuses CONSENT_PRESENT before any source write. Canonical-only DSR also refuses. Already-converged no-op remains allowed with canonical consent and changes no source row. No policy, view or consent semantics were modified.

Related later-activity audit guards now include exact actor/row and old/new user/identity fields, detecting service-role governance changes even if their live rows are removed. Exact restore preserves appended maintenance audits and verifies the original scoped audit prefix unchanged, rather than deleting history to match an old row count. The full 14-group CLI proof passes with these guards.
