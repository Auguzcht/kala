# Convenience targets. Adjust ACCOUNT/REGION or pass them in.
REGION ?= ap-southeast-1
ACCOUNT ?= $(shell aws sts get-caller-identity --query Account --output text)
ECR = $(ACCOUNT).dkr.ecr.$(REGION).amazonaws.com

.PHONY: web-dev api-dev openapi ecr-login build push tf-apply

web-dev:
	pnpm --filter web dev

api-dev:
	cd services/api && uvicorn app.main:app --reload --port 8000

openapi:
	cd services/api && python scripts/export_openapi.py && cd ../../apps/web && pnpm gen:api

ecr-login:
	aws ecr get-login-password --region $(REGION) | docker login --username AWS --password-stdin $(ECR)

build:
	docker build -t $(ECR)/kala-api:latest services/api
	docker build -t $(ECR)/kala-worker:latest services/worker

push: ecr-login build
	docker push $(ECR)/kala-api:latest
	docker push $(ECR)/kala-worker:latest

tf-apply:
	cd infra/terraform && terraform apply
