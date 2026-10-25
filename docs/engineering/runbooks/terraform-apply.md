---
runbook: terraform-apply
applies_to: [dev-hosted, prod]
who_runs_it: Named AWS / ITO infrastructure maintainer
time_needed: "[Fred to confirm]"
last_verified: "unverified; source review at 4f3ec29 on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 06 — bootstrap and apply the AWS stack

## When to use it

Provision a fresh approved environment from committed Terraform. WI-07 draft of human steps only; agents perform no infrastructure mutation. Routine code redeployment uses [07](deploy-backend.md).

## Before you start

- Resolve [01](aws-account-bootstrap.md)'s identity, state and concurrency gates. Select the reviewed revision; the named infrastructure owner approves the concrete plan.
- Obtain Docker, AWS CLI and Terraform through reviewed setup. Confirm profile/account/region privately.
- Prepare non-secret inputs from the committed [example](../../../infra/terraform/terraform.tfvars.example). SPA origin, state/backend init parameters, bootstrap image inputs and plan approver: [Fred to confirm]. Never store application secrets in Terraform.
- Check which resources already exist in state. Fixed names do not independently isolate parallel environments in the same account/region.

## Steps

1. Review [Terraform sources](../../../infra/terraform/) and the approved state procedure. The human runs `pnpm terraform -chdir=infra/terraform init` only after backend/state inputs are approved. Check account/region/state; no import or state migration without review.
2. Resolve the image/secret cycle in a fresh environment. The README targets ECR first; secret population must also precede invocation. Proposed bootstrap plan for owner review:

   ```sh
   pnpm terraform -chdir=infra/terraform plan -target=aws_ecr_repository.api -target=aws_ecr_repository.worker -target=aws_secretsmanager_secret.app
   ```

   Not run by Lane R. Required provisional image input values and their validation: [Fred to confirm]. After plan approval the human executes the matching targeted apply. Targeting is a bootstrap exception. Check repositories and empty secret exist in state, with no invocation yet.
3. Populate configuration privately using [05](secrets-manager.md). Resolve provisional registration fields before invocation. Confirm a valid secret value exists; do not create a secret version through Terraform.
4. From repository root the human runs `make push` with approved CLI/profile/account/region. It logs into ECR using password stdin, builds both images with `linux/amd64 --provenance=false --sbom=false` and pushes `latest`. Record immutable digests privately and associate them with the reviewed source. Agents never execute this external write.
5. Set approved image URIs and run `pnpm terraform -chdir=infra/terraform plan`. Review actions, IAM, CORS, secret reference, schedule and quota. Source declares API 30s/1024 MB, worker 120s/1024 MB, default schedule 15 minutes, async worker retries zero and 30-day Lambda log retention. These are declarations, not live evidence.
6. Stop on unexpected replacement/destruction or quota failure. The human applies only the approved concrete plan. Exact saved-plan handoff procedure: [Fred to confirm]. Partial failure means partial deployment, not permission to reset state or destroy resources.
7. Check API `live`, Gateway's alias integration, worker update and Scheduler target. Check provisioned concurrency reports `READY` if allocated. Scheduler can write hosted data as soon as active: confirm database/config readiness before apply. Exact first-run/disable procedure if not ready: [Fred to confirm]. Record only endpoint hosts and outcomes publicly; identifiers stay private.
8. Finish [04](anthology-developer-app.md)/[08](lti-tool-registration.md), [09](vercel-web.md) and [10](first-launch-smoke.md). Apply success and container health do not prove LMS integration.

## Verify it worked

Record maintainer, revision, environment/date, reviewed plan/apply results, image references privately and status-only `/health`. Verify alarm/budget delivery separately: the error alarm has no notification action in source. Current quota, notifications and fresh-account acceptance: [Fred to confirm].

## Undo / roll back

Preserve state and sanitized failure details. Inspect partial resources and prepare a new reviewed plan. No automatic destroy, hand-deletion or state editing. For application image recovery use 07 after compatibility review. Infrastructure recovery rehearsal: [Fred to confirm].

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Image missing at Lambda creation | Bootstrap order | Complete repository/image phase and verify digest. |
| Missing settings | Empty/unreadable secret or precedence | Follow 05 before invocation. |
| Concurrency allocation fails | Regional quota | Account owner resolves; do not silently remove the resource. |
| Drift after `make deploy` | Out-of-band alias/image changes | Reconcile intended version/digest in a reviewed plan. |

## Sources

[Terraform README](../../../infra/terraform/README.md), [Makefile](../../../Makefile), bootstrap lessons and deployment evidence. No fresh-account execution was performed by Lane R.

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-25 | Draft phased bootstrap and apply gates | APPROVAL-05 rev 2, Lane R, WI-07. |

## Historical sources

These links preserve provenance only. Required rules, commands and limits are stated above; do not read the records unless the task explicitly names them.

- [deployment evidence](../../work/handover-2026/evidence/deployment-2026-10-25.md)
- [bootstrap lessons](../../work/handover-2026/evidence/recap-knowledge.md)
