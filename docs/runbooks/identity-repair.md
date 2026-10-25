# Dev identity history repair — WI-24 design

Status: design blocked; **not executable and not released for FG-7a**. No repair script exists yet. This is a one-time, maintainer-run repair of explicitly proved dev identities. Production and hosted execution remain Fred gates. No feature behavior is changed.

Read [database policy](../engineering/database.md), [AUTH contract](../features/lti-auth/README.md), [Twin contract](../features/twin/README.md), [gamification contract](../features/gamification/README.md) and [WI-24](../work/handover-2026/work-items/WI-24-dev-identity-history-repair.md). All 0001–0037 migrations are immutable.

## Decisions required before implementation

1. `item_reviews` has UNIQUE `(user_id,idempotency_key)` and a partial UNIQUE `(user_id,item_id,session_id) WHERE counted AND session_id IS NOT NULL` (0027). `practice_answer_results` has UNIQUE `(user_id,idempotency_key)` (0032). Two source rows can be distinct history yet collide after attribution. Deleting either loses source history; changing counted/XP/outcome changes learning history; rewriting keys changes replay semantics. **Stop the entire pair before any mutation if either collision occurs.** Proposed bounded alternative: support only proved collision-free pairs; report collision counts and leave other pairs blocked. A generic key/session rewrite requires separate approval and a replay-semantic design. Exact duplicate payloads are still two source records and are not silently deduplicated.
2. Redirecting all legacy aliases conflicts with keeping its exact LMS identifier unchanged. `resolve_user` at `services/api/app/db/supabase.py` rejects an alias when an exact users row for that identifier points elsewhere. Proposed alternatives: explicitly retain the legacy identifier solely as a retired, never-resolved identifier (and document the error); or approve tombstoning `users.lms_user_id` to a deterministic reserved repair marker while preserving the original in the in-DB merge audit and backup. Neither is assumed authorized. Current AUTH-REQ-006 says established conflicting aliases are not reassigned; coordinator must explicitly reconcile its historical-repair wording before implementation.
3. Historical actor/governance references must not be rewritten as though the canonical identity originally performed them. Proposed exception to an entirely empty shell: retain historical `audit_log.actor_id`, audit JSON/row identifiers, `researcher_grants.granted_by`, `skills.reviewed_by` and `recommendations.decided_by`; insert a merge linkage audit record. If an empty shell means zero historical actor references too, stop for a provenance-preserving decision. Never update old audit payloads.
4. Supabase Storage object names embed the old user ID (0011). Moving attachment DB ownership leaves raw object-folder RLS associated with the old ID; moving object bytes/names cannot be atomic with this Postgres transaction. Proposed bounded alternative: block any pair with attachments pending an approved storage procedure, or explicitly accept retained immutable paths accessed through the existing owner-checked API. Do not mutate storage.objects metadata to pretend bytes moved.

These are design findings, not observations of hosted data. No real pair IDs, launch subjects, credentials or content have been received. No hosted query is needed to choose the policy.

## Inventory and deterministic rules

The complete catalog of **all** public primary/unique/FK constraints, unique indexes (including predicates) and non-internal triggers is retained in the dedicated schema fixture after replay of all 37 migrations. The following table covers every user identity reference, including columns without FKs. Any new column, constraint, trigger or schema drift must stop the repair until reviewed.

| Table / columns | Keys, dependencies and rule |
| --- | --- |
| users.id, lms_user_id | PK id; UNIQUE institution/LMS ID; institution FK. Keep both user anchors; canonical chosen only from exact UUID/sub mapping. Legacy LMS-key disposition is decision 2. |
| lms_identity_aliases.user_id | PK institution/LMS ID; user and institution FKs. Redirect only aliases already belonging to the listed legacy user; third-user alias/exact-user conflicts stop. Preserve source/timestamps. |
| user_profiles.user_id | PK/FK user. Source PII, not derived. Do not overwrite/drop conflicting profile values. Stop on unequal dual profiles; bounded option requires approved preservation in private backup/audit. |
| enrollments.user_id | PK user/course; user/course/institution FKs. Same-role collision: retain canonical enrollment, remove duplicate enrollment; different role stops. Move unique enrollments; legacy ends unenrolled. Audit trigger remains active. |
| evidence_events.user_id | UUID PK; user/course/skill/institution FKs. Change only user_id for exact preselected legacy row IDs; preserve all payload/time/IDs. Under APPROVAL-07 Amendment 1, snapshot `(id,created_at)` for every selected row before mutation and require exact timestamp equality for every moved ID afterward; never replace created_at or introduce occurred_at. Cursor order is `(created_at DESC,id DESC)`. Suspend only t_immutable around that statement under exclusive table lock. |
| mastery_state.user_id | PK user/skill; user/course/skill/institution FKs. Invalidate both users' derived rows in affected courses, including stale canonical skills without evidence; no numerical merge. Reconcile worker rebuilds canonical state. |
| readiness_snapshots.user_id | UUID PK; user/course/institution FKs. Derived historical series: archive exact preimages, delete affected pair snapshots only under explicit derived-state rule. Existing job can create current snapshots; it cannot recreate historical time-series values. Full historical readiness preservation would instead require reattribution, a planner decision. |
| srs_state.user_id | PK user/item; user/course/item/skill/institution FKs. One schedule per card. Select entire row with greatest last_reviewed_at NULLS LAST, then created_at, then canonical side on ties; retain losing row in exact private backup. Do not sum box/reps/lapses. Move noncolliding rows. Card memory extensions 0026/0029/0030 are part of the selected whole row. |
| quiz_set_attempts.user_id | UUID PK; UNIQUE user/set/attempt_number after 0034; user/course/set/institution FKs. Keep canonical numbering; order legacy rows by old attempt_number, id, allocate sequentially after canonical max, then move. Refuse smallint overflow, malformed relations or multiple unfinished attempts in a set (no safe active-attempt rule). Keep IDs, counters, completion and timestamps. |
| practice_answer_results.user_id | UUID PK; UNIQUE user/idempotency key and attempt/item; attempt FK ON DELETE CASCADE, item FK. Do not delete attempts. Preserve attempt_id links, immutable answers, XP and keys. Reattribute only collision-free rows; stop for decision 1 otherwise. Trigger practice_answer_results_immutable needs narrowly scoped suspension, never all triggers. |
| item_reviews.user_id | UUID PK; UNIQUE user/key and partial user/item/session; item FK; user/institution/course/skill IDs have no FK. Validate manually. Preserve counted/outcome/session/key/time. Collisions stop; trigger t_immutable requires narrow suspension. |
| item_exposures.user_id | PK user/item; user/course/skill/item/institution FKs. Independent max studied/tested/answered timestamps; last_correct follows latest answered row (tie canonical); times_tested sum only for proved disjoint source attempts, otherwise stop. Preserve earliest created_at and latest updated_at; retain both preimages. |
| tutor_conversations.user_id | UUID PK; user/course/institution FKs. Move ownership only, preserve IDs, title, created/updated/pinned timestamps. |
| tutor_messages.conversation_id | No user column; UUID PK, conversation FK cascade. Preserve messages unchanged via unchanged conversation IDs. |
| tutor_attachments.user_id, storage_path | UUID PK; user/conversation/institution FKs. Preserve attachment metadata/content and conversation IDs. Storage boundary requires decision 4. |
| recommendations.user_id, decided_by | UUID PK; user/course/skill/institution and deciding-user FKs. Move learner target; preserve decisions/status/rationale/times. Historical actor disposition is decision 3. No user composite uniqueness. |
| consents.user_id | UUID PK; user/institution FKs. Historical legal consent, not ordinary derived state. Stop if any legacy rows: merging latest-wins consent can change research access. Separate explicit policy required. Audit trigger remains active. |
| data_subject_requests.user_id | UUID PK; user/institution FKs. Governance records: stop if legacy rows pending explicit legal identity decision. Audit trigger remains active. |
| lti_launches.user_id | UUID PK; user/institution FKs; t_immutable. Preserve launch provenance on legacy with merge linkage, or obtain explicit authorization for exact-row user-only reattribution. No assumption that launches are actually recorded by current routes. |
| researcher_grants.granted_by | UUID without user FK; researcher_id references separate researchers, not users. Historical actor: decision 3; retain original. Audit trigger remains active. |
| skills.reviewed_by | Text LMS ID, no user FK. Never guess or globally replace matching strings. Historical actor: decision 3. |
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

## Exact backup and rollback design — unreleased

`pg_dump` cannot filter rows with a WHERE clause. A table-filtered whole-table dump is not an exact affected-row backup, and blindly restoring it can collide with retained canonical rows. Do not advertise a nonexistent row-filter flag.

Proposed procedure for proof before FG-7a: under the same locks/snapshot used for apply, create a private staging schema with typed copies of **both sides' entire affected rows**, including losing schedule/exposure/enrollment rows, canonical preimages, original attempt numbers, all derived snapshots/state and indirect dependents that could cascade. Include exact PK lists, trigger states, schema/migration digest, operation ID and manifest counts. No generic cascading delete in rollback. Use a dedicated second local process to pg_dump just this staging schema after its backup transaction commits; keep the maintenance window and verify a new locked snapshot equals the backup manifest before apply. If any affected preimage changed, refuse apply and retake backup. Do not keep access-exclusive locks across an external dump process that needs the same tables.

Dump is mode 0600 on Fred's local disk, never committed/shared. Test restore into a separate throwaway DB first. If private staging objects on dev-hosted are disallowed, alternative is binary COPY to private local files followed by load into a local staging DB and pg_dump there; this needs an explicit reviewed transport and snapshot proof. Neither alternative is implemented or authorized merely by this design.

Rollback must quiesce writers and recompute, verify the post-apply affected rows equal the saved postimage manifest (stop if later activity changed anything), lock the same tables, restore canonical/legacy preimages and collision losers in dependency order, restore old attempt numbers, and restore derived rows after removing only the exact repair/recompute-generated derived rows named in a validated rollback manifest. Immutable rows need the same exact-ID single-statement trigger suspension and transactional restoration. Preserve original audits and append a rollback audit; do not erase the merge audit. Generated enrollment audit rows remain historical. Recompute jobs write outside the repair transaction: capture their exact derived PKs/preimages in the rollback manifest before accepting rollback readiness. A time-based guess or deleting all later snapshots is forbidden. Post-check byte-equivalent source/derived preimages and trigger states before commit. **No generic restore commands are supplied until this procedure has an executable local proof.** FG-7a stays blocked until exact backup/restore is implemented and tested.

## Worker recomputation limits

After approved apply Fred can invoke the existing worker handler with institution scope through a separately reviewed hosted gate, or wait for the scheduled run. The normal handler orders reconcileMastery before readinessSnapshot; use existing jobs, never grading/review functions. No AWS command is executed by this lane. Reconcile only upserts, so invalidating both canonical and legacy affected mastery rows avoids stale canonical rows absent from evidence. It caps each institution at 50,000 evidence rows without pagination: stop if completeness cannot be proved below that cap. Match supported tracer K before replay and record equal-timestamp ordering limits. Readiness rebuild creates a new current snapshot, not replacement historical values. Count rebuilt skill pairs and current snapshots; no raw IDs or learning payloads enter gate output.

## Local proof and release checklist

A dedicated Docker Supabase Postgres container/database with no published port replays all 0001–0037 migrations; synthetic auth/storage SQL scaffolding is identified explicitly and is not a complete Supabase service/RLS proof. Record actual server/image versions. Capture the full constraint/unique-index/trigger catalog and migration hashes.

After policy resolution, fixtures must exercise one-sided history, two-sided history with schedule/attempt collisions, source-key collisions (safe stop), conflicting aliases/profiles/roles, cross-tenant rows including unconstrained tables, append-only launches/reviews/results, attachments, source payload conservation and rewards. Prove dry-run immutability, apply, post-checks, no-op rerun, rollback of injected mid-transaction failure, trigger restoration, concurrent writer blocking, backup/restore including collision losers/renumbered attempts/derived recompute. No tests are evidence of unexecuted behavior.

Coordinator reviews design, proof and counts format before Fred gets FG-7a. FG-7b remains separate after real dry-run review. WI-24 stays open until real acceptance. No deployment, push, merge, hosted connection or cleanup of this worktree is authorized.

## Verified by

- [APPROVAL-07, section 3](../work/handover-2026/approval-07.md)
- [WI-24 inventory evidence](../work/handover-2026/evidence/wi24-identity-repair.md)
- [Local schema fixtures](../../scripts/tests/identity_repair/)
