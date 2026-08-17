# How Kala connects end to end

This is the map of how the pieces talk to each other. Read it once, then use the per-folder `CLAUDE.md` files for detail.

## The launch sequence (auth spine)

1. A student or instructor clicks the Kala link inside their LMS course. The LMS sends an OIDC third-party initiation to `POST/GET /lti/login` on the backend.
2. `/lti/login` generates state and nonce, stores them in a short-lived signed cookie, and redirects the browser to the platform's authorization endpoint.
3. The platform posts a signed `id_token` back to `POST /lti/launch`. The backend verifies the state cookie, verifies the token against the platform JWKS, and checks the nonce, message type, and deployment.
4. The backend resolves the tenant from `(iss, deployment_id)`, upserts the user, course, and enrollment in Supabase, then mints one session token (`app/security/jwt.py`) carrying `sub`, `institution_id`, and `app_role`.
5. The backend redirects into the SPA at `${FRONTEND_URL}/launch#token=...`. The SPA reads the token from the URL fragment, keeps it, and clears the fragment.

That one token is the whole auth story. The database RLS reads its claims, so the same token works for both the API and direct Supabase reads.

## Who calls whom

- The SPA (`apps/web`) calls the backend for actions (submit a diagnostic, ask the tutor) using the token as a bearer, and can read RLS-protected rows directly from Supabase with the same token.
- The backend (`services/api`) is the trusted writer. It holds the Supabase service-role key and writes evidence and twin state through `app/db/supabase.py`. It talks to Bedrock through `app/ai/`, always de-identifying first. It reads the LMS through `app/lms/`.
- The worker (`services/worker`) runs on a schedule, recomputes the twin from the append-only evidence log, and re-embeds changed content into pgvector. It never sits in the request path.

## The data path for one diagnostic

`DiagnosticPanel` (frontend) calls `GET /courses/{id}/diagnostic`. The backend reads the course skills and returns questions. The student answers; the frontend calls `POST /courses/{id}/diagnostic/submit`. The backend writes one `evidence_events` row per answer (service role, append-only) and updates `mastery_state` through `app/twin/tracer.py`. The `twin` feature later reads that mastery back through RLS.

## The tenancy and identity contract

A tenant is an LMS deployment. Every persisted row carries `institution_id`. The token's `institution_id` and `app_role` claims are the only source of tenancy and role; nothing trusts client-supplied values. This contract is enforced twice: by the backend (which sets them from the validated launch) and by Postgres RLS (which reads them from the token).

## Types stay in sync

The backend emits an OpenAPI schema (`python scripts/export_openapi.py` writes `openapi.json`). The frontend generates its API types from it (`pnpm gen:api`). Do not hand-write API types on either side.

## Deploy pipeline

Build the two container images, push them to ECR, then apply Terraform in `infra/terraform`, which stands up the API behind an HTTP API Gateway, the worker on an EventBridge schedule, Secrets Manager, IAM, and CloudWatch. See `infra/terraform/README.md`. After the first apply, take the API base URL from the Terraform output and use `<api_base_url>/lti/launch` as the redirect and `<api_base_url>/lti/jwks` as the tool JWKS when you register in the Anthology Developer Portal.
