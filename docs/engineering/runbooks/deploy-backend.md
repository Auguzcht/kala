---
runbook: deploy-backend
applies_to: [dev-hosted, prod]
who_runs_it: Fred / ITO deployment maintainer
time_needed: "[Fred to confirm]"
last_verified: "unverified as a full procedure; source review at 6e21eed on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 07 — deploy backend images

## When to use it

Redeploy approved API/worker source into an existing stack. WI-07 draft replacing the partial extract. The named human deploys; agents prepare checks and stop at approval. Initial infrastructure uses [06](terraform-apply.md).

## Before you start

- Use the release gates stated here: reviewed local integration, required schema verification, human backend deployment, fast-forward publication, Vercel readiness, then separate live acceptance. Coordinator completes the approved local integration/full checks, reports the exact final SHA and included/left-out work, then stops. This lane does not merge, push or deploy.
- Confirm clean reviewed revision and intended CLI/profile/account/region privately. Credentials stay in [approved custody](../secrets.md).
- There are **37 repository migrations** at base `6e21eed`. FG-3 requires Fred to apply [0037 using its exact runbook](../../runbooks/0037-apply.md), including baseline/checksum, column-absence, RLS/grant/service-privilege and count pre-checks, then type/nullability/no-default, unchanged-access and row/pin post-checks. Save his results before FG-4. The new API's list route requires pinned_at; do not deploy it first. Fred reported dev-hosted 0037 application and read-only post-checks passed on 2026-10-25; do not reapply it. A fresh institutional target requires its own verification. FG-2 continues to gate Lane DB, not this separately approved maintainer-only 0037 procedure.
- Record previous API `live` version and immutable worker image digest privately; source has no worker version alias. Confirm [05](secrets-manager.md), rollback compatibility, Docker and test window. Recovery owner/window: [Fred to confirm].

## Steps

1. Coordinator runs the full local checks from [local-development.md](../local-development.md): `uv run pytest` separately in API and worker, checked-in frontend Node tests and Study component tests, web lint/typecheck/build, configuration check and all four browser suites listed there. Shared committed `services/conftest.py` disables dotenv, clears inherited app/AWS settings, generates test-only signing material and blocks network before collection; both service pytest configs retain `--confcutdir=..`. External renderer/browser fixtures remain documented limitations; do not invent a package test script or replace isolation with live configuration. Use the complete portable commands and fixture setup in local-development.md; dated counts belong only in verification records. One coordinated browser server on 5173 only. Lane R executes none of these runtime suites for this docs refresh.
2. **FG-4 — Fred only**, after FG-3 and final coordinator checks, runs the canonical target from the approved repository revision:

   ```sh
   make deploy
   ```

   Check identity/region first. Existing Makefile supports `AWS` and `REGION` overrides; approved institutional profile/wrapper invocation: [Fred to confirm]. Keep full command output private and share only selected metadata/status, never configuration payloads.
3. The target logs into ECR via password stdin; builds/pushes both images with `linux/amd64 --provenance=false --sbom=false`; updates API; waits for its update; publishes a version; advances `live`; then updates worker. `latest` is mutable; record immutable digest/source mapping.
4. Check exit status and each stage. API success followed by worker failure is a partial deploy. The target does not wait for worker completion: separately check worker State/LastUpdateStatus until successful or failed. Do not repeat the entire deploy blindly.
5. Inspect selected metadata only: API version State/LastUpdateStatus and resolved image digest, `live` version/routing weights, Gateway alias integration, worker State/LastUpdateStatus/digest. Avoid full environment or `get-function` responses. Keep identifiers privately and statuses/revision in shared evidence. Expect the alias entirely on the approved version unless a weighted rollout was explicitly approved.
6. Fred checks public `/health` with bounded status-only output and CloudWatch for startup errors. At FG-4 he then runs `git push origin main` from the approved main checkout using the standing fetch/ancestry/fast-forward checks and waits for Vercel Ready. Agents stop at this gate; no agent push is authorized. FG-5 is Fred's [10](first-launch-smoke.md) acceptance, covering launch, course context, Diagnostic, Study/Test, Tutor persistence and instructor views with no unauthorized cross-user/course access. Health/Active does not prove providers, RLS or persistence.
7. Report merge, deployment, Git publication, Vercel readiness and FG-5 acceptance separately. Before each gate, the coordinator supplies Fred its name, exact steps, expected result and rollback. Leave unfinished/non-green lanes out under the same-day lateness rule, with branch/status recorded. The paid fallback setting was verified in Secrets Manager on 2026-10-25 under a narrow explicit delegation; fresh Lambda instances and live hint retest remain human release checks; provider recovery is not inferred from merged diagnostics. Preserve failed checks and later results.

## Contract generation before release checks

The web manifest's `pnpm --filter web gen:api` chains an API export pre-hook and frontend type generation, but a bare non-pytest export does not automatically load pytest isolation. For the coordinator's isolated release refresh, use the source-traced two-stage method recorded at 7036f27: in a fresh process from `services/api`, load committed isolation before exporting, then regenerate types from repository root:

```sh
(cd services/api && uv run python - <<'PYGEN'
import runpy
runpy.run_path('../conftest.py')
runpy.run_path('scripts/export_openapi.py', run_name='__main__')
PYGEN
)
pnpm --filter web exec openapi-typescript ../../services/api/openapi.json -o src/lib/api/types.gen.ts
```

These are documented local generation steps, not commands run by Lane R. Coordinator reviews semantic OpenAPI/type diffs and reruns web typecheck/build. The current integration evidence attributes generation to 7036f27 and includes B's PATCH/list contracts; do not regenerate database types with the hosted-ref script. Lane DB still owns local database type generation after FG-2. Never use test configuration for application startup/deployment.

## Verify it worked

Record deployer/date/environment/revision, API version/alias/image mapping privately, worker completion, health and role-based smoke. 2026-10-25 evidence confirmed v6 image/source/alias, worker update and health, while explicitly leaving authenticated Learn/tutor/Study unverified. It does not verify this whole procedure. No deploy or AWS query was performed by Lane R.

## Undo / roll back

At FG-R Fred restores the approved previous API live alias and promotes the previous Vercel deployment after schema/config compatibility review; agents do not perform either action. Leave 0037 and its stored pin values intact. A human can move API `live` to the recorded previous published version, including its captured configuration. Worker recovery requires code update to the recorded immutable ECR digest and completion check; there is no worker alias to move. Exact rollback commands, version retention and rehearsal: [Fred to confirm]. Never revert migrations, restore revoked credentials or use mutable `latest` as a previous-image reference.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| New code absent | Older alias target | Compare version/digest before another deploy. |
| Worker behavior unchanged | Update pending/failed | Check completion independently. |
| Tutor 502 with healthy API | Provider/embedding/config failure | Follow [12](incident-response.md). |
| Secret edit has no effect | Cached settings or environment override | Follow 05; diagnose before rebuilding. |

## Sources

[Makefile](../../../Makefile), [Lambda](../../../infra/terraform/lambda.tf), [Gateway](../../../infra/terraform/apigw.tf), [root README](../../../README.md), bootstrap extraction.

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-24 | Preserve image/secret bootstrap lessons | WI-03 extraction. |
| 2026-10-25 | Draft release, verification and recovery gates | APPROVAL-05 rev 2, Lane R, WI-07. |
| 2026-10-25 | Source-trace 37-file/0037 prerequisite, isolated generation/current checks and FG-1–FG-5/FG-R | APPROVAL-06 rev 2; source 6e21eed; no execution. |

## Historical sources

These links preserve provenance only. Required rules, commands and limits are stated above; do not read the records unless the task explicitly names them.

- [coordinator integration evidence](../../work/handover-2026/evidence/approval-06-integration.md)
- [2026-10-25 evidence](../../work/handover-2026/evidence/deployment-2026-10-25.md)
- [bootstrap extraction](../../work/handover-2026/evidence/recap-knowledge.md)
