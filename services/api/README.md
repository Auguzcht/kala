# services/api — Kala backend (FastAPI)

Request-path backend. Runs locally with uvicorn and on AWS Lambda (container image) behind API Gateway. Read `docs/BACKEND.md` for how the whole system connects, and the root `CLAUDE.md` for the rules.

## Run locally
Managed with [uv](https://docs.astral.sh/uv/). Installs Python and the venv for you, no manual `python -m venv` step.
```
uv sync
cp .env.example .env   # fill in values
uv run uvicorn app.main:app --reload --port 8000
```
`requirements.txt` is kept in sync from `uv.lock` (`uv export --no-hashes --no-dev -o requirements.txt`) purely so the Lambda container build below can stay on plain `pip`. Don't hand-edit it, regenerate it after changing `pyproject.toml`.

## Export the OpenAPI schema (frontend types)
```
python scripts/export_openapi.py    # writes openapi.json
```
Then from apps/web: `pnpm gen:api`.

## What is here
- `app/main.py` — app, routers, CORS, Lambda handler.
- `app/config.py` — settings (env or AWS Secrets Manager).
- `app/security/jwt.py` — mint and verify the Supabase-compatible session token.
- `app/lti/` — LTI 1.3 login + launch (the auth spine).
- `app/db/` — Supabase access (service role).
- `app/lms/` — LMS connector interface + Blackboard + Canvas.
- `app/ai/` — Bedrock model router, de-identification, RAG.
- `app/twin/` — mastery tracer and readiness.
- `app/routers/` — feature endpoints.

## Deploy
Build and push the image, then apply Terraform in `infra/terraform`. See that folder's README.
