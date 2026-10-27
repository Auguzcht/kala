# FG-6 acceptance and FG-8 delegation — 2026-10-27

Operator/acceptance owner: Fred. Reviewed application source: `616dfc66f572132378f1c080761ecf661de04262`. Fred applied 0038/0039 and ran `make deploy`; Codex performed the previously delegated read-only post-checks. **Fred accepts FG-6 on 2026-10-27 with the grant-drift finding below.** This supersedes the earlier pending-sign-off observation without claiming that hosted role acceptance has run.

## Hosted results accepted by Fred

| Check | Verified result |
| --- | --- |
| 0038 | All 22 changed policies across 20 tables exactly match the reviewed local replay; affected-table RLS enabled |
| Complete public policy catalogue | All 36 public policies match, including those 22; 36 is the total, not 36 additional policies |
| Application SQL functions/helpers | All 20 match the repository replay |
| RLS/exposure | All 36 ordinary public tables have RLS enabled; no anon/public policies |
| 0039 | Exact `(user_id, course_id, created_at DESC, id DESC)` index definition; `indisvalid=true`, `indisready=true` |
| Hosted PostgreSQL | 17.6; post-check queries ran in a read-only transaction |

Accepted file checksums:

- 0038: `aef2053f98368d691bb2735ec6ffbeafc603426b10eef6b24b516f076ad83485`
- 0039: `d0e727d0ce33eecd12fcbb8a169e7efcb2a649943e925a0434af4f7511a20f95`

## Accepted finding — Lane DB drift check, owner ITO

SELECT grants differ from the local replay on 14 tables: anon SELECT on generated_items, guided_lesson_steps, guided_lessons, ingest_jobs, item_exposures, item_reviews, lms_identity_aliases, quiz_set_attempts, quiz_set_items, quiz_sets, srs_state, tutor_attachments, tutor_conversations and tutor_messages; authenticated SELECT also differs on ingest_jobs.

Fred accepts this as **pre-existing** drift. At least the tutor_conversations difference is recorded before 0038, and 0038 contains ALTER POLICY statements only. The likely cause is manual application of 0001–0036 together with Supabase default grants; this is a hypothesis, not a verified reconstruction of every grant's origin. The complete pre-0038 hosted snapshot is unavailable. RLS is enabled everywhere inspected, and no anon/public policy grants row access. No grants are changed now.

Assign inventory, attribution and any proposed remediation to **Lane DB / WI-04, owner ITO**. Existing drift-inspection and human-change gates remain. This acceptance does not authorize grant edits, history reconciliation or a new hosted inspection. Hosted authenticated-role acceptance moves explicitly to **FG-9**: live LTI sessions, cross-course refusal and non-enrolled student 404s. WI-24/25/26 stay open for their remaining human outcomes.

The sanitized receipt `.tmp/fg6-postchecks-2026-10-27.json` stays **local only, not retained**. It and the private comparison catalogue are not committed. Local policy proof first hit a database startup transition; after stable health the unchanged committed verifier passed. The agent removed only its disposable comparison container.

## FG-8 backend — verified complete

- API alias `live` points to version **8**, with no weighted routing; API Active / Successful.
- Worker Active / Successful.
- API digest: `sha256:050a862de5c55f47a24296ca9acc921c24aeb2fdd3761b7826c88accba048aa0`.
- Worker digest: `sha256:7d9b199a7ca0326cc3a07fab0f890d557d92842596fe6b00fcb9f7ffa6650f1b`.
- Both resolved digests match the local ECR-tagged images. Their tracked application files and requirements match reviewed source `616dfc66`.
- API Gateway targets the `live` alias; public `/health` returned **200**.

These checks establish backend deployment identity/update completion, not worker-job completion, provider answers or live LTI acceptance.

## FG-8 frontend — one narrowly delegated publication

Fred delegates exactly one docs-only commit on main, a fast-forward push and read-only Vercel/GitHub status checks. Application source must stay identical to `616dfc66`. Fetch/check the existing origin/main reference; stop if it moved, main is behind, any non-docs diff exists, docs checks fail, another credential is needed or Vercel requires a redeploy/settings change. Never pull/rebase main or force-push.

Publication attribution on success: **pushed by Codex, delegated by Fred**. At this pre-push documentation commit, push and production Ready are pending. The final coordinator response records the actual pushed SHA, deployment state and production URL host after read-only verification. No second documentation commit is delegated to backfill a deployment outcome. A Git push alone is not Vercel readiness.

No hosted SQL, grant/data/secret/config edits, Lambda/alias changes, repair execution or Vercel settings changes are delegated by this instruction.

## FG-7a prepared for Fred — not executed

Source: `docs/runbooks/identity-repair.md` and static review of `scripts/repair_identity_split.py`. Run from the repository root only when Fred chooses to perform FG-7a:

```sh
uv run --directory services/api --no-sync python ../../scripts/repair_identity_split.py   --input ../../tmp/wi24-pairs.json   --source-service wi24_source   --private-directory ../../tmp/wi24-dry # local only, not retained
```

The command has no apply/confirm flags. Environment names only: **PGSERVICEFILE**, **PGPASSFILE**, and **PATH** for the PostgreSQL client. Explicit service/passfile locations are optional if Fred already uses libpq's private defaults. The script clears other inherited PG settings and sets PYTHON_DOTENV_DISABLED itself; no application dotenv, AWS or Supabase API credential is required by this CLI. Source credentials stay in Fred's private libpq service/passfile, never argv or chat. Do not request connection strings.

Fred prepares a mode-0600, gitignored input with independently proved institution, canonical/legacy user anchors, equal validated LMS UUID/LTI sub and approved courses. Exact object keys: institution_id, canonical_id, legacy_id, lms_uuid, lti_sub, course_ids; one institution and at most20 pairs per batch. The output parent must exist; the dry-run directory must be fresh, ignored, non-symlinked and private (created 0700). Python 3.10+ and an available `psql` are required. The fixed source-service name is `wi24_source`, not a connection string. Keep pair values and private files out of the report.

Expected output shape, **illustrative placeholders, not actual counts**:

```text
pair 1 evidence_events move=N delete=0 retained_metadata=0 collisions=0 rule=reattribute
pair 1 converged=false
dry_run=true source_writes=0
```

Other table lines use the same move/delete/retained_metadata/collisions/rule fields. Already-converged input ends with `converged=true source_writes=0`. Ordinary blockers include `pair 1 blocked_count=N reason=REASON` and `blocked=true reason=BLOCKED_PAIR`, exit 2. Governance ambiguity prints only pair label and counts, then exits 2:

```text
pair 1 refused: governance ambiguity consent_count=N dsr_count=N
```

Consent or DSR records on either anchor of a non-converged pair refuse attribution, even if their states appear equal. A refusal is a valid FG-7 outcome, never permission to change governance records, research views or policies. Fred sends only real counts/reasons to the planner before any apply.

There is no separate backup-only CLI mode: a later reviewed apply requires the local backup service, and its backup phase completes before persistent source mutation. Before a separately approved FG-7b apply, Fred must establish maintenance quiescence, confirm deployed worker revision/effective tracer K and compatible PostgreSQL clients/major/encoding, and configure an empty **loopback-only local backup** service. The script locks and revalidates source scope, makes exact binary copies of both sides (including collision losers/attempt numbers/derived preimages), loads typed local staging, writes private `affected.dump` and a hashed manifest, and verifies preimages **before the first persistent source mutation**. Files are 0600 under 0700 directories. Backup failure rolls back before source writes. Preserve the original archive for exact restore; subsequent worker recomputation requires its separately reviewed capture. No backup/apply/capture/restore command is run or newly delegated here.

Refuse invalid/private-file or service configuration, schema/trigger drift, missing/unproved/ambiguous identities, cross-institution or out-of-scope relations, conflicting roles/aliases/tombstones, unequal profiles, legacy attachments, governance records, source idempotency/session collisions, invalid/multiple unfinished attempts or numbering overflow, unproved exposure collisions, stale canonical mastery without evidence, or equal-time conflicting worker evidence. Timeouts, database/backup failures and unsafe/stale restore state also refuse; never force a merge or loosen guards.


## Approved command reflow proof

Fred approved this formatting correction after the marker gate stopped publication. The original drafted command is transcribed line by line below; this is a historical transcription, not an executable listing. The executable command remains in its original shell fence above. Only continuation backslashes and line breaks were removed; indentation spaces were preserved, and the final shell comment was appended. The checker and tests were not edited.

| Line | Original drafted text, verbatim | Retention |
| --- | --- | --- |
| 1 | `uv run --directory services/api --no-sync python ../../scripts/repair_identity_split.py \` |  |
| 2 | `  --input ../../tmp/wi24-pairs.json \` | # local only, not retained |
| 3 | `  --source-service wi24_source \` |  |
| 4 | `  --private-directory ../../tmp/wi24-dry` | # local only, not retained |

After POSIX backslash-newline removal, shell tokenization (comments ignored) yields the following exact comparison. All13 tokens are identical in value and order; no flag, argument or path changed.

| Position | Drafted token | One-line token | Equal / retention |
| --- | --- | --- | --- |
| 1 | `uv` | `uv` | yes |
| 2 | `run` | `run` | yes |
| 3 | `--directory` | `--directory` | yes |
| 4 | `services/api` | `services/api` | yes |
| 5 | `--no-sync` | `--no-sync` | yes |
| 6 | `python` | `python` | yes |
| 7 | `../../scripts/repair_identity_split.py` | `../../scripts/repair_identity_split.py` | yes |
| 8 | `--input` | `--input` | yes |
| 9 | `../../tmp/wi24-pairs.json` | `../../tmp/wi24-pairs.json` | yes; local only, not retained |
| 10 | `--source-service` | `--source-service` | yes |
| 11 | `wi24_source` | `wi24_source` | yes |
| 12 | `--private-directory` | `--private-directory` | yes |
| 13 | `../../tmp/wi24-dry` | `../../tmp/wi24-dry` | yes; local only, not retained |

Both private paths were confirmed ignored with git check-ignore and untracked. The repair command was not executed.

## Audit report at documentation preparation

```text
AUDIT REPORT
Task / brief ID: Fred's FG-6 acceptance / FG-8 frontend delegation; FG-7a preparation
Branch and worktree: main; primary repository (local only, not retained)
Base revision: 616dfc66f572132378f1c080761ecf661de04262
Files changed: docs/** only; exact commit manifest is the review boundary
REQ / WI IDs touched: WI-04/24/25/26; AUTH/INSTR/TWIN gate records only
Commands run and results: docs checker0 violations; unit tests18 passed;
  both private paths ignored/untracked; all13 shell tokens identical;
  application/checker/tests/ignore files unchanged. Final publication and
  production results are reported after execution in the coordinator response.
Spec changes made: none; operational acceptance/ownership/preparation only.
Evidence added: this acceptance record; private receipt not committed.
Anything not done: push/Ready pending at this commit; FG-7a not run;
  FG-7b/9, hosted changes and settings changes not delegated.
Risks or questions for the planner: pre-existing grant finding assigned
  to ITO; role acceptance remains FG-9; origin movement/build failure stops.
Secrets printed: none (confirmed).
```
