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

## Cost-driver worksheet (WI-13, for the sponsor)

[WI-13](../work/handover-2026/README.md#work-items) remains `planned`: this worksheet identifies inputs to collect, not a completed estimate. Fred/ITO must use dev billing history and the chosen institutional plans before sponsor sign-off. No billing account or live prices were inspected for Lane C2; no prices, totals or pilot-scale savings are assumed.

| Cost driver | Quantity or choice to confirm | Billing evidence and monthly cost |
| --- | --- | --- |
| Generation models | Active students; tutor calls; question, lesson and tagging jobs; input/output tokens; model/provider mix; retries and fallback use: [Fred to confirm] | Usage export, applicable rates and billed amount: [Fred to confirm] |
| Embeddings | Course-content and question-bank volume; live tutor query embeddings; cache reuse and re-embedding frequency; model/provider choice: [Fred to confirm] | Token/request usage, applicable rates and billed amount: [Fred to confirm] |
| Lambda API and worker | Invocations, memory, duration, architecture, scheduled and self-invoked worker runs: [Fred to confirm] | Usage, allowances and billed amount: [Fred to confirm] |
| Lambda provisioned concurrency | Current quota, alias allocation, readiness, memory and hours enabled (see verification gap below): [Fred to confirm] | Allocation evidence, usage and billed amount: [Fred to confirm] |
| HTTP API Gateway | Requests and transferred data: [Fred to confirm] | Usage, allowances and billed amount: [Fred to confirm] |
| CloudWatch | Log ingestion, retention, stored volume and queries: [Fred to confirm] | Usage and billed amount: [Fred to confirm] |
| Supporting AWS services | ECR image storage/transfer, Secrets Manager storage/access and EventBridge schedule frequency: [Fred to confirm] | Per-service usage and billed amount: [Fred to confirm] |
| Supabase | Plan, compute, database/vector size, attachment storage, backups and egress: [Fred to confirm] | Plan invoice, included allowances, overages and billed amount: [Fred to confirm] |
| Web hosting | Vercel team/plan, seats, builds, traffic and bandwidth; institutional hosting choice: [Fred to confirm] | Current invoice and chosen hosting estimate: [Fred to confirm] |
| Blackboard | Use of school-managed Learn versus a separate EC2 test server; instance size, uptime, disks, snapshots and licensing responsibility: [Fred to confirm] | Separate test-server bill and any incremental institutional cost: [Fred to confirm] |
| Other institutional costs | Repository plan, domain/DNS, support, cross-service data transfer and any additional registrations or licences: [Fred to confirm] | Applicable invoices and incremental costs without double counting: [Fred to confirm] |

Record the billing period, currency, taxes, credits/free allowances and whether each charge is recurring or one-time: [Fred to confirm]. Record pilot active students, courses, uploaded content and expected growth so observed dev spend can be separated from a pilot projection: [Fred to confirm]. Dev monthly total, institutional pilot estimate, budget owner and sponsor-approved ceiling: [Fred to confirm].

Any AWS-native alternative needs its own usage and migration estimate after ITO chooses a direction: [Fred to confirm]. The component table above is not cost parity evidence or authorization to migrate.

## What the "offline AI" option would mean
[ADR-013 is a planned seed](../decisions/README.md). An OpenAI-compatible endpoint is a possible design direction; compatibility, latency, structured-output quality, privacy and operating cost need a dedicated evaluation. No self-hosted model support or quality result has been verified.

## Verification gap: provisioned concurrency

MEMORY, original lines 268–274 records an AWS account concurrency cap of 10; PC=1 could not leave Lambda's required 10 unreserved executions. A request for 11 was rejected, and a request for 1,001 was pending at that time. The support identifier is omitted from this extraction. The source therefore does **not** establish a warm provisioned environment.

Before claiming warm-path readiness, Fred/ITO must verify current quota, allocation readiness for the intended alias and observed timing. This lane did not query AWS or execute Terraform. The observation/check is preserved in recap evidence; it is independent of [planned Gateway access logging](../work/handover-2026/work-items/WI-18-api-gateway-access-logs.md).

## Change log

| Date | Change | Decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-25 | Add cost-driver and billing-evidence placeholders for Fred/ITO; leave estimates and sign-off pending | APPROVAL-05 rev 2 section 4, Lane C2 | WI-13 |

## Historical sources

These links preserve provenance only. Required rules, commands and limits are stated above; do not read the records unless the task explicitly names them.

- [MEMORY, original lines 268–274](../archive/session-recaps/MEMORY.md)
- [recap evidence](../work/handover-2026/evidence/recap-knowledge.md)
