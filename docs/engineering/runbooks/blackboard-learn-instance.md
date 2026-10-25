---
runbook: blackboard-learn-instance
applies_to: [dev-hosted, prod]
who_runs_it: Learn administrator and AWS / ITO maintainer
time_needed: "[Fred to confirm]"
last_verified: "unverified; source review at 4f3ec29 on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 03 — obtain a Blackboard Learn instance

## When to use it

Provision an institutional test environment before registering Kala. This is a WI-06 draft for a human maintainer; agents do not provision infrastructure. Prefer the school's Learn test instance. The developer-image path below is a historical outline with blocking gaps, not a verified import recipe.

## Before you start

- Complete [01](aws-account-bootstrap.md) if EC2 is needed. Obtain Learn administration access through ITO and the account custody process in [the catalogue](../secrets.md).
- Confirm the environment owner, approved test users, course and network exposure: [Fred to confirm]. Use synthetic learners and material.
- Read [environments](../environments.md). School production is a fresh institutional environment; do not copy personal accounts, keys or student data.

## Steps

1. Ask the Learn administrator for a school test/staging instance and its supported integration process. Record only its host, version, owner and access procedure in handover evidence. Check that the administrator can open the system administration area.
2. If school access is available, have that administrator create a synthetic instructor, two synthetic students and a test course, then enroll them with the matching roles. Exact course creation/enrollment console paths and permissions: [Fred to confirm]. Check that both roles can open the same course. Continue at step 7.
3. If a developer image is required, have ITO approve AWS cost, image licence, expiry and support constraints first. [The infrastructure README](../../../infra/blackboard/README.md) historically describes a downloaded VMDK, not an AWS Marketplace deployment. Current download availability, licence, version, expiry and size: [Fred to confirm]. Stop if the image cannot be obtained under an institutional account.
4. Historical path: Developer Portal Learn server download → accept licence → download VMDK → upload to a private S3 staging bucket. Current portal labels, official image checksum, bucket/region, encryption policy and VM import service-role setup: [Fred to confirm]. Verify the downloaded image against the publisher's checksum before upload. Do not guess an import manifest or reuse an old AMI ID.
5. Historical path: AWS VM import `import-snapshot` → wait for completed snapshot → register an AMI → launch EC2. Exact approved CLI argument arrays or console procedure, disk format, root device, architecture, boot mode, IAM permissions, security group, storage and instance size: [Fred to confirm]. The README's t2.large-or-larger suggestion is historical and not a sizing acceptance result. Stop here until these details are supplied and reviewed.
6. Have the AWS maintainer assign the approved stable address and DNS, establish trusted HTTPS, and obtain the bootstrap administrator credential privately from the image's official instructions. Bootstrap login details are intentionally not reproduced. Rotate it through the approved account process. Static-address allocation/association procedure, HTTPS termination and original import evidence: [Fred to confirm]. Check Learn health in a browser before creating the synthetic users/course as in step 2.
7. Record the Learn host, administrator role owner, test-course label, image expiry if applicable, and the private inventory location for resource identifiers. Keep credentials only in the institutional password manager. Obtain the platform OIDC, OAuth and JWKS endpoints from the administrator; do not derive them from a remembered host/path.
8. Continue with [04](anthology-developer-app.md) and [08](lti-tool-registration.md). Use [13](blackboard-instance-ops.md) for ongoing EC2 operation. Check that all three procedures agree on the same Learn environment.

## Verify it worked

The named administrator signs in over approved HTTPS; the instructor and students open the same test course with their intended roles. Record date, source revision, environment, verifier, Learn version and pass/fail per role. This alone does not verify LTI or REST; those checks belong to 08 and 10. No instance was accessed by Lane R.

## Undo / roll back

For a school test instance, ask the Learn administrator to remove only the new test placement/users after approval; do not alter the shared instance. For a failed EC2 bootstrap, preserve import/task evidence and let the AWS maintainer review cleanup of this environment's staging objects, volumes, snapshots, AMI and address. Exact retention and deletion approval: [Fred to confirm]. Never terminate or release existing resources as an automatic rollback.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| No supported download or image expired | Historical image distribution changed | Stop; obtain the school test instance or a supported image from Anthology. |
| VM import cannot start or fails | Import permissions, unsupported disk/boot layout | Retain sanitized task status; have ITO validate publisher requirements and the reviewed manifest. |
| Browser cannot reach Learn | Instance not ready, address/DNS/firewall/TLS | Check instance status and approved network settings using 13; do not disable TLS verification as a workaround. |
| Instructor/student cannot open course | Enrollment or account-role mismatch | Learn administrator verifies the synthetic memberships before attempting LTI. |

## Sources and evidence gaps

[Blackboard README](../../../infra/blackboard/README.md), archived MEMORY and archived closeout provide historical architecture context. They do not contain a reproducible AMI import manifest, a confirmed static-IP procedure or current portal screenshots. No parent-chat material was consulted. All missing details above require Fred's evidence before execution.

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-25 | Draft school-instance path and gated developer-image path | APPROVAL-05 rev 2, Lane R, WI-06; no provisioning performed. |

## Historical sources

These links preserve provenance only. Required rules, commands and limits are stated above; do not read the records unless the task explicitly names them.

- [archived closeout](../../archive/session-recaps/DEEPSEEK_SEPT1_CLOSEOUT.md)
- [archived MEMORY](../../archive/session-recaps/MEMORY.md)
