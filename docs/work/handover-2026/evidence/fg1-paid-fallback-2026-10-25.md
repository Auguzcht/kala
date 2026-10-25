# FG-1 paid fallback configuration update

Verified at 2026-10-25T08:01:15.818640+08:00 (Asia/Manila). Source base:bff389a7cf511d83d66905da9f9df12eb218c8ee. Authority: Fred's explicit CLI delegation, recorded in [APPROVAL-06](../approval-06.md#confirmed-fg-1-cli-delegation--2026-10-25).

## Result

Added OPENROUTER_MODEL_CHAT_FALLBACK=nex-agi/nex-n2.5-mini to the existing kala/app secret in ap-southeast-1. The setting previously was absent, so the application used its free fallback default. Bundle size changed from25 to26 entries. Candidate/current/previous readbacks prove all25 existing entries unchanged. No credential was rotated and no source default was changed. Live and latest API configurations reference this secret and do not override the fallback setting in their Lambda environment.

The previous secret version is retained with AWSPREVIOUS. Version identifiers and the exact rollback mapping are private in gitignored .tmp/fg1-fallback-update.json, mode0600. No secret payload or credential value is retained in that record or in Git.

## Method and verification

Terraform source infra/terraform/secrets.tf manages only the secret container, explicitly leaving secret contents out of Terraform state. This update used the workspace AWS CLI1.46.1, not Terraform or direct KMS calls. Secrets Manager handles [KMS-backed encryption](https://docs.aws.amazon.com/secretsmanager/latest/userguide/security-encryption.html).

The implementation created one new version under a unique temporary staging label with put-secret-value, validated its parsed JSON, then moved AWSCURRENT conditionally from the recorded previous version using update-secret-version-stage. A concurrent change to the expected current version would reject promotion rather than overwrite it. It then read back AWSCURRENT and the retained previous version, compared the complete parsed objects, and removed the temporary label. See [AWS version update semantics](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/update-secret-version-stage.html).

CLI v1 consumed stdin differently than expected; the first parser attempt failed before any remote version was created. A local FIFO parser probe also timed out. Successful transport used a mode0600 temporary JSON input file inside a private temporary directory, deleted immediately after the CLI call (including error cleanup). No secret value was placed in shell arguments/output, history, chat, committed files or Terraform state. Errors were reported only as operation/code; no secret-containing CLI input/error body was emitted. Candidate existence was checked before retrying, reusing the recorded idempotency token rather than blindly creating another version. The temporary payload was confirmed removed; only the non-secret rollback metadata remains locally.

Verification results:

- Intended runtime secret matches target: true.
- Lambda fallback environment override: absent.
- New paid fallback readback: true.
- Other existing entries unchanged: true (25/25).
- Previous version retained: true.
- Temporary staging label removed: true.
- Temporary payload file removed: true.
- Runtime refresh performed: false; no Lambda/config/image/alias update was made.

## Remaining release steps

Fred's make deploy creates fresh API/worker execution environments; the settings loaders read this updated secret when initializing. Existing warm settings remain cached until replaced. Live hint, Explain and Tutor acceptance remain pending; a stored setting is not a successful model response. No paid model completion was requested by this operation.

0037 post-checks already pass; Fred confirms historical migration-tracking gaps do not block the deployment. Preserve that finding in the database stream; do not repair/replay history during this release.

Recovery: a reviewed rollback can move AWSCURRENT back to the previous version recorded privately, then refresh affected runtimes. No rollback was executed. Preserve unrelated future edits when choosing a later rollback strategy; do not restore an older whole bundle blindly after other changes.

## AUDIT REPORT

```text
Task / brief ID: FG-1 narrow AWS CLI delegation, paid chat fallback
Branch and worktree: main; /Users/fred/Documents/Repository/kala
Base revision:bff389a7cf511d83d66905da9f9df12eb218c8ee
Files changed: approval amendment and release evidence only
REQ / WI IDs touched: AI-REQ-002; TUTOR-REQ-001; WI-01; FG-1
Commands run and results: source ownership/precedence review; AWS CLI
  get-secret-value, put-secret-value, update-secret-version-stage;
  candidate/current/previous JSON comparisons all pass,25/25 retained.
Spec changes made: none; approved paid fallback policy applied
Evidence added: this report and private rollback-version metadata
Anything not done, and why: no Terraform/KMS-resource change, credential
  rotation, browser use, deployment, push or live model smoke test;
  fresh runtime and acceptance remain Fred's steps
Risks or questions for planner: cached warm settings need replacement;
  no successful live answer claimed; history gap remains DB-stream work
Secrets printed: none (confirmed)
```
