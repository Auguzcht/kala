---
runbook: blackboard-instance-ops
applies_to: [dev-hosted, prod]
who_runs_it: AWS / Learn administrator
time_needed: "[Fred to confirm]"
last_verified: "unverified; source review at 4f3ec29 on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 13 — operate the developer Learn instance

## When to use it

Start/stop and check an approved EC2 developer instance, or plan image expiry replacement. WI-07 draft of maintainer-only actions. A school-managed Learn service follows its administrator's service procedure instead of these EC2 examples. No instance was queried or changed by Lane R.

## Before you start

Complete [03](blackboard-learn-instance.md). Obtain the private inventory's exact instance, region/profile, stable-address association, Learn administrator access and maintenance owner. Current identifiers, instance size, startup duration, approved stop window, expiry and backup procedure: [Fred to confirm]. Access custody is in [secrets.md](../secrets.md). Do not discover the target by choosing the first instance returned.

## Steps

1. Confirm the intended account/profile and exact instance privately. Human command examples below require approved `LEARN_INSTANCE_ID` and `LEARN_REGION` values in the maintainer's shell; no values belong in repository evidence. Current CLI installation/profile invocation: [Fred to confirm]. Confirm the instance is EBS-backed and supports stop/start before any operation; storage layout: [Fred to confirm]. Check state only:

   ```sh
   aws ec2 describe-instances --instance-ids "$LEARN_INSTANCE_ID" --region "$LEARN_REGION" --query 'Reservations[].Instances[].State.Name' --output text
   ```

   Stop on an empty/mismatched target or `terminated`; do not launch a replacement automatically.
2. If stopped and the maintenance owner approves a start, the human runs:

   ```sh
   aws ec2 start-instances --instance-ids "$LEARN_INSTANCE_ID" --region "$LEARN_REGION" --query 'StartingInstances[].CurrentState.Name' --output text
   aws ec2 wait instance-running --instance-ids "$LEARN_INSTANCE_ID" --region "$LEARN_REGION"
   aws ec2 describe-instance-status --instance-ids "$LEARN_INSTANCE_ID" --region "$LEARN_REGION" --query 'InstanceStatuses[].{State:InstanceState.Name,System:SystemStatus.Status,Instance:InstanceStatus.Status}' --output table
   ```

   These documented examples were not executed. Check system and instance checks pass; `running` alone does not mean Learn is ready. On timeout/failure retain sanitized state and consult the administrator; do not loop restarts.
3. Verify stable address/DNS association privately against the approved inventory, then trusted HTTPS and Learn administrator login. A transient auto-assigned address is not proof of a stable endpoint. Exact address association, TLS and Learn application/service checks: [Fred to confirm]. Never print startup logs that may include bootstrap credentials.
4. Launch Kala once through the synthetic course as student/instructor using [08](lti-tool-registration.md)/[10](first-launch-smoke.md). If the host changed, review portal/Learn/backend platform endpoints before testing. Do not disable TLS validation or replace issuer values by guesswork.
5. Before a stop, the human notifies affected users through the institution's approved maintenance process and confirms no active demo/test/ingest/roster work. Stopping Learn does not stop API/worker scheduling or provider costs; separately approve any change to those services. Stop only the exact reviewed instance:

   ```sh
   aws ec2 stop-instances --instance-ids "$LEARN_INSTANCE_ID" --region "$LEARN_REGION" --query 'StoppingInstances[].CurrentState.Name' --output text
   aws ec2 wait instance-stopped --instance-ids "$LEARN_INSTANCE_ID" --region "$LEARN_REGION"
   ```

   Check final state using step 1. No terminate/force-stop or address release is included. Storage/address charges may continue; the billing owner verifies actual costs.
6. Record image expiry from the publisher's accepted download licence and schedule replacement review before it expires. Historical README says no in-place upgrade; current publisher support/migration method, renewal lead time and restore rehearsal: [Fred to confirm]. Preserve only approved synthetic data for a developer image. Production requires its own supported Learn migration plan.

## Verify it worked

Record maintainer/date/environment, start/stop states, status checks, Learn HTTPS availability and LTI result. Keep resource IDs and address associations privately. Record the expiry and replacement owner in the environment inventory. No archived repo session located provides the original start/stop transcript or static-IP allocation proof; these examples are proposed procedure, not historical execution evidence.

## Undo / roll back

The human may reverse an approved start with a coordinated stop, or reverse a stop using the start/readiness sequence. Neither operation guarantees an unchanged address without the verified stable-address setup. Do not terminate, detach volumes, deregister images, release addresses or discard snapshots as rollback. Exact backup/restore and expiry recovery: [Fred to confirm].

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| EC2 healthy, Learn unavailable | Application still starting, TLS/DNS or expired image | Administrator checks application readiness privately. |
| Launch breaks after restart | Address changed or registration mismatch | Verify stable DNS and all platform endpoints through 08. |
| Learn stopped, writes/errors continue elsewhere | API/worker independent | Incident lead reviews separate services; no automatic scheduler mutation. |

## Sources

[Blackboard README](../../../infra/blackboard/README.md), [environment guide](../environments.md), [archived closeout](../../archive/session-recaps/DEEPSEEK_SEPT1_CLOSEOUT.md). The API Terraform stack does not manage the Learn EC2 instance. Official CLI references confirm the documented [start](https://docs.aws.amazon.com/cli/latest/reference/ec2/start-instances.html), [stop](https://docs.aws.amazon.com/cli/latest/reference/ec2/stop-instances.html), [status](https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-instance-status.html) and [running waiter](https://docs.aws.amazon.com/cli/latest/reference/ec2/wait/instance-running.html) interfaces; this is syntax/reference checking, not an instance test.

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-25 | Draft scoped operations and expiry gates | APPROVAL-05 rev 2, Lane R, WI-07. |
