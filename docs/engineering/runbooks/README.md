# Runbooks: standing Kala up from zero

All 13 procedures now have **unverified drafts** under WI-06/WI-07. Resolve their blocking `[Fred to confirm]` items and record named human execution before using them to provision an environment. The structure follows [the runbook template](../documentation/templates/runbook.md); `last_verified` distinguishes source review from execution. Agents never perform the hosted actions described here.

| # | Runbook file | Produces | Needs from earlier steps | Source material to reconcile |
| --- | --- | --- | --- | --- |
| 01 | [aws-account-bootstrap.md](aws-account-bootstrap.md) | Approved admin access, region, budget/state/quota decisions (backend not yet declared) | AWS account | `infra/terraform/README.md` |
| 02 | [02-database-setup.md](02-database-setup.md) | Project URL, keys, extensions (`vector`, `pgcrypto`), migrations applied, pilot institution row | none | Historical 36-file audit plus [0037 local replay/apply note](../../runbooks/0037-apply.md) |
| 03 | [blackboard-learn-instance.md](blackboard-learn-instance.md) | Running Learn instance (school test instance, or developer VMDK imported to an AMI on EC2), static address, admin and test users, test course | AWS account | `infra/blackboard/README.md`, High-level Blackboard README; import/static-address transcript [Fred to confirm] |
| 04 | [anthology-developer-app.md](anthology-developer-app.md) | Application key and secret, application ID (LTI client ID), REST app | API base URL from 06; early metadata only, placeholder support [Fred to confirm] | Blackboard README and connector; current Portal screenshots [Fred to confirm] |
| 05 | [secrets-manager.md](secrets-manager.md) | JSON secret populated (current source: `kala/app`; environment-scoped naming is proposed) | 02, 03, 04 | `infra/terraform/README.md` "Set the application secrets", `docs/engineering/secrets.md` |
| 06 | [terraform-apply.md](terraform-apply.md) | ECR repos, API Lambda and `live` alias, worker Lambda, EventBridge schedule, API Gateway, IAM, CloudWatch | 01, 05, built images | `infra/terraform/` |
| 07 | [deploy-backend.md](deploy-backend.md) | Both images updated; API version/alias and worker completion checked | 06 | `make deploy`, README "Deploying backend changes" |
| 08 | [lti-tool-registration.md](lti-tool-registration.md) | Tool registered on the Learn instance with redirect `<api>/lti/launch`, login `<api>/lti/login`, JWKS `<api>/lti/jwks`, Deployment ID, placement in a course, REST integration allowed | 03, 04, 06 | LTI source/tests; current Learn placement screenshots [Fred to confirm] |
| 09 | [vercel-web.md](vercel-web.md) | Vercel project, `VITE_*` variables, domain, effective backend origin aligned through its Terraform-owned Lambda setting | 02, 06 | `apps/web/README.md` |
| 10 | [first-launch-smoke.md](first-launch-smoke.md) | Student and instructor launch, ingest of one course, one diagnostic, one tutor answer | all | `docs/TESTING.md` |
| 11 | [key-rotation.md](key-rotation.md) | Replacement checks and signing-key gates; downtime-free rollover unproven | any time | Names-only catalogue and current signing-key source |
| 12 | [incident-response.md](incident-response.md) | How to size and handle a production failure (CloudWatch queries, which logs exist, what does not exist yet) | any time | 0035 apply note, INC-002, current error/timing source |
| 13 | [blackboard-instance-ops.md](blackboard-instance-ops.md) | Start, stop, verify the EC2 Learn instance, image expiry plan | 03 | Proposed scoped CLI examples; original transcript [Fred to confirm] |

## Authoring and verification state

These drafts prioritize Learn acquisition, developer registration and LTI placement (03, 04 and 08). **No procedure is execution-verified by Lane R.** Prior observations stay attributed: the migration replay proves empty-schema SQL replay, and v6 deployment evidence proves image/alias/health metadata. Neither establishes a fresh environment or authenticated acceptance. [TESTING.md](../../TESTING.md) remains the preserved baseline, incorporated by runbook 10.

Each procedure states its own unresolved prerequisites; review those before execution. The source-review transcript is historical, not a required operating input. Exact time estimates, current portal/console fields and resource/account details are `[Fred to confirm]`; public documentation is not evidence that these procedures ran.

## Dependency and execution gates

1. Start with 01's account/state/quota approval. 02's local workflow waits for Lane DB and Fred's hosted Postgres major. At refreshed base `6e21eed`, **37 repository migration files** (0001–0037) remain in `packages/db/migrations`; relocation is pending FG-2. B's locally merged 0037 and [exact apply runbook](../../runbooks/0037-apply.md) are read-only inputs for Lane R. For dev-hosted, Fred reported 0037 application and read-only checks passed on 2026-10-25. Fresh institutional setup still needs reviewed application; file count alone does not establish hosted state.
2. Obtain Learn via 03, then prepare portal metadata in 04. API endpoint fields cannot be finalized until 06 produces the API; whether provisional registration is supported is unverified. Do not submit invented placeholder URLs.
3. 05 and 06 are phased together: approved state → ECR/empty secret bootstrap → secret population and images → full reviewed stack. Secret readiness and database readiness must precede worker scheduling/invocation. This sequence is a proposed fresh-environment procedure, not an executed transcript.
4. Finalize 04/08 after 06 and 09's frontend origin. 08 completes the Learn deployment/placement and separate REST integration; 10 accepts real synthetic-role launches and material/learning flows.
5. Use 07 for subsequent backend code releases. Current release sequence: coordinator supplies the reviewed SHA and complete local checks; the maintainer verifies required migrations, deploys backend changes, checks alias/worker/startup, then publishes main and waits for Vercel Ready; live acceptance is a separate named-human gate. For frontend-only changes, publish only after review; no backend deploy is required. FG-1 provider configuration/refresh is separate from FG-2, which blocks Lane DB only. 11 and 12 apply when needed; 13 applies only to an EC2 developer Learn instance. Any shutdown/cutover requires separate named human approval.

All hosted/infrastructure mutation steps in these documents belong to named human maintainers; local verification/generation may run only within its separately authorized coordinator scope. A draft command is not authorization for an agent deploy, hosted migration/write, key rotation, merge or push. Lane R stops with its audit report for coordinator review.

## Historical sources — authoring approvals

[APPROVAL-05 rev 2](../../work/handover-2026/approval-05.md) is now committed; the original Lane R draft used the supplied attachment. [APPROVAL-06 rev 2](../../work/handover-2026/approval-06.md) continues R/P/C2 docs and sets the current same-day Fred gates. Its Lane R grant is: draft runbooks 01–13 from archived records, MEMORY and READMEs; mark unknowns `[Fred to confirm]`; own only `docs/engineering/runbooks/`. Existing [APPROVAL-01](../../work/handover-2026/approval-01.md), [02](../../work/handover-2026/approval-02.md), [03](../../work/handover-2026/approval-03.md) and [04](../../work/handover-2026/approval-04.md) retain their database, privacy and integration gates. The full approval attachment and all credential material are excluded from these drafts.

## History

| Date | Change | Source |
| --- | --- | --- |
| 2026-10-24 | Install registry and two partial knowledge extracts | WI-03, APPROVAL-01. |
| 2026-10-25 | Draft all 13 procedures and reconcile dependencies/gaps | WI-06/WI-07, APPROVAL-05 rev 2, Lane R. |
| 2026-10-25 | Refresh from local main 6e21eed: 37 migrations, exact 0037 note and same-day gates | APPROVAL-06 rev 2 and coordinator Lane R continuation. |

## Historical sources

These links preserve provenance only. Required rules, commands and limits are stated above; do not read the records unless the task explicitly names them.

- [v6 deployment evidence](../../work/handover-2026/evidence/deployment-2026-10-25.md)
- [migration replay](../../work/handover-2026/evidence/audit-migration-replay.md)
