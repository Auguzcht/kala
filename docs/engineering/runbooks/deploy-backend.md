---
runbook: deploy-backend
applies_to: [dev-hosted, prod]
who_runs_it: Fred / ITO deployment maintainer
time_needed: "[Fred to confirm]"
last_verified: "unverified as a full procedure; source review at 4f3ec29 on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 07 — deploy backend images

## When to use it

Redeploy approved API/worker source into an existing stack. WI-07 draft replacing the partial extract. The named human deploys; agents prepare checks and stop at approval. Initial infrastructure uses [06](terraform-apply.md).

## Before you start

- Get coordinator approval of integrated revision and required checks. APPROVAL-05's proposed second release is not this lane's authorization to merge/push/deploy.
- Confirm clean reviewed revision and intended CLI/profile/account/region privately. Credentials stay in [approved custody](../secrets.md).
- Confirm migrations were human-applied and backward compatible first. At base, 36 files are current. Lane B's 0037 is pending with its own apply runbook; this procedure does not apply it.
- Record previous API `live` version and immutable worker image digest privately; source has no worker version alias. Confirm [05](secrets-manager.md), rollback compatibility, Docker and test window. Recovery owner/window: [Fred to confirm].

## Steps

1. Run relevant local checks from [local-development.md](../local-development.md). API and worker suites run in separate service processes using committed shared isolation, without live credentials. Integrated release requires both suites, web lint/typecheck/build and feature-specific acceptance.
2. The named human runs the canonical target from the approved repository revision:

   ```sh
   make deploy
   ```

   Check identity/region first. Existing Makefile supports `AWS` and `REGION` overrides; approved institutional profile/wrapper invocation: [Fred to confirm]. Keep full command output private and share only selected metadata/status, never configuration payloads.
3. The target logs into ECR via password stdin; builds/pushes both images with `linux/amd64 --provenance=false --sbom=false`; updates API; waits for its update; publishes a version; advances `live`; then updates worker. `latest` is mutable; record immutable digest/source mapping.
4. Check exit status and each stage. API success followed by worker failure is a partial deploy. The target does not wait for worker completion: separately check worker State/LastUpdateStatus until successful or failed. Do not repeat the entire deploy blindly.
5. Inspect selected metadata only: API version State/LastUpdateStatus and resolved image digest, `live` version/routing weights, Gateway alias integration, worker State/LastUpdateStatus/digest. Avoid full environment or `get-function` responses. Keep identifiers privately and statuses/revision in shared evidence. Expect the alias entirely on the approved version unless a weighted rollout was explicitly approved.
6. Check public `/health` with a bounded status-only request. Then the human follows [10](first-launch-smoke.md), including release-specific tutor, Study and authorization checks. Health/Active does not prove providers, RLS or persistence.
7. Report merge, deployment and live acceptance separately. Publication/push is a separate coordinator/human gate; this draft grants no agent push. Preserve failed checks and subsequent results.

## Verify it worked

Record deployer/date/environment/revision, API version/alias/image mapping privately, worker completion, health and role-based smoke. [2026-10-25 evidence](../../work/handover-2026/evidence/deployment-2026-10-25.md) confirmed v6 image/source/alias, worker update and health, while explicitly leaving authenticated Learn/tutor/Study unverified. It does not verify this whole procedure. No deploy or AWS query was performed by Lane R.

## Undo / roll back

Deployment owner approves recovery after schema/config compatibility review. A human can move API `live` to the recorded previous published version, including its captured configuration. Worker recovery requires code update to the recorded immutable ECR digest and completion check; there is no worker alias to move. Exact rollback commands, version retention and rehearsal: [Fred to confirm]. Never revert migrations, restore revoked credentials or use mutable `latest` as a previous-image reference.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| New code absent | Older alias target | Compare version/digest before another deploy. |
| Worker behavior unchanged | Update pending/failed | Check completion independently. |
| Tutor 502 with healthy API | Provider/embedding/config failure | Follow [12](incident-response.md). |
| Secret edit has no effect | Cached settings or environment override | Follow 05; diagnose before rebuilding. |

## Sources

[Makefile](../../../Makefile), [Lambda](../../../infra/terraform/lambda.tf), [Gateway](../../../infra/terraform/apigw.tf), [root README](../../../README.md), [bootstrap extraction](../../work/handover-2026/evidence/recap-knowledge.md).

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-24 | Preserve image/secret bootstrap lessons | WI-03 extraction. |
| 2026-10-25 | Draft release, verification and recovery gates | APPROVAL-05 rev 2, Lane R, WI-07. |
