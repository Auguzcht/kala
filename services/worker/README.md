# services/worker — Kala async worker

EventBridge-scheduled worker, not in the request path. Read `docs/BACKEND.md` for how it fits with `services/api`, and `CLAUDE.md` in this folder for the rules.

## Run locally
Managed with [uv](https://docs.astral.sh/uv/).
```
uv sync
cp ../api/.env.example .env   # same Supabase + AWS values as the api service
uv run python -c "from app.handler import handler; handler({}, None)"
```
`requirements.txt` is kept in sync from `uv.lock` for the Lambda container build (see Dockerfile). Regenerate it with `uv export --no-hashes --no-dev -o requirements.txt` after changing `pyproject.toml`, don't hand-edit it.

## What is here
- `app/handler.py` — `handler(event, context)`, the entry point EventBridge invokes.

## Deploy
Build and push the image, then apply Terraform in `infra/terraform`. See that folder's README. Schedule lives in `infra/terraform/eventbridge.tf`.
