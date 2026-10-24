---
runbook: deploy-backend
applies_to: [dev-hosted, prod]
who_runs_it: Fred / ITO maintainer
last_verified: unverified; extraction only at e9de105 on 2026-10-24
status: partial
---

# Backend deployment — preserved bootstrap lessons

**Incomplete procedure. WI-07 must supply the full pre-check, verification, undo and troubleshooting steps before a new maintainer follows it.** This extract preserves unique source knowledge; no deployment or infrastructure change was executed by Lane D.

## Ordering constraints

Create the ECR repositories and push a compatible image before creating image-dependent Lambda resources. An initial Terraform configuration can depend on an image that does not exist yet; source setup uses a phased bootstrap for that reason.

A Secrets Manager container can exist with no value. Populate and verify required configuration **before first invocation**; otherwise cold settings initialization can fail or leave later operations failing. A catch-and-warn loader is not evidence that an empty secret is usable. Consult [Lane C's names-only catalogue](../secrets.md); never paste values into evidence.

## Existing deployment entry point

The repository's canonical redeploy entry point is `make deploy`. The existing Makefile pins `--platform linux/amd64 --provenance=false --sbom=false`; bare Docker builds in old notes are host-dependent. Fred runs this once after the approved S/T/F integration, then records deployed revision and performs the student/instructor smoke in [TESTING.md](../../TESTING.md), plus the approved tutor/Study/auth checks. Agents prepare changes and evidence; a deployed hash and Active state alone do not prove application behavior.

## Still to author under WI-07

Named access prerequisites, exact initial bootstrap steps, alias/version checks, rollback and error recovery. Keep local and hosted procedure boundaries explicit. No current hosted quota, image, secret membership or deployment status is asserted here.

Sources: [closeout, original lines 28–35](../../archive/session-recaps/DEEPSEEK_SEPT1_CLOSEOUT.md), [infra README](../../../infra/terraform/README.md), [Makefile](../../../Makefile), [root README](../../../README.md), [recap evidence](../../work/handover-2026/evidence/recap-knowledge.md).
