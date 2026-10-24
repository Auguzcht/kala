# Environments

The target environment boundary is a complete separately owned set of systems. The table lists six service/account groups. Personal dev-hosted arrangements are historical source records, not live observations. Nothing from personal accounts is carried into school production under the full-transfer plan.

| System | What it provides | Owned in dev today by | Target owner after handover |
| --- | --- | --- | --- |
| Blackboard Learn instance | The LMS that launches Kala | Developer AMI on EC2 in a personal AWS account | ITO (school test instance, or school-owned EC2) |
| Anthology Developer Portal app | LTI client ID and REST application key/secret | Personal developer account | ITO-owned developer account |
| AWS account | API Lambda, worker Lambda, API Gateway, EventBridge, ECR, Secrets Manager, CloudWatch, (Bedrock) | Personal account, region `ap-southeast-1` | School AWS account or organization member account |
| Supabase project | Postgres, pgvector, RLS, storage | Personal organization | New school organization/project (no account/data transfer) |
| Vercel project | Hosted SPA | Personal | School team |
| Model providers | OpenRouter (chat and generation), OpenAI (embeddings) | Personal keys | School-billed keys, or self-hosted (see ADR on offline AI) |

## Environment list

| Name | Purpose | Web | API | Database | LMS |
| --- | --- | --- | --- | --- | --- |
| `local` | Day-to-day development | Vite :5173 | uvicorn :8000 | Local Supabase in Docker | Mock LTI launch script |
| `local-on-dev` | UI work with real data | Vite :5173 | dev API Gateway | dev Supabase | Real launch, token copied to localhost |
| `dev-hosted` | Current live system (pilot and demos) | Vercel production deployment | API Gateway `live` alias | Personal Supabase project | EC2 developer AMI |
| `prod` | School-owned system, provisioned by ITO from scratch in the Mapua landing zone | ITO chooses | ITO's AWS | ITO's new Supabase project, built from `supabase/migrations` | School Learn instance |

The pack names the personal pilot/demo system `dev-hosted`, even where older notes call it "production". In the docs it is called `dev-hosted` so nobody mistakes personal accounts for the school's production. It is a full transfer: nothing in `dev-hosted` is migrated. No data, no accounts, no keys. Any later shutdown requires its own explicit human authorization after ITO verification (runbook 10); it is not an action for this lane. What ITO provisions is listed in `infrastructure-requirements.md`.

## Recreating an environment

Follow [the runbook registry](runbooks/README.md) once its procedures are authored and verified. The local stack remains gated under Lane DB; the listed local environment is the target, not a completed setup claim. The order matters because each system needs an output from the one before it (for example, the LTI registration needs the API Gateway URL, and the API needs the LTI client ID).

## Known gotchas

- The API loads secrets from Secrets Manager with `os.environ.setdefault`. A Lambda environment variable with the same name silently wins over the secret.
- Secret loading never crashes the Lambda. A missing or unreadable secret shows only as a `warning: could not load secrets` line in CloudWatch, followed by failures elsewhere.
- Vite embeds `VITE_*` values at build time. Change them in Vercel, then redeploy.
- The API CORS allows `http://localhost:5173` only for local work.
- The Blackboard developer image expires. Plan a migration before the expiry date shown on the download page.

See [APPROVAL-01](../work/handover-2026/approval-01.md) for current gates. Source defaults do not establish deployed provider selection. [The config audit](../work/handover-2026/evidence/audit-config.md) proves source precedence only; actual hosted secret memberships are unknown. Lane C owns the [names-only secrets catalogue](secrets.md).
