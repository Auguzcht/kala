# Deploying the Kala backend on AWS

This stack deploys the FastAPI backend (Lambda container behind an HTTP API Gateway), the async worker (Lambda on an EventBridge schedule), Secrets Manager, IAM (least privilege), and CloudWatch.

## Prerequisites

- Terraform >= 1.6, AWS CLI, Docker.
- Access to the target AWS account. Two cases:
  - The school gives you a cross-account role in their AWS Organization: put its ARN in `assume_role_arn`. Your local credentials assume that role.
  - The school gives you a standalone account (or you create one with the needed permissions): leave `assume_role_arn` empty and authenticate with a profile or environment credentials.
- Bedrock enabled in the target region, with model access approved for the models you plan to use. Confirm the exact model ids before setting them in the app secrets.

## One-time bootstrap

```
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # edit values
terraform init
terraform apply -target=aws_ecr_repository.api -target=aws_ecr_repository.worker
```

This creates the two ECR repositories first, so you have somewhere to push images.

## Build and push the images

From the repo root (adjust account and region):

```
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=ap-southeast-1
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$REGION.amazonaws.com

docker build -t $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/kala-api:latest    services/api
docker build -t $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/kala-worker:latest services/worker
docker push $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/kala-api:latest
docker push $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/kala-worker:latest
```

Put those image URIs into `terraform.tfvars` (`api_image_uri`, `worker_image_uri`).

## Set the application secrets

Secrets never live in Terraform state. After the first apply creates the secret, put the values in:

```
cat > secrets.json <<'JSON'
{
  "SUPABASE_URL": "https://YOUR-PROJECT.supabase.co",
  "SUPABASE_SERVICE_KEY": "...",
  "SUPABASE_JWT_SECRET": "...",
  "BEDROCK_MODEL_TIER1": "...",
  "BEDROCK_MODEL_TIER2": "...",
  "BEDROCK_EMBED_MODEL": "...",
  "LTI_CLIENT_ID": "...",
  "LTI_AUTH_LOGIN_URL": "...",
  "LTI_AUTH_TOKEN_URL": "...",
  "LTI_KEYSET_URL": "...",
  "LTI_DEPLOYMENT_IDS": "...",
  "LTI_TOOL_PRIVATE_KEY_PEM": "-----BEGIN PRIVATE KEY----- ..."
}
JSON
aws secretsmanager put-secret-value --secret-id kala/app --secret-string file://secrets.json
rm secrets.json
```

The backend loads these at cold start via `KALA_SECRETS_ARN` (see `app/config.py`).

## Apply the full stack

```
terraform apply
```

Take `api_base_url` from the output. Your LTI redirect URI is `<api_base_url>/lti/launch`, and the tool JWKS is `<api_base_url>/lti/jwks`. Use these when registering in the Anthology Developer Portal.

## Notes

- The API Lambda should be kept warm enough that the LTI launch handler responds quickly. Add provisioned concurrency if cold starts hurt the launch.
- Redeploys after a code change: rebuild and push the image, then `terraform apply` (or update the function to the new image tag).
- To hand this to the school's IT for review, everything is declarative here; the only manual step is the secret value, by design.
