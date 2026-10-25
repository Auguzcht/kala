# Dev identity history repair — WI-24 design

Status: bounded local implementation authorized; **not released for FG-7a**. Local proof and coordinator review remain required. This is a one-time, maintainer-run repair of explicitly proved dev identities. Production and hosted execution remain Fred gates. No feature behavior is changed.

Read [database policy](../engineering/database.md), [AUTH contract](../features/lti-auth/README.md), [Twin contract](../features/twin/README.md), [gamification contract](../features/gamification/README.md) and [WI-24](../work/handover-2026/work-items/WI-24-dev-identity-history-repair.md). All 0001–0037 migrations are immutable.

## Bounded local design decisions

Coordinator decisions authorize collision-free source merges and explicit SRS/attempt collision rules locally. Any blocked pair refuses the entire apply transaction before writes. Refuse source idempotency/session collisions, unequal dual profiles, legacy consents/DSRs/attachments, multiple unfinished attempts, ambiguous roles/aliases, foreign tenant relations and stale canonical mastery keys absent combined evidence. Never rewrite source keys, outcomes, counted flags, XP or timestamps; never deduplicate distinct source rows.

Proposed marker: `wi24-retired:<legacy-users.id>`. Preserve the original LMS ID in private backup and the new in-DB merge audit. Keep legacy users.id, role and historical metadata. Redirect aliases only after coordinator commits the AUTH manual-repair exception; implementation of this part waits for that commit. Refuse any existing tombstone/third-user identifier conflict. Application resolver simulations must prove canonical exact UUID/sub resolution before/after and retired legacy alias resolution afterward.

Keep all historical audit actor/row/JSON, skills.reviewed_by, recommendations.decided_by, researcher_grants.granted_by and lti_launches references unchanged. The shell has no active aliases/enrollments/learner ownership; historical actor references and identity profiles may remain. Old audit rows are never updated. Legacy attachments block; canonical attachments remain unchanged. No storage bytes, paths or RLS changes.

Delete only legacy mastery/readiness derived rows. Preserve canonical historical readiness. Worker upserts canonical mastery from combined evidence and appends a current readiness snapshot; it cannot reconstruct historical readiness. Refuse stale canonical mastery keys without combined source evidence. Refuse incomplete worker reads: its 50,000 code limit and a potentially lower PostgREST server row cap are independent limits. A local source replay proof cannot certify hosted worker transport completeness.

## Inventory and deterministic rules

The complete catalog of **all** public primary/unique/FK constraints, unique indexes (including predicates) and non-internal triggers is retained in the dedicated schema fixture after replay of all 37 migrations. The following table covers every user identity reference, including columns without FKs. Any new column, constraint, trigger or schema drift must stop the repair until reviewed.

| Table / columns | Keys, dependencies and rule |
| --- | --- |
| users.id, lms_user_id | PK id; UNIQUE institution/LMS ID; institution FK. Keep both user anchors; canonical chosen only from exact UUID/sub mapping. Legacy LMS key uses the proposed reserved marker only after the AUTH exception commit. |
| lms_identity_aliases.user_id | PK institution/LMS ID; user and institution FKs. Redirect only aliases already belonging to the listed legacy user; third-user alias/exact-user conflicts stop. Preserve source/timestamps. |
| user_profiles.user_id | PK/FK user. Source PII, not derived. Keep profiles as identity metadata; refuse unequal dual profiles. Never use profile values to prove identity. |
| enrollments.user_id | PK user/course; user/course/institution FKs. Same-role collision: retain canonical enrollment, remove duplicate enrollment; different role stops. Move unique enrollments; legacy ends unenrolled. Audit trigger remains active. |
| evidence_events.user_id | UUID PK; user/course/skill/institution FKs. Change only user_id for exact preselected legacy row IDs; preserve all payload/time/IDs. Under APPROVAL-07 Amendment 1, snapshot `(id,created_at)` for every selected row before mutation and require exact timestamp equality for every moved ID afterward; never replace created_at or introduce occurred_at. Cursor order is `(created_at DESC,id DESC)`. Suspend only t_immutable around that statement under exclusive table lock. |
| mastery_state.user_id | PK user/skill; user/course/skill/institution FKs. Delete legacy rows only; block canonical stale keys absent combined evidence. Worker upserts canonical state; no numerical merge. |
| readiness_snapshots.user_id | UUID PK; user/course/institution FKs. Delete legacy derived snapshots only; preserve canonical historical snapshots. Back up exact preimages. Existing job appends a current snapshot; it cannot recreate historical time-series values. |
| srs_state.user_id | PK user/item; user/course/item/skill/institution FKs. One schedule per card. Select entire row with greatest last_reviewed_at NULLS LAST, then created_at, then canonical side on ties; retain losing row in exact private backup. Do not sum box/reps/lapses. Move noncolliding rows. Card memory extensions 0026/0029/0030 are part of the selected whole row. |
| quiz_set_attempts.user_id | UUID PK; UNIQUE user/set/attempt_number after 0034; user/course/set/institution FKs. Keep canonical numbering; order legacy rows by old attempt_number, id, allocate sequentially after canonical max, then move. Refuse smallint overflow, malformed relations or multiple unfinished attempts in a set (no safe active-attempt rule). Keep IDs, counters, completion and timestamps. |
| practice_answer_results.user_id | UUID PK; UNIQUE user/idempotency key and attempt/item; attempt FK ON DELETE CASCADE, item FK. Do not delete attempts. Preserve attempt_id links, immutable answers, XP and keys. Reattribute only collision-free rows; stop for decision 1 otherwise. Trigger practice_answer_results_immutable needs narrowly scoped suspension, never all triggers. |
| item_reviews.user_id | UUID PK; UNIQUE user/key and partial user/item/session; item FK; user/institution/course/skill IDs have no FK. Validate manually. Preserve counted/outcome/session/key/time. Collisions stop; trigger t_immutable requires narrow suspension. |
| item_exposures.user_id | PK user/item; user/course/skill/item/institution FKs. Independent max studied/tested/answered timestamps; last_correct follows latest answered row (tie canonical); times_tested sum only when both sides equal their own saved set-answer counts, proving disjoint attempt sources; otherwise stop. Preserve earliest created_at and latest updated_at; retain both preimages. |
| tutor_conversations.user_id | UUID PK; user/course/institution FKs. Move ownership only, preserve IDs, title, created/updated/pinned timestamps. |
| tutor_messages.conversation_id | No user column; UUID PK, conversation FK cascade. Preserve messages unchanged via unchanged conversation IDs. |
| tutor_attachments.user_id, storage_path | UUID PK; user/conversation/institution FKs. Preserve attachment metadata/content and conversation IDs. Any legacy attachment blocks the entire transaction; canonical attachments stay unchanged. |
| recommendations.user_id, decided_by | UUID PK; user/course/skill/institution and deciding-user FKs. Move learner target; preserve decisions/status/rationale/times. Keep decided_by historical actor unchanged. No user composite uniqueness. |
| consents.user_id | UUID PK; user/institution FKs. Historical legal consent, not ordinary derived state. Stop if any legacy rows: merging latest-wins consent can change research access. Separate explicit policy required. Audit trigger remains active. |
| data_subject_requests.user_id | UUID PK; user/institution FKs. Governance records: stop if legacy rows pending explicit legal identity decision. Audit trigger remains active. |
| lti_launches.user_id | UUID PK; user/institution FKs; t_immutable. Preserve launch provenance on legacy with merge linkage; never reattribute. No assumption that launches are actually recorded by current routes. |
| researcher_grants.granted_by | UUID without user FK; researcher_id references separate researchers, not users. Historical actor: retain original. Audit trigger remains active. |
| skills.reviewed_by | Text LMS ID, no user FK. Never guess or globally replace matching strings. Historical actor: retain original. |
| audit_log.actor_id, row_id, old_data, new_data, metadata | bigint PK; no user/tenant FK; t_immutable. Preserve old rows and identifiers/JSON exactly. New merge row links both anchors, actor current_user, timestamp, mapping proof, per-table counts and backup digest IN DATABASE. No IDs/payloads in stdout. |
| rewards / XP | No persisted reward/XP table in 0001–0037. Derived from evidence, counted item_reviews and practice_answer_results.xp_awarded; preserve all source rows and XP fields, never call grading/review RPCs. Opening views creates no reward source rows. |

Course/content/generated-item/lesson/quiz-set/bank/ingest/generation/worker-state tables have no learner ownership column. Their IDs remain unchanged. Researchers are a separate principal domain. Audit JSON may contain historical IDs and is provenance, not an invitation to recursive replacement.

## Input, identity proof and output contract

Fred creates a mode-0600 local JSON file under gitignored `tmp/` containing explicit institution, canonical user, legacy user, validated LMS UUID/sub proof, actor reference and approved course scope for each pair. Check `git check-ignore` before reading it. Reject symlinks, overlapping pairs, same user twice, unknown IDs, cross-tenant users/relations and ambiguous alias mappings. Never select by name or email; never echo input, SQL parameters, connection strings, database errors with DETAIL, row data or paths with embedded identifiers. Use libpq service/passfile configuration maintained locally by Fred, no credentials in arguments or .env. The agent uses only its own Docker database.

Canonical resolution must match the exact current resolver: UUID equals validated launch subject; alias target and exact users row, if both present, agree. An alias source label or email match is not proof. Check listed course and institution scope on every row and every related entity, including tables lacking FK constraints. Third-user or cross-scope links stop. Schema catalog must match the reviewed replay except explicitly reviewed 0038 policy/0039 index additions.

Dry run defaults to a read-only transaction and prints only pair labels, static table/rule names, counts, boolean convergence/blocked status and fixed reason codes. Example format (illustrative, not observed):

```text
pair 1 evidence_events move=40 collisions=0 rule=reattribute
pair 1 srs_state move=2 collisions=1 rule=latest_review
pair 1 converged=false blocked=true reason=POLICY_REQUIRED
```

Apply requires BOTH `--apply --confirm`; a single flag fails without connecting. It also requires a verified backup manifest. Dry run cannot print an apply-ready claim while any decision above is unresolved. No apply command is released by this design.

## Transaction and concurrency design

After release, one transaction covers every approved pair, all attribution/derived cleanup and merge audit inserts. Set bounded lock/statement/idle-transaction timeouts. Acquire ACCESS EXCLUSIVE locks on affected tables in a stable alphabetical order before inventory, row-ID selection and backup snapshot; use NOWAIT or a short timeout and fail cleanly. Include all actor/governance tables touched or inspected for guard conditions and dependent source tables. This intentionally blocks concurrent writers/readers briefly; Fred must arrange a maintenance window and quiesce workers through separately gated procedures. A per-pair advisory lock alone cannot protect against ordinary app writers.

Capture exact row-ID sets while locked, prove scope and collision rules again, then suspend one named immutable trigger for exactly one UPDATE whose WHERE clause uses both the exact captured IDs and listed legacy user/institution. Restore that trigger immediately before any next operation; assert its enabled state and affected-row count. An UPDATE must change only user_id. Repeat separately for every authorized immutable table; never disable all triggers, FK triggers, RLS, session_replication_role or replace forbid_mutation globally. Existing audit triggers stay active. On any exception, connection loss, timeout or failed post-check, rollback the transaction, including DDL trigger state. Capture stdout only from fixed count structures after commit or read-only rollback; all database exceptions are reduced to fixed reason code/SQLSTATE without DETAIL.

Post-check exact event/review/result ID sets and hashes excluding user_id, per-ID evidence created_at equality (zero missing IDs and zero timestamp mismatches), source count conservation, XP sums, attempt links, uniqueness, no cross-tenant moves, zero legacy enrollments, alias convergence per approved shell rule and restored trigger states. Audit remains append-only; no-op rerun must insert no additional merge audit or delete recomputed derived state. Store successful merge identity in audit metadata; recognize completed pairs only after validating convergence, never just because a marker exists.

## Exact local backup and rollback design

No hosted staging schema. Use a second, typed **local-only** staging database, reached through a libpq service. Validate its server address is loopback/Unix socket and it differs from source. Create only local `wi24_backup` tables with source column types, no copied FKs/defaults/triggers. The backup must include both users' complete affected learner rows, original users/aliases, collision losers, original attempt numbers, and derived preimages. Scope is exact row selections, not whole hosted tables. Protect backup directory/files mode 0700/0600 and refuse symlinks or tracked input/output paths.

Before apply, lock source tables in alphabetical order with bounded timeouts; materialize pair inputs into temporary tables; validate all scope/collision rules. Use binary COPY-to-local while the source locks remain held; load those exact files into typed local tables; pg_dump only this local schema to a private custom archive. Include migration/catalog/preimage digests and counts in a private manifest. Recheck source snapshot digests against the manifest before the first source write. If local backup/dump fails, rollback without source changes. Credentials stay in libpq service/passfiles, never argv or output. No .env use.

All source writes are in that one transaction, including exact immutable source-row updates, deterministic state collision resolution, derived legacy cleanup and in-DB merge audit. The source connection remains open while the local backup completes; a bounded idle timeout makes interruption fail safely. Do not use a second source session to inspect uncommitted temp tables.

Postimage manifest includes exact affected rows after apply and the preexisting immutable audit digest. Restore first verifies every affected current row matches the postimage, including canonical and legacy identities, aliases, source rows, state and derived rows. Any later activity, including worker recomputation, refuses rollback until an exact new manifest of recompute PKs/preimages has been reviewed/proved. Add an explicit post-worker capture while learner writes remain quiesced. Under the same source table locks, refuse any non-derived postimage change; verify all canonical mastery keys/counts/last_seen against combined evidence (no source cap), zero legacy derived rows, unchanged canonical historical readiness, and exactly one new current snapshot per eligible student/course with score matching approved mastery. Copy the exact current mastery/readiness rows, including their PKs, into a new typed local staging schema and private `recompute.dump`; retain the original `affected.dump` unchanged. Record both archive digests, before/after derived digests/counts and the resulting full postimage in the private manifest and in-DB capture audit. This captures exact PKs/preimages, without time-window guesses. Restore verifies both archives and the full current captured postimage, then reverses exact PK deltas to the original preimages. Any later activity or incomplete/malformed worker output still refuses rollback; no claim of general rollback after live use.

A safe local restore uses the typed backup archive, verifies its digest/schema and preimage/postimage manifests, locks source tables again, and reverses only exact modified rows. Preserve all original source IDs/payloads. Restore attempt ownership/numbers without deleting attempts (their FK cascades to saved answers); restore losers and derived preimages explicitly in dependency order. Suspend only each exact named immutable trigger around its one exact-ID statement, restore immediately; audit triggers remain active and a new rollback audit records the operation. Do not erase old or merge audit records. Refuse any collision/out-of-scope relation or later activity. No whole-table restore, cascading deletes, RLS bypass changes or session_replication_role.

Before FG-7a require executable proof of archive restore, every collision loser, original attempt numbering, exact derived preimages, source payload/timestamp conservation, injected failure rollback and refusal after later activity/recompute. No hosted restore command is released until this proof passes. If exact restore cannot be delivered within this bounded script, stop with that concrete limitation.

## Worker recomputation limits

After approved apply Fred can invoke the existing worker handler with institution scope through a separately reviewed hosted gate, or wait for the scheduled run. The normal handler orders reconcileMastery before readinessSnapshot; use existing jobs, never grading/review functions. No AWS command is executed by this lane. Reconcile only upserts, so delete only legacy derived rows and block stale canonical keys absent combined evidence before apply. It caps each institution at 50,000 evidence rows without pagination: stop if completeness cannot be proved below that cap. Match supported tracer K before replay and record equal-timestamp ordering limits. Readiness rebuild creates a new current snapshot, not replacement historical values. Count rebuilt skill pairs and current snapshots; no raw IDs or learning payloads enter gate output.

## Local proof and release checklist

A dedicated Docker Supabase Postgres container/database with no published port replays all 0001–0037 migrations; synthetic auth/storage SQL scaffolding is identified explicitly and is not a complete Supabase service/RLS proof. Record actual server/image versions. Capture the full constraint/unique-index/trigger catalog and migration hashes.

Local fixtures must exercise one-sided history, two-sided history with schedule/attempt collisions, source-key collisions (safe stop), conflicting aliases/profiles/roles, cross-tenant rows including unconstrained tables, append-only launches/reviews/results, attachments, source payload conservation and rewards. Prove dry-run immutability, apply, post-checks, no-op rerun, rollback of injected mid-transaction failure, trigger restoration, concurrent writer blocking, backup/restore including collision losers/renumbered attempts/derived recompute. No tests are evidence of unexecuted behavior.

Coordinator reviews design, proof and counts format before Fred gets FG-7a. FG-7b remains separate after real dry-run review. WI-24 stays open until real acceptance. No deployment, push, merge, hosted connection or cleanup of this worktree is authorized.

## Verified by

- [APPROVAL-07, section 3](../work/handover-2026/approval-07.md)
- [WI-24 inventory evidence](../work/handover-2026/evidence/wi24-identity-repair.md)
- [Local schema fixtures](../../scripts/tests/identity_repair/)

## Implementation sequencing

This bounded design update is committed before implementation. Source-key refusal, local backup transport, deterministic SRS/attempt operations and fixtures may proceed independently. Coordinator AUTH manual exception is committed at `bf750f7184c1e0ec718aba686d607f26ed08caff`; checked alias/tombstone code may now proceed locally. Every evidence UPDATE preserves exact created_at by ID; no occurred_at schema change. Keep WI-24 owner ITO and open until FG-7b plus FG-9.

The local backup service permits only explicit loopback host, numeric port, simple database name and a minimal libpq option whitelist. Reject connection-option/service indirection and inherited PG endpoint/option overrides before connection. Local fixtures prove public CLI dry-run/apply/no-op, failure refusals, post-worker capture and restore, plus actual resolver function bodies under synthetic local adapters. Profiles remain unchanged identity metadata on both anchors; unequal dual profiles block.

## Worker estimate verification amendment

Before apply Fred confirms the deployed worker revision and effective tracer_k. Apply requires explicit `--worker-tracer-k` and `--confirm-worker-config`, records that numeric parameter privately before source writes, and capture requires the same confirmed value. The verifier executes the existing worker `_replay` function body from the reviewed repository source in an isolated namespace, reads complete grouped correctness sequences internally, rounds exactly as the job does, and compares every stored estimate. It writes no derived values and emits only verified-pair/mismatch counts. Record the worker source digest in the manifest/audit. Attempts/last_seen/readiness checks alone do not establish a rebuild.

Refuse a pair before apply if evidence for a combined skill has equal created_at with differing Boolean targets (NULL is treated as false, matching the worker). The worker orders only by created_at; never apply the history endpoint's ID tiebreak to replay. Equal timestamps with the same target are order independent. Capture independently enforces this ambiguity check and refuses wrong estimates even when attempts/last_seen already match.
