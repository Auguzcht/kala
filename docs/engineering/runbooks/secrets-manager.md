---
runbook: secrets-manager
applies_to: [dev-hosted, prod]
who_runs_it: AWS secret custodian and API / worker maintainer
time_needed: "[Fred to confirm]"
last_verified: "unverified; source review at 4f3ec29 on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 05 — populate runtime configuration

## When to use it

Prepare the backend bundle before first invocation or make an approved configuration update. WI-07 draft; only a named human custodian writes hosted values. [secrets.md](../secrets.md) remains the sole names/stores/owners inventory. No payload example is included here.

## Before you start

Have [01](aws-account-bootstrap.md)'s approved identity/state, [02](02-database-setup.md)'s project, [03](blackboard-learn-instance.md)/[04](anthology-developer-app.md)'s platform/app outputs and provider billing/key custody. Some LTI fields arrive after 06/08; defer invocation until configuration is complete. Payload membership, custodian and recovery policy: [Fred to confirm].

## Steps

1. Review the catalogue with both service owners. Select settings for this environment/provider; the old Terraform README's reduced JSON is not the full catalogue. Shared evidence reports presence and endpoint hosts only.
2. Create the empty secret through [06](terraform-apply.md)'s reviewed bootstrap phase. Source names it `kala/app`; environment-scoped naming is proposed, not implemented. Confirm account/region privately; do not create a duplicate under a guessed name.
3. In Secrets Manager, select the reviewed secret and use the value-editing flow to store approved JSON privately. Current console labels, validation and secure preparation/transport: [Fred to confirm]. No values in Terraform inputs/state, command arguments, chat, screenshots or commits. Do not read/reuse historical `secrets.json` files.
4. Check precedence privately. [API](../../../services/api/app/config.py) and [worker](../../../services/worker/app/config.py) loaders use `os.environ.setdefault` and cached settings. Lambda environment wins. [lambda.tf](../../../infra/terraform/lambda.tf) declares `FRONTEND_URL` and `WORKER_FUNCTION_ARN` for API, and `WORKER_FUNCTION_ARN` for worker. Editing matching secret entries cannot change those effective values; Terraform-owned changes require infrastructure review.
5. Verify `KALA_SECRETS_ARN`, secret-read permission and regional match without printing payload/environment output. An empty secret container is not readiness. The loader catches failures and warns, so startup alone does not prove complete settings.
6. Follow [07](deploy-backend.md) or a separately reviewed configuration-refresh procedure so both consumers initialize with the new value. Warm settings are cached; a new secret version alone proves no refresh. Exact refresh mechanism/version mapping for both consumers: [Fred to confirm]. Do not invoke the worker just to test loading: it writes data.
7. Finish 08 and [10](first-launch-smoke.md) with the human tester. Record the secret-version mapping privately and presence/refresh/smoke outcomes in shared evidence, never the payload.

## Verify it worked

Both consumers initialize with required settings, no loading warning occurs for tested initialization, and synthetic launch/tutor/ingest checks succeed. Verify provider selection rather than inferring defaults. Presence checks alone do not establish key validity/billing. No hosted configuration was read or written by Lane R.

## Undo / roll back

The custodian may restore a previously approved version only if its credentials remain valid and uncompromised, then repeat the reviewed refresh. Never revive revoked/exposed keys to pass smoke. Exact version-label reversal and coordinated refresh: [Fred to confirm]. See [11](key-rotation.md).

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Edit has no effect | Environment shadowing or cached settings | Compare names privately and validate refresh. |
| Secret-loading warning | Reference/region, permission or payload problem | Custodian checks privately; share no raw warning remainder. |
| Provider 401/403/402 after startup | Key, entitlement or billing | Provider owner checks privately; follow 12. |

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-25 | Draft population, precedence and refresh checks | APPROVAL-05 rev 2, Lane R, WI-07. |
