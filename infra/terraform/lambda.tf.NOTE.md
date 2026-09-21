# infra/terraform — what actually changes (almost nothing) and why

You asked "what credentials do you need, and since they're already in AWS
secrets, why not just access them." Here is the precise answer, confirmed
against the repo's own terraform:

## The worker ALREADY has the credentials. No new secret, no new IAM.

From `iam.tf` and `lambda.tf`:

- **Same role.** Both `aws_lambda_function.api` and `aws_lambda_function.worker`
  use `aws_iam_role.lambda`. Whatever the api can do, the worker can do.
- **Same secret, already readable.** The `lambda_extra` policy grants
  `secretsmanager:GetSecretValue` on `aws_secretsmanager_secret.app` (the
  `kala/app` bundle). The worker already has this permission today.
- **Same bundle, already loaded.** Both functions get
  `KALA_SECRETS_ARN = aws_secretsmanager_secret.app.arn`, and both call
  `_load_secrets_into_env()` at settings time. The worker already pulls the
  entire `kala/app` bundle into its environment on cold start — including the
  `LMS_REST_*` and `LTI_AUTH_TOKEN_URL` values, because the api put them there.

So the worker was never missing AWS access to the LMS credentials. It was
missing only two code-level things, both handled in this bundle:
1. the four/five field **declarations** in the worker's slim `config.py`
   (see `config.py.ADD_THESE_FIELDS.md`), and
2. the **connector** to use them (see `app/lms/blackboard.py`).

## Terraform changes required: NONE that are mandatory.

Because the secret already carries the LMS values, there is nothing to add to
`secrets.tf`, `iam.tf`, or the worker's `environment` block. The existing
`KALA_SECRETS_ARN` passthrough is sufficient.

## One OPTIONAL hardening you may want

Today all secrets live in the shared `kala/app` bundle and both Lambdas read the
whole thing. That is fine and is the current design. If you ever want to split
LMS credentials into their own secret so the api and worker read a narrower
bundle, that is a real change — but it is scope creep for this task and is NOT
needed to ship the async ingest. Noted so it is a conscious future choice, not
an oversight.

## Confirm before you rely on this

DeepSeek: verify the live `kala/app` secret actually contains `LMS_REST_BASE_URL`,
`LMS_REST_CLIENT_ID`, `LMS_REST_CLIENT_SECRET`, `LMS_VERIFY_TLS`, and
`LTI_AUTH_TOKEN_URL`. It must, because the api uses all of them, but confirm it
with a one-line check before the first worker walk rather than discovering a
missing key at runtime:

    aws secretsmanager get-secret-value --secret-id kala/app \
      --query SecretString --output text | python -c \
      "import sys,json; d=json.load(sys.stdin); print([k for k in \
      ('LMS_REST_BASE_URL','LMS_REST_CLIENT_ID','LMS_REST_CLIENT_SECRET',\
      'LMS_VERIFY_TLS','LTI_AUTH_TOKEN_URL') if k in d])"
