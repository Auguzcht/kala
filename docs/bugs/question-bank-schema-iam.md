# Question-bank schema/IAM brief report

Date: 2026-10-06. No new model calls were made for this report. The latency
and depth figures below are computed from `scripts/bench/out/batch_items.raw.json`
and read-only content metadata queries.

## Existing benchmark follow-up

For batch size 5, `max_tokens=8192`:

| Skill | p50 | p95 | Runs >75s | Runs >90s |
|---|---:|---:|---:|---:|
| Compare managed AWS services against self-managed alternatives | 49.4s | 264.1s | 1 | 1 |
| Describe the six benefits of cloud computing and AWS CAF | 63.6s | 83.3s | 1 | 0 |
| Evaluate personal readiness for AWS Cloud Practitioner certification | 102.4s | 161.4s | 3 | 3 |
| Overall, 15 runs | 62.9s | 214.4s | 5 | 4 |

The earlier `~3 batches to MIN_USABLE` estimate covered all 10 approved AWS101
skills after summing their deficits, not only the three benchmark skills. Under
section 0/A1’s amended similarity-only rule (`SIM_THRESHOLD=0.544`, minimum
200-character chunk), the depths are:

| Approved skill | Similarity depth | Flag |
|---|---:|---|
| Compare and contrast traditional IT infrastructure with cloud computing models | 3 | |
| Distinguish between IaaS, PaaS, and SaaS service models and deployment models | 1 | |
| Identify appropriate AWS service categories | 8 | |
| Describe the six benefits of cloud computing and AWS CAF | 7 | |
| Design a cloud architecture in AWS | 1 | |
| Configure auto scaling policies and CloudWatch monitoring | 1 | |
| Compare managed AWS services against self-managed alternatives | 2 | |
| Identify AWS certification pathways and credential requirements | 9 | |
| Compile course deliverables for AWS course badge submission | 8 | |
| Evaluate personal readiness for AWS Cloud Practitioner certification | 9 | |

No approved skill has depth 0. The estimate therefore remains an all-course
estimate, but the low-depth skills still need significant generation.

## Migration

Implemented in [0021_question_bank.sql](../../packages/db/migrations/0021_question_bank.sql).
It adds the requested generated-item metadata/indexes, `quiz_set_items` with
legacy backfill and staff-only RLS, `item_exposures`, `skill_bank_state`,
global default-deny `worker_state`, and course bank flags. `generated_items.set_id`
and its existing kind check are unchanged.

## Terraform plan

`terraform validate` passed. Plan was run with `-input=false -no-color` and was
not applied. Full output:

```text
data.aws_iam_policy_document.scheduler_assume: Reading...
data.aws_caller_identity.current: Reading...
data.aws_iam_policy_document.lambda_assume: Reading...
aws_cloudwatch_log_group.worker: Refreshing state... [id=/aws/lambda/kala-worker]
aws_cloudwatch_log_group.api: Refreshing state... [id=/aws/lambda/kala-api]
aws_ecr_repository.worker: Refreshing state... [id=kala-worker]
aws_secretsmanager_secret.app: Refreshing state... [id=arn:aws:secretsmanager:ap-southeast-1:945252182809:secret:kala/app-SbnDti]
aws_ecr_repository.api: Refreshing state... [id=kala-api]
aws_budgets_budget.monthly[0]: Refreshing state... [id=945252182809:kala-monthly]
aws_apigatewayv2_api.http: Refreshing state... [id=14vua0ys43]
data.aws_iam_policy_document.scheduler_assume: Read complete after 0s [id=52247394]
data.aws_iam_policy_document.lambda_assume: Read complete after 0s [id=2690255455]
aws_iam_role.scheduler: Refreshing state... [id=kala-scheduler-role]
aws_iam_role.lambda: Refreshing state... [id=kala-lambda-role]
data.aws_caller_identity.current: Read complete after 0s [id=945252182809]
aws_apigatewayv2_stage.default: Refreshing state... [id=$default]
aws_iam_role_policy_attachment.lambda_basic: Refreshing state... [id=kala-lambda-role-20260830180350209400000001]
aws_lambda_function.worker: Refreshing state... [id=kala-worker]
data.aws_iam_policy_document.lambda_extra: Reading...
aws_iam_role_policy.scheduler_invoke: Refreshing state... [id=kala-scheduler-role:kala-scheduler-invoke]
aws_scheduler_schedule.worker: Refreshing state... [id=default/kala-worker-schedule]
aws_lambda_function.api: Refreshing state... [id=kala-api]
data.aws_iam_policy_document.lambda_extra: Read complete after 0s [id=436583667]
aws_iam_role_policy.lambda_extra: Refreshing state... [id=kala-lambda-role:kala-lambda-extra]
aws_lambda_permission.apigw: Refreshing state... [id=AllowAPIGatewayInvoke]
aws_apigatewayv2_integration.api: Refreshing state... [id=1aa8mln]
aws_cloudwatch_metric_alarm.api_errors: Refreshing state... [id=kala-api-errors]
aws_apigatewayv2_route.proxy: Refreshing state... [id=i30hdlq]

Terraform used the selected providers to generate the following execution
plan. Resource actions are indicated with the following symbols:
  ~ update in-place

Terraform will perform the following actions:

  # aws_iam_role_policy.lambda_extra will be updated in-place
  ~ resource "aws_iam_role_policy" "lambda_extra" {
        id          = "kala-lambda-role:kala-lambda-extra"
        name        = "kala-lambda-extra"
      ~ policy      = jsonencode(
          ~ {
              ~ Statement = [
                    # (1 unchanged element hidden)
                    {
                        Action   = [
                            "bedrock:InvokeModelWithResponseStream",
                            "bedrock:InvokeModel",
                        ]
                        Effect   = "Allow"
                        Resource = [
                            "arn:aws:bedrock:ap-southeast-1:945252182809:inference-profile/*",
                            "arn:aws:bedrock:*::foundation-model/*",
                        ]
                        Sid      = "InvokeBedrock"
                    },
                  + {
                      + Action   = "lambda:InvokeFunction"
                      + Effect   = "Allow"
                      + Resource = "arn:aws:lambda:ap-southeast-1:945252182809:function:kala-worker"
                      + Sid      = "InvokeWorker"
                    },
                ]
                # (1 unchanged attribute hidden)
            }
        )
        # (2 unchanged attributes hidden)
    }

  # aws_lambda_function.api will be updated in-place
  ~ resource "aws_lambda_function" "api" {
        id                             = "kala-api"
        tags                           = {}
        # (28 unchanged attributes hidden)

      ~ environment {
          ~ variables = {
              + "WORKER_FUNCTION_ARN" = "arn:aws:lambda:ap-southeast-1:945252182809:function:kala-worker"
                # (2 unchanged elements hidden)
            }
        }

        # (3 unchanged blocks hidden)
    }

Plan: 0 to add, 2 to change, 0 to destroy.

Changes to Outputs:
  + worker_function_arn = "arn:aws:lambda:ap-southeast-1:945252182809:function:kala-worker"

─────────────────────────────────────────────────────────────────────────────

Note: You didn't use the -out option to save this plan, so Terraform can't
guarantee to take exactly these actions if you run "terraform apply" now.
```

## Verification

- API tests: **308 passed**, 29 warnings.
- Worker tests: **53 passed**.
- Terraform validation: **passed**.
- Scratch Postgres 16 + pgvector: **NOT VERIFIED**. Docker is installed but
  its daemon is unavailable, and no local PostgreSQL server is running. The
  migration was not applied to any database.
- Consequently, the requested live checks—single-application after 0020,
  backfill row-count equality, and student-JWT RLS isolation—remain pending.
  No production database or data was changed.
