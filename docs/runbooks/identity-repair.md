# Dev identity history repair — WI-24 design

Status: bounded local implementation authorized; **not released for FG-7a**. Local proof and coordinator review remain required. This is a one-time, maintainer-run repair of explicitly proved dev identities. Production and hosted execution remain Fred gates. No feature behavior is changed.

Read [database policy](../engineering/database.md), [AUTH contract](../features/lti-auth/README.md), [Twin contract](../features/twin/README.md), [gamification contract](../features/gamification/README.md) and [WI-24](../work/handover-2026/work-items/WI-24-dev-identity-history-repair.md). All 0001–0037 migrations are immutable.

## Bounded local design decisions

Coordinator decisions authorize collision-free source merges and explicit SRS/attempt collision rules locally. Any blocked pair refuses the entire apply transaction before writes. Refuse source idempotency/session collisions, unequal dual profiles, consents/DSRs on either anchor and legacy attachments, multiple unfinished attempts, ambiguous roles/aliases, foreign tenant relations and stale canonical mastery keys absent combined evidence. Never rewrite source keys, outcomes, counted flags, XP or timestamps; never deduplicate distinct source rows.

Checked marker: `wi24-retired:<legacy-users.id>`. Preserve the original LMS ID in private backup and the new in-DB merge audit. Keep legacy users.id, role and historical metadata. The coordinator committed the AUTH manual-repair exception at `bf750f7` before alias-changing implementation. Refuse any existing tombstone/third-user identifier conflict. Application resolver simulations must prove canonical exact UUID/sub resolution before/after and retired legacy alias resolution afterward.

Keep all historical audit actor/row/JSON, skills.reviewed_by, recommendations.decided_by, researcher_grants.granted_by and lti_launches references unchanged. The shell has no active aliases/enrollments/learner ownership; historical actor references and identity profiles may remain. Old audit rows are never updated. Legacy attachments block; canonical attachments remain unchanged. No storage bytes, paths or RLS changes.

Delete only legacy mastery/readiness derived rows. Preserve canonical historical readiness. Worker upserts canonical mastery from combined evidence and appends a current readiness snapshot; it cannot reconstruct historical readiness. Refuse stale canonical mastery keys without combined source evidence. Refuse incomplete worker reads: its 50,000 code limit and a potentially lower PostgREST server row cap are independent limits. A local source replay proof cannot certify hosted worker transport completeness.

## Inventory and deterministic rules

The complete catalog of **all** public primary/unique/FK constraints, unique indexes (including predicates) and non-internal triggers is retained in the dedicated schema fixture after replay of all 37 migrations. The following table covers every user identity reference, including columns without FKs. Any new column, constraint, trigger or schema drift must stop the repair until reviewed.

| Table / columns | Keys, dependencies and rule |
| --- | --- |
| users.id, lms_user_id | PK id; UNIQUE institution/LMS ID; institution FK. Keep both user anchors; canonical chosen only from exact UUID/sub mapping. Legacy LMS key uses the checked reserved marker under the committed AUTH manual exception. |
| lms_identity_aliases.user_id | PK institution/LMS ID; user and institution FKs. Redirect aliases already belonging to the listed legacy user; create the original legacy LMS-key alias if missing; third-user alias/exact-user conflicts stop. Preserve source/timestamps. |
| user_profiles.user_id | PK/FK user. Source PII, not derived. Keep profiles as identity metadata; refuse unequal dual profiles. Never use profile values to prove identity. |
| enrollments.user_id | PK user/course; user/course/institution FKs. Same-role collision: retain canonical enrollment, remove duplicate enrollment; different role stops. Move unique enrollments; legacy ends unenrolled. Audit trigger remains active. |
| evidence_events.user_id | UUID PK; user/course/skill/institution FKs. Change only user_id for exact preselected legacy row IDs; preserve all payload/time/IDs. Under APPROVAL-07 Amendment 1, snapshot `(id,created_at)` for every selected row before mutation and require exact timestamp equality for every moved ID afterward; never replace created_at or introduce occurred_at. Cursor order is `(created_at DESC,id DESC)`. Suspend only t_immutable around that statement under exclusive table lock. |
| mastery_state.user_id | PK user/skill; user/course/skill/institution FKs. Delete legacy rows only; block canonical stale keys absent combined evidence. Worker upserts canonical state; no numerical merge. |
| readiness_snapshots.user_id | UUID PK; user/course/institution FKs. Delete legacy derived snapshots only; preserve canonical historical snapshots. Back up exact preimages. Existing job appends a current snapshot; it cannot recreate historical time-series values. |
| srs_state.user_id | PK user/item; user/course/item/skill/institution FKs. One schedule per card. Select entire row with greatest last_reviewed_at NULLS LAST, then created_at, then canonical side on ties; retain losing row in exact private backup. Do not sum box/reps/lapses. Move noncolliding rows. Card memory extensions 0026/0029/0030 are part of the selected whole row. |
| quiz_set_attempts.user_id | UUID PK; UNIQUE user/set/attempt_number after 0034; user/course/set/institution FKs. Keep canonical numbering; order legacy rows by old attempt_number, id, allocate sequentially after canonical max, then move. Refuse smallint overflow, nonpositive numbering, malformed relations, multiple unfinished attempts or a lifecycle that would hide an existing active attempt (no safe active-attempt rule). Keep IDs, counters, completion and timestamps. |
| practice_answer_results.user_id | UUID PK; UNIQUE user/idempotency key and attempt/item; attempt FK ON DELETE CASCADE, item FK. Do not delete attempts. Preserve attempt_id links, immutable answers, XP and keys. Reattribute only collision-free rows; refuse the whole transaction on source-key collision otherwise. Trigger practice_answer_results_immutable needs narrowly scoped suspension, never all triggers. |
| item_reviews.user_id | UUID PK; UNIQUE user/key and partial user/item/session; item FK; user/institution/course/skill IDs have no FK. Validate manually. Preserve counted/outcome/session/key/time. Collisions stop; trigger t_immutable requires narrow suspension. |
| item_exposures.user_id | PK user/item; user/course/skill/item/institution FKs. Independent max studied/tested/answered timestamps; last_correct follows latest answered row (tie canonical); times_tested sum only when both sides equal their own saved set-answer counts, proving disjoint attempt sources; otherwise stop. Preserve earliest created_at and latest updated_at; retain both preimages. |
| tutor_conversations.user_id | UUID PK; user/course/institution FKs. Move ownership only, preserve IDs, title, created/updated/pinned timestamps. |
| tutor_messages.conversation_id | No user column; UUID PK, conversation FK cascade. Preserve messages unchanged via unchanged conversation IDs. |
| tutor_attachments.user_id, storage_path | UUID PK; user/conversation/institution FKs. Preserve attachment metadata/content and conversation IDs. Any legacy attachment blocks the entire transaction; canonical attachments stay unchanged. |
| recommendations.user_id, decided_by | UUID PK; user/course/skill/institution and deciding-user FKs. Move learner target; preserve decisions/status/rationale/times. Keep decided_by historical actor unchanged. No user composite uniqueness. |
| consents.user_id | UUID PK; user/institution FKs. Historical legal consent, not ordinary derived state. For non-converged pairs, stop if either anchor has any row: canonical consent can expose moved legacy evidence through research_evidence_anon/has_consent even when consent rows are untouched. Already-converged no-op changes no attribution. Separate explicit policy required. Audit trigger remains active. |
| data_subject_requests.user_id | UUID PK; user/institution FKs. Governance records: for non-converged pairs, stop if either anchor has rows pending an explicit legal identity decision; preserve already-converged no-op. Audit trigger remains active. |
| lti_launches.user_id | UUID PK; user/institution FKs; t_immutable. Preserve launch provenance on legacy with merge linkage; never reattribute. No assumption that launches are actually recorded by current routes. |
| researcher_grants.granted_by | UUID without user FK; researcher_id references separate researchers, not users. Historical actor: retain original. Audit trigger remains active. |
| skills.reviewed_by | Text LMS ID, no user FK. Never guess or globally replace matching strings. Historical actor: retain original. |
| audit_log.actor_id, row_id, old_data, new_data, metadata | bigint PK; no user/tenant FK; t_immutable. Preserve old rows and identifiers/JSON exactly. New merge row links both anchors, actor current_user, timestamp, mapping proof, per-table counts and backup digest IN DATABASE. No IDs/payloads in stdout. |
| rewards / XP | No persisted reward/XP table in 0001–0037. Derived from evidence, counted item_reviews and practice_answer_results.xp_awarded; preserve all source rows and XP fields, never call grading/review RPCs. Opening views creates no reward source rows. |

Course/content/generated-item/lesson/quiz-set/bank/ingest/generation/worker-state tables have no learner ownership column. Their IDs remain unchanged. Researchers are a separate principal domain. Audit JSON may contain historical IDs and is provenance, not an invitation to recursive replacement.

## Input, identity proof and output contract

Fred creates a mode-0600 local JSON file under gitignored `tmp/` containing explicit institution, canonical user, legacy user, validated LMS UUID/sub proof and approved course scope for each pair. Check `git check-ignore` before reading it. Reject symlinks, overlapping pairs, same user twice, unknown IDs, cross-tenant users/relations and ambiguous alias mappings. Never select by name or email; never echo input, SQL parameters, connection strings, database errors with DETAIL, row data or paths with embedded identifiers. Use libpq service/passfile configuration maintained locally by Fred, no credentials in arguments or .env. The agent uses only its own Docker database.

Canonical resolution must match the exact current resolver: UUID equals validated launch subject; alias target and exact users row, if both present, agree. An alias source label or email match is not proof. Check listed course and institution scope on every row and every related entity, including tables lacking FK constraints. Third-user or cross-scope links stop. Schema catalog must match the reviewed replay except explicitly reviewed 0038 policy/0039 index additions.

Dry run defaults to a read-only transaction and prints only pair labels, static table/rule names, counts, boolean convergence/blocked status and fixed reason codes. Example format (illustrative, not observed):

```text
pair 1 evidence_events move=40 delete=0 retained_metadata=0 collisions=0 rule=reattribute
pair 1 srs_state move=2 delete=1 retained_metadata=0 collisions=1 rule=latest_whole_state
pair 1 converged=false
blocked=true reason=BLOCKED_PAIR
```

Apply requires BOTH `--apply --confirm`; a single flag fails without connecting. It creates and verifies a private exact backup before its first source write. Dry run reports blocked counts for any refused pair. Commands below are reviewable maintainer procedures, unreleased until coordinator review; preparing them grants no hosted authorization.

## Transaction and concurrency design

After release, one transaction covers every approved pair, all attribution/derived cleanup and merge audit inserts. Set bounded lock/statement/idle-transaction timeouts. Acquire ACCESS EXCLUSIVE locks on affected tables in a stable alphabetical order before inventory, row-ID selection and backup snapshot; use NOWAIT or a short timeout and fail cleanly. Include all actor/governance tables touched or inspected for guard conditions and dependent source tables. This intentionally blocks concurrent writers/readers briefly; Fred must arrange a maintenance window and quiesce workers through separately gated procedures. A per-pair advisory lock alone cannot protect against ordinary app writers.

Capture exact row-ID sets while locked, prove scope and collision rules again, then suspend one named immutable trigger for exactly one UPDATE whose WHERE clause uses both the exact captured IDs and listed legacy user/institution. Restore that trigger immediately before any next operation; assert its enabled state and affected-row count. An UPDATE must change only user_id. Repeat separately for every authorized immutable table; never disable all triggers, FK triggers, RLS, session_replication_role or replace forbid_mutation globally. Existing audit triggers stay active. On any exception, connection loss, timeout or failed post-check, rollback the transaction, including DDL trigger state. Capture stdout only from fixed count structures after commit or read-only rollback; all database exceptions are reduced to fixed reason code/SQLSTATE without DETAIL.

Post-check exact event/review/result ID sets and hashes excluding user_id, per-ID evidence created_at equality (zero missing IDs and zero timestamp mismatches), source count conservation, XP sums, attempt links, uniqueness, no cross-tenant moves, zero legacy enrollments, alias convergence per approved shell rule and restored trigger states. Audit remains append-only; no-op rerun must insert no additional merge audit or delete recomputed derived state. Store successful merge identity in audit metadata; recognize completed pairs only after validating convergence, never just because a marker exists.

## Exact local backup and rollback design

No hosted staging schema. Use a second, typed **local-only** staging database, reached through a libpq service. Validate the effective libpq service specifies only a literal loopback endpoint, reject option/environment indirection, and compare the actual server address/database against source before staging writes. Require equal server major and encoding for typed binary copies; normalize session timezone/date formatting and hash order. Create only local `wi24_backup` tables with source column types, no copied FKs/defaults/triggers. The backup must include both users' complete affected learner rows, original users/aliases, collision losers, original attempt numbers, and derived preimages. Scope is exact row selections, not whole hosted tables. Protect backup directory/files mode 0700/0600 and refuse symlinks or tracked input/output paths.

Before apply, lock source tables in alphabetical order with bounded timeouts; materialize pair inputs into temporary tables; validate all scope/collision rules. Use binary COPY-to-local while the source locks remain held; load those exact files into typed local tables; pg_dump only this local schema to a private custom archive. Include migration/catalog/preimage digests and counts in a private manifest. Recheck source snapshot digests against the manifest before the first source write. If local backup/dump fails, rollback without source changes. Credentials stay in libpq service/passfiles, never argv or output. No .env use.

All source writes are in that one transaction, including exact immutable source-row updates, deterministic state collision resolution, derived legacy cleanup and in-DB merge audit. The source connection remains open while the local backup completes; a bounded idle timeout makes interruption fail safely. Do not use a second source session to inspect uncommitted temp tables.

Postimage manifest includes exact affected rows after apply and the preexisting immutable audit digest. Restore first verifies every affected current row matches the postimage, including canonical and legacy identities, aliases, source rows, state and derived rows. Any later activity, including worker recomputation, refuses rollback until an exact new manifest of recompute PKs/preimages has been reviewed/proved. Add an explicit post-worker capture while learner writes remain quiesced. Under the same source table locks, refuse any non-derived postimage change; verify all canonical mastery keys/counts/last_seen against combined evidence (no source cap), zero legacy derived rows, unchanged canonical historical readiness, and exactly one new current snapshot per eligible student/course with score matching approved mastery. Copy the exact current mastery/readiness rows, including their PKs, into a new typed local staging schema and private `recompute.dump`; retain the original `affected.dump` unchanged. Record both archive digests, before/after derived digests/counts and the resulting full postimage in the private manifest and in-DB capture audit. This captures exact PKs/preimages, without time-window guesses. Restore verifies both archives and the full current captured postimage, then reverses exact PK deltas to the original preimages. Any later activity or incomplete/malformed worker output still refuses rollback; no claim of general rollback after live use.

A safe local restore uses the typed backup archive, verifies its digest/schema and preimage/postimage manifests, locks source tables again, and reverses only exact modified rows. Preserve all original source IDs/payloads. Restore attempt ownership/numbers without deleting attempts (their FK cascades to saved answers); restore losers and derived preimages explicitly in dependency order. Suspend only each exact named immutable trigger around its one exact-ID statement, restore immediately; audit triggers remain active and a new rollback audit records the operation. Do not erase old or merge audit records. Refuse any collision/out-of-scope relation or later activity. No whole-table restore, cascading deletes, RLS bypass changes or session_replication_role.

Before FG-7a require executable proof of archive restore, every collision loser, original attempt numbering, exact derived preimages, source payload/timestamp conservation, injected failure rollback and refusal after later activity/recompute. No hosted restore command is released until this proof passes. If exact restore cannot be delivered within this bounded script, stop with that concrete limitation.

## Worker recomputation limits

After approved apply Fred can invoke the existing worker handler with institution scope through a separately reviewed hosted gate, or wait for the scheduled run. The normal handler orders reconcileMastery before readinessSnapshot; use existing jobs, never grading/review functions. No AWS command is executed by this lane. Reconcile only upserts, so delete only legacy derived rows and block stale canonical keys absent combined evidence before apply. It caps each institution at 50,000 evidence rows without pagination: stop if completeness cannot be proved below that cap. Match supported tracer K before replay and record equal-timestamp ordering limits. Readiness rebuild creates a new current snapshot, not replacement historical values. Count rebuilt skill pairs and current snapshots; no raw IDs or learning payloads enter gate output.

## Local proof and release checklist

Dedicated Docker Supabase Postgres fixtures replay all 0001–0037 migrations; the initial catalog proof publishes no port, and the full CLI proof uses a random loopback-only port; synthetic auth/storage SQL scaffolding is identified explicitly and is not a complete Supabase service/RLS proof. Record actual server/image versions. Capture the full constraint/unique-index/trigger catalog and migration hashes.

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

## Reviewable maintainer procedure — no hosted release yet

Python 3.10+ is required. Local proof uses repo uv Python 3.13.14, PostgreSQL clients 17.10 and Supabase Postgres 17.6. No Python dependency changes. Run the commands below from repository root; uv changes into services/api, so paths passed to Python use the corresponding ../../ prefix. The CLI accepts the reviewed source service directly; Fred must not edit code or supply a bypass flag. Agents never execute hosted services.

1. Coordinator reviews this source, local proof, counts format and rollback, then supplies the final SHA and exact FG-7a/7b steps. Fred confirms the deployed worker revision/effective tracer_k, source PostgreSQL major/encoding and compatible local clients/staging. Confirm backups have disk space and all learner writes/jobs are quiesced in the approved maintenance procedure. No schema/infrastructure changes are authorized here.
2. Fred creates gitignored `tmp/wi24-pairs.json`, mode 0600, containing a list of objects with exactly `institution_id`, `canonical_id`, `legacy_id`, `lms_uuid`, `lti_sub`, `course_ids`. UUID/sub equality must come from independently validated LMS mapping; never infer it from profiles. No real values enter chat/commits. Both identity profiles stay unchanged, including a legacy-only profile; they are retained metadata, not active learner ownership.
Input template (replace placeholders privately; no extra actor/profile fields):

```json
[
  {
    "institution_id": "<institution UUID>",
    "canonical_id": "<canonical users UUID>",
    "legacy_id": "<legacy users UUID>",
    "lms_uuid": "<proved LMS UUID>",
    "lti_sub": "<same validated launch subject>",
    "course_ids": ["<approved course UUID>"]
  }
]
```

The input is limited to one institution per batch. Fred's human attribution belongs in the gate record, alongside the in-DB session_user attribution.

3. Fred privately configures source, local backup and fresh local restore libpq services/passfiles. Service/passfiles must not be printed. Backup service permits host 127.0.0.1 or ::1, explicit numeric port, simple dbname, and the minimal option whitelist in the script. Local staging/restore databases must differ from source and be empty of wi24_* schemas. Inherited PG settings are discarded except service/passfile locations. Audit records the database session principal as who; Fred's named gate record supplies the human operator attribution.
4. FG-7a: run dry run into a fresh ignored private directory; paste only its counts/reason output. Any blocked pair stops the entire apply; no partial repair or key rewriting. Coordinator reviews actual counts before FG-7b.

```sh
uv run --directory services/api --no-sync python ../../scripts/repair_identity_split.py --input ../../tmp/wi24-pairs.json --source-service wi24_source --private-directory ../../tmp/wi24-dry # local only, not retained
```

5. FG-7b after explicit review: use a new directory. The K below is an illustrative argument placeholder; Fred supplies the **confirmed deployed value**, in supported range 0 < K <= 1, never a guessed default. Binary copies, typed staging and affected.dump finish before source mutations. All source mutations/audits are one transaction. If the command fails, source rolls back; retain private artifacts and stop for review. Do not manually rerun SQL fragments.

```sh
uv run --directory services/api --no-sync python ../../scripts/repair_identity_split.py --input ../../tmp/wi24-pairs.json --source-service wi24_source --backup-service wi24_backup --private-directory ../../tmp/wi24-preapply --apply --confirm --worker-tracer-k CONFIRMED_K --confirm-worker-config # local only, not retained
```

6. Review counts: timestamp_mismatches=0, legacy_learner_rows=0, triggers_restored=true. affected.dump, all binary copies and manifest remain private 0600 under a 0700 directory. Audit contains both IDs, original LMS key, database actor/time/counts and backup digest. Retain unchanged original affected.dump. A no-op rerun uses a fresh private directory; it performs no source writes and adds no merge audit.
7. Fred triggers the existing reconcile_mastery then readiness_snapshot jobs using the coordinator's separately reviewed hosted procedure, once while writes remain quiesced. Do not call review/grading functions or run a numerical merge. Then capture exact post-worker rows using the same K, same input, original private directory and local staging service. Capture verifies complete evidence counts/keys, exact replay estimates, old readiness preservation and one new eligible readiness row per course; it rejects truncation or additional worker runs. Only mastery/readiness are allowed to differ from the immediate post-apply image.

```sh
uv run --directory services/api --no-sync python ../../scripts/repair_identity_split.py --input ../../tmp/wi24-pairs.json --source-service wi24_source --backup-service wi24_backup --private-directory ../../tmp/wi24-preapply --apply --confirm --capture-recompute --worker-tracer-k CONFIRMED_K --confirm-worker-config # local only, not retained
```

8. Counts must report recompute_captured=true, estimate_mismatches=0 and k_confirmed=true, plus verified skill-pair/mastery/readiness counts. The additional recompute.dump stores exact current derived PKs/preimages; both archive hashes are recorded privately and in DB. No raw payload, identifier or archive is pasted. A failed capture makes rollback unverified until its exact reason is resolved; do not resume learner writes or claim FG-7b passed.
9. If rollback is required, use the original input/backup directory and a fresh local restore database service. The script verifies both archives, exact captured postimage and in-DB audit linkage, restores only exact PK deltas, preserves old/merge audits and appends rollback audit. It never deletes attempts/source/user anchors or cascades. Before recompute it restores directly from the immediate postimage; after recompute capture is mandatory. Later activity refuses restore. On any rollback failure source rolls back; retain artifacts and stop. Retrying uses a fresh **local** restore database; never reset source.

```sh
uv run --directory services/api --no-sync python ../../scripts/repair_identity_split.py --input ../../tmp/wi24-pairs.json --source-service wi24_source --backup-service wi24_restore --private-directory ../../tmp/wi24-preapply --apply --confirm --restore # local only, not retained
```

10. Keep maintenance quiescence until post-check/capture or rollback completes. Coordinator releases views and runs the separate FG-9 acceptance; WI-24 stays open until FG-7b plus FG-9. Later use deliberately invalidates exact rollback. No automatic rollback after later learner activity is claimed.

## Governance reach amendment

Canonical-only consent is a stop condition, not evidence that legacy consent transfers. The local counterexample uses the real has_consent/research_evidence_anon logic: zero visible legacy rows before attribution can become visible under canonical consent. Consent and DSR rows on either anchor therefore refuse a non-converged transaction, before writes; a converged no-op remains allowed. No consent/view/policy is changed.

Later-activity audit guards include exact actor/row and old_data/new_data identity references, so service-role consent/DSR changes remain detectable even after their live rows are removed. Source rollback preserves newly appended maintenance audits, while independently proving the entire original scoped audit prefix unchanged. It never removes audit history to force preimage equality.

## Valid governance-refusal outcome

Fred confirms refusal is a valid FG-7 outcome. For a non-converged pair, a safe no-record case has no consent or DSR rows on either anchor; it may proceed only if every other guard passes. A governance-state case has records on either anchor and remains conservatively refused, even if the records appear to match: this tool does not establish transferable legal scope. Mismatched state must never be reconciled by changing consent records, research policies or views.

The public governance-refusal output contains only affected pair labels, counts and the exact phrase, for example:

```text
pair 1 refused: governance ambiguity consent_count=1 dsr_count=0
```

No table plans, IDs, state values, names, content or additional generic error are printed for this outcome. Exit 2 is the expected safe refusal, with the entire source transaction rolled back before writes. Coordinator records the actual pair-label/count outcome in WI-24 without describing that pair as repaired; no real pair is assumed by local proof. Already-converged no-op performs no attribution change and remains allowed. A refusal does not authorize changing legal data or policies to force a merge.
