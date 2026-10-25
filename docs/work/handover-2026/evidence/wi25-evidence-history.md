# WI-25: complete evidence history

Date: 2026-10-25. Environment: local synthetic only. Branch: `codex/wi25-evidence-history`.
Base: `9c24a85b4bd21ca9995073dd078e2b3f66ea8325` plus the working-tree paths recorded below. Requirements: TWIN-REQ-010 / INSTR-REQ-010, coordinator-owned specs committed before implementation. Authority: APPROVAL-07 section 2 and Amendments 1–3.

## Query and cursor verification

`cd services/api && uv run pytest tests/test_evidence_history.py -q`: **24 passed**. Uses committed `services/conftest.py`; dotenv disabled, inherited application settings replaced and IPv4/IPv6/DNS blocked. No hosted calls or credentials.

Scenarios: first/next/final/empty/exact-limit pages; equal timestamp ID ties; limit bounds; malformed/noncanonical/tampered/wrong-version cursors; timestamp/UUID validation; caller/target/course/institution binding; secret rotation; concurrent newer arrival; valid cutoff after anchor removal/re-attribution; scoped approved skill names. These query tests do not assert route admission.

The new helper reads only evidence and approved skill names, explicitly filtering tenant/user/course and ordering `(created_at DESC, id DESC)`. Existing bounded responses are untouched. Cursor HMAC is domain-separated from the existing JWT secret; no new setting, TTL, anchor query, evidence/XP write or model call is added.

## Local database proof

Dedicated container: `kala-wi25-history-pg`, network disabled, no host port mapping. Image: `public.ecr.aws/supabase/postgres:17.6.1.158`; PostgreSQL reports 17.6. This container was created for H and no other lane's database was reset/reused.

Historical 0001–0037 replay completed byte-for-byte. The database image lacks the service-managed auth/storage bootstrap: initial replay stopped at missing `auth.jwt()`, then at `storage.buckets`. Minimal synthetic `auth.jwt()`, storage buckets/objects and foldername shims were installed only in this throwaway database. Replay resumed at the failed files; no migration source was changed. This is a database replay with bootstrap shims, not a full running Supabase service stack.

0039 applied twice successfully. The runbook's actual pre-check and guarded apply/post-check SQL ran successfully. A transactionally created conflicting index was rejected with the expected mismatch; connection abort rolled the probe back. The correct index definition survived.

`services/api/tests/fixtures/evidence_history_local.sql` passed on the replay. Its 61 synthetic events include timestamp ties. The PostgREST-equivalent OR predicate matches native tuple ordering with 26-row lookahead. `EXPLAIN` selects `evidence_events_history_idx` for user/course ordering, with institution as an explicit row filter; no leading institution column is needed. `enable_seqscan=off` demonstrates index eligibility only, not measured production latency. All fixture rows rolled back.

All **37** historical migration files compare byte-identically with the base. Only new 0039 is added by H. Hosted FG-6 is pending Fred.

## Frontend verification

Frozen-lockfile install completed without changing dependency manifests/lockfile. Web lint passes with 18 pre-existing Fast Refresh warnings; typecheck and production build pass. Build retains existing large-chunk warnings.

The independent history hook scopes cached pages by institution/caller/target/course and stores cursor identity in TanStack pageParams. It does not retain previous-scope data. Loaded pages deduplicate by ID in server order. Shared ledger ten-row pages and reduced-motion behavior remain intact. The new wrapper keeps bounded fallback labels until history succeeds, labels loaded counts, retries failures while retaining rows, and resets the whole cursor chain on Reload activity. Readiness charts/statistics keep their original bounded arrays.

Dedicated `evidence-history.browser.mjs` is written for student Twin and instructor record, at 375/1440 and reduced/normal motion: older loading through the earliest event, keyboard activation, 40px controls, failure/retry, invalid-cursor reload, final-page behavior, overflow, and no mutations. **Execution pending coordinator handover of port 5173.** Retained UI/tour fixtures were not edited.

## Remaining integration

New own/staff routes, authorization integration tests and generated OpenAPI/types are pending SEC merge and explicit router-phase release. H has not edited twin/dashboard routers or generated files. Coordinator owns generation after integration. Full API suite on this pre-route working tree: `cd services/api && uv run pytest -q` — **634 passed**, 30 dependency deprecation warnings, 28.66s. This does not verify the pending routes.

Retained fixture proposal: add a synthetic `/evidence` handler only where those suites intend active full history, and change their `Last 20/25 events` assertions to the loaded-activity wording with the synthetic feed's count. Fixtures that intentionally omit/fail history may retain legacy expectations. H does not change retained fixtures without coordinator direction.

No hosted read/write, deployment, push, migration application, real-user fixture or 5173 server action occurred.
