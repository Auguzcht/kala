# Runbooks: standing Kala up from zero

Author and verify these procedures before using them to provision a new environment. Then follow the order below. Each one lists the outputs the next one needs. Every runbook uses `../documentation/templates/runbook.md` and records `last_verified`.

| # | Runbook file | Produces | Needs from earlier steps | Source material to reconcile |
| --- | --- | --- | --- | --- |
| 01 | [aws-account-bootstrap.md](aws-account-bootstrap.md) | IAM admin role (no long-lived root keys), region, budget alert, Terraform state backend | AWS account | `infra/terraform/README.md` |
| 02 | [02-database-setup.md](02-database-setup.md) | Project URL, keys, extensions (`vector`, `pgcrypto`), migrations applied, pilot institution row | none | `docs/SUPABASE.md`, `docs/runbooks/00xx-apply.md` |
| 03 | [blackboard-learn-instance.md](blackboard-learn-instance.md) | Running Learn instance (school test instance, or developer VMDK imported to an AMI on EC2), static address, admin and test users, test course | AWS account | `infra/blackboard/README.md`, session notes on the AMI import and static IP |
| 04 | [anthology-developer-app.md](anthology-developer-app.md) | Application key and secret, application ID (LTI client ID), REST app | API base URL from 06 (register placeholders first, update after 06) | Developer Portal notes |
| 05 | [secrets-manager.md](secrets-manager.md) | JSON secret populated (current source: `kala/app`; environment-scoped naming is proposed) | 02, 03, 04 | `infra/terraform/README.md` "Set the application secrets", `docs/engineering/secrets.md` |
| 06 | [terraform-apply.md](terraform-apply.md) | ECR repos, API Lambda and `live` alias, worker Lambda, EventBridge schedule, API Gateway, IAM, CloudWatch | 01, 05, built images | `infra/terraform/` |
| 07 | [deploy-backend.md](deploy-backend.md) | New image, published version, alias moved | 06 | `make deploy`, README "Deploying backend changes" |
| 08 | [lti-tool-registration.md](lti-tool-registration.md) | Tool registered on the Learn instance with redirect `<api>/lti/launch`, login `<api>/lti/login`, JWKS `<api>/lti/jwks`, Deployment ID, placement in a course, REST integration allowed | 03, 04, 06 | session notes from the ngrok era and the switch to API Gateway |
| 09 | [vercel-web.md](vercel-web.md) | Vercel project, `VITE_*` variables, domain, `FRONTEND_URL` updated in the secret | 02, 06 | `apps/web/README.md` |
| 10 | [first-launch-smoke.md](first-launch-smoke.md) | Student and instructor launch, ingest of one course, one diagnostic, one tutor answer | all | `docs/TESTING.md` |
| 11 | [key-rotation.md](key-rotation.md) | Rotated secrets with no downtime | any time | Session record section 10 |
| 12 | [incident-response.md](incident-response.md) | How to size and handle a production failure (CloudWatch queries, which logs exist, what does not exist yet) | any time | INC-001 (0034 submit failure) |
| 13 | [blackboard-instance-ops.md](blackboard-instance-ops.md) | Start, stop, verify the EC2 Learn instance, image expiry plan | 03 | the start, stop and describe commands in the notes |

Steps 03, 04 and 08 are where most of the undocumented knowledge sits. Write them first, from memory and screenshots, while the person who did them is still on the project.

## Authoring and verification state

These are planned runbooks under WI-06/WI-07. Only [deploy-backend.md](deploy-backend.md) and [02-database-setup.md](02-database-setup.md) currently contain **partial, unverified knowledge extracts**; neither is a full executable procedure. Missing files are reported separately by the docs link check, not invented. [TESTING.md](../../TESTING.md) remains Fred's preserved student/instructor checklist until manual-smoke/first-launch procedures are authored. The existing migration-apply notes remain at [0034](../../runbooks/0034-apply.md), [0035](../../runbooks/0035-apply.md) and [0036](../../runbooks/0036-apply.md) as dated evidence, not fresh migration authorization.

Runbook 02 reconciles the complete 36-file migration history; Lane DB owns the gated local stack and database guide. Lane DB rebases after Lane D's merge, then updates references in this post-archive tree. The historical 0036 SQL comment must stay unchanged.
