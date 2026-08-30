# Convenience targets. Adjust ACCOUNT/REGION or pass them in.
# Uses the workspace-local AWS CLI and Terraform installed by `pnpm setup`.
REGION ?= ap-southeast-1
AWS ?= aws
TF ?= pnpm terraform
ACCOUNT ?= $(shell $(AWS) sts get-caller-identity --query Account --output text)
ECR = $(ACCOUNT).dkr.ecr.$(REGION).amazonaws.com

.PHONY: web-dev api-dev openapi ecr-login build push tf-init tf-plan tf-apply

web-dev:
	pnpm --filter web dev

api-dev:
	cd services/api && uvicorn app.main:app --reload --port 8000

openapi:
	cd services/api && python scripts/export_openapi.py && cd ../../apps/web && pnpm gen:api

ecr-login:
	$(AWS) ecr get-login-password --region $(REGION) | docker login --username AWS --password-stdin $(ECR)

build:
	docker build --platform linux/amd64 --provenance=false --sbom=false -t $(ECR)/kala-api:latest services/api
	docker build --platform linux/amd64 --provenance=false --sbom=false -t $(ECR)/kala-worker:latest services/worker

push: ecr-login build
	docker push $(ECR)/kala-api:latest
	docker push $(ECR)/kala-worker:latest

tf-init:
	$(TF) -chdir=infra/terraform init

tf-plan:
	$(TF) -chdir=infra/terraform plan

tf-apply:
	$(TF) -chdir=infra/terraform apply
