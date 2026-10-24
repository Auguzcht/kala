# What ITO needs to provision to run Kala

Written for ITO's infrastructure planning and the sponsor sign-off. Kala is handed over as source code and migrations. ITO provisions every account and service. Nothing from the student developer's personal accounts carries over.

## Components and AWS-native options

ITO raised that not all of Kala runs on AWS, which matters for management and billing under the Mapua landing zone. This table shows each component, what the handover pack describes and possible AWS-native paths. These are planning inputs, not verified hosted configuration or authorization to change hosting.

| Component | Today (dev) | Can stay as is | AWS-native alternative | Effort to switch |
| --- | --- | --- | --- | --- |
| API | Lambda container + HTTP API Gateway, Terraform | Yes, already AWS | n/a | none |
| Worker | Lambda + EventBridge schedule | Yes, already AWS | n/a | none |
| Secrets | Secrets Manager | Yes, already AWS | n/a | none |
| Logs | CloudWatch | Yes, already AWS | n/a | none |
| LMS | Blackboard Learn developer image on EC2 | Use the school's own Learn test and production instances | EC2 if a separate instance is needed | low (registration only) |
| Web app | Vercel | Yes, if a Vercel team is acceptable | S3 + CloudFront, or Amplify Hosting (static Vite build) | low |
| Generation models | OpenRouter | Yes, if the school accepts a third-party bill | Amazon Bedrock. The code already has a Bedrock provider path (`AI_PROVIDER`) | low to medium, needs testing and prompt checks |
| Embeddings | OpenAI, 1024 dimensions | Same as above | Bedrock embedding model that outputs 1024 dimensions. Needs a full re-embed (vectors from different models do not mix) | medium |
| Database | Supabase (Postgres, pgvector, RLS) | Yes, recommended | RDS or Aurora Postgres with pgvector | **high**. RLS policies use Supabase's `auth.jwt()` and roles, and the architecture supports direct Supabase reads; the endpoint audit found no current feature SDK calls. Moving needs an auth and data-access redesign |

ITO must decide hosting/provider choices with the sponsor before any separate implementation task. This document makes no infrastructure change.

## Region
Source configuration and historical notes use `ap-southeast-1` (Singapore). Hosted project region, model availability and actual billing must be confirmed by ITO/Fred; no live region verification occurred in this lane.

## Accounts and registrations ITO must own

1. AWS account in the landing zone, with Bedrock model access if Bedrock is chosen.
2. Supabase organization and project.
3. Anthology Developer Portal account and application (gives the LTI client ID and REST key and secret).
4. Tool registration on the school's Blackboard Learn instance (gives the Deployment ID), done by the Learn administrator.
5. Web hosting (Vercel team or CloudFront).
6. Model provider billing (OpenRouter and OpenAI, or Bedrock).
7. GitHub organization for the repository and CI.

## Rough cost drivers (for the sponsor)

- Model calls: tutor answers, question generation, lesson generation and tagging. The biggest variable cost. Scales with active students.
- Embeddings: one-time per course content and question bank, plus re-embeds.
- Lambda and API Gateway: low at pilot scale. Provisioned concurrency has a fixed cost if successfully allocated; current allocation is unverified (see verification gap below).
- Supabase: plan tier by database size and compute.
- Blackboard EC2 instance only if ITO runs a separate test Learn server.

Fill in actual numbers from the dev account's billing history before the sign-off meeting.

## What the "offline AI" option would mean
[ADR-013 is a planned seed](../decisions/README.md). An OpenAI-compatible endpoint is a possible design direction; compatibility, latency, structured-output quality, privacy and operating cost need a dedicated evaluation. No self-hosted model support or quality result has been verified.

## Verification gap: provisioned concurrency

[MEMORY, original lines 268–274](../archive/session-recaps/MEMORY.md) records an AWS account concurrency cap of 10; PC=1 could not leave Lambda's required 10 unreserved executions. A request for 11 was rejected, and a request for 1,001 was pending at that time. The support identifier is omitted from this extraction. The source therefore does **not** establish a warm provisioned environment.

Before claiming warm-path readiness, Fred/ITO must verify current quota, allocation readiness for the intended alias and observed timing. This lane did not query AWS or execute Terraform. The observation/check is preserved in [recap evidence](../work/handover-2026/evidence/recap-knowledge.md); it is independent of [planned Gateway access logging](../work/handover-2026/work-items/WI-18-api-gateway-access-logs.md).
