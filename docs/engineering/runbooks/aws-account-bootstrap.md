---
runbook: aws-account-bootstrap
applies_to: [dev-hosted, prod]
who_runs_it: AWS account administrator / ITO
time_needed: "[Fred to confirm]"
last_verified: "unverified; source review at 4f3ec29 on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 01 — AWS account bootstrap

## When to use it

Prepare institutional AWS access, region, budget and Terraform state custody before provisioning Kala. WI-07 draft; every account/infrastructure action is maintainer-only.

## Before you start

Obtain sponsor/ITO approval for the account, billing owner and landing zone described in [environments](../environments.md) and [infrastructure requirements](../infrastructure-requirements.md). Credential custody is in [secrets.md](../secrets.md). Account/role names, budget recipient and state custodian: [Fred to confirm]. No personal credentials transfer to school production.

## Steps

1. ITO creates/selects the institution-owned account and establishes root recovery and MFA under its account policy. Use an approved administrative role for setup, with no long-lived root access keys. Exact identity-provider/role enrollment flow: [Fred to confirm]. Check authentication to the intended account and region privately.
2. Choose the target region in private environment inventory. Terraform defaults to `ap-southeast-1`; it must match repositories, Lambda, secret access and any Bedrock model availability. Region and model entitlement: [Fred to confirm].
3. Review [providers.tf](../../../infra/terraform/providers.tf): `assume_role_arn` supports an organization role; leaving it empty uses the caller's credentials. ITO verifies the final assumed identity before plan/apply. `make` discovers the caller account unless explicitly overridden; check the active profile.
4. Establish Terraform state ownership, encryption, access control, locking, backup and recovery. No remote backend is declared in committed Terraform. Actual state location and school backend design: [Fred to confirm]. **Stop before init/apply** until the administrator approves a state procedure. A new backend needs separately authorized infrastructure work; do not start an independent state against existing resources.
5. Confirm budget custody. [observability.tf](../../../infra/terraform/observability.tf) declares an optional USD 100 monthly budget with an 80% actual-spend notification when a recipient is configured. This is not a spending cap or verified bill. Approved amount, recipient and EC2/provider budgets: [Fred to confirm]. Runbook 06 applies only reviewed settings.
6. The administrator checks regional Lambda concurrency before 06. Source declares provisioned concurrency of one on `live`; archived MEMORY records an unresolved quota problem. Current quota, increase-request disposition and allocation state: [Fred to confirm]. Earlier deployment success does not establish this readiness.
7. Verify tooling versions/paths privately. Terraform >=1.6 and AWS provider constraints are in [versions.tf](../../../infra/terraform/versions.tf). Review root setup scripts first; `pnpm setup` installs tools and changes shell paths. Do not run it as a documentation check.

## Verify it worked

ITO signs off role, region, billing alerts, state recovery and quota readiness. Shared evidence contains verifier/date/environment and outcomes only; identifiers and credentials stay in approved stores. No live account check was performed by Lane R. Continue with [02](02-database-setup.md), [03](blackboard-learn-instance.md), [05](secrets-manager.md) and [06](terraform-apply.md).

## Undo / roll back

Revoke only newly granted setup access after owner review. Preserve state/backups. Do not close accounts, delete state or destroy resources as an automatic rollback. Exact access-removal/recovery procedure: [Fred to confirm].

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Assume-role denied | Trust or caller/target permission | ITO checks both sides privately. |
| Plan replaces existing resources | Wrong account/region/state | Stop and reconcile state ownership. |
| Provisioned concurrency fails | Insufficient quota | Obtain an approved resolution; do not silently remove the resource. |

## Sources and evidence gaps

[Terraform README](../../../infra/terraform/README.md), linked Terraform files and [recap evidence](../../work/handover-2026/evidence/recap-knowledge.md) establish source declarations, not deployed account controls.

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-25 | Draft access, state, budget and quota gates | APPROVAL-05 rev 2, Lane R, WI-07. |
