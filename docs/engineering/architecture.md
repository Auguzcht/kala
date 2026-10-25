# Runtime and state ownership

Kala is an intelligence layer over Blackboard Learn, not a course host. Blackboard owns course content and grades; Supabase owns learning evidence. This source map reflects [AGENTS.md](../../AGENTS.md) and the current manifests, not the historical Next.js proposal.

| Boundary | Current implementation | Owner |
| --- | --- | --- |
| Browser | React/Vite SPA on Vercel; routes in `apps/web/src/app/router.tsx` | TanStack Query for server data, session for auth, Zustand for ephemeral UI |
| Login | Blackboard LTI 1.3 to FastAPI, validated session returned to SPA | [LTI auth spec](../features/lti-auth/README.md) |
| API | `services/api`, FastAPI on AWS Lambda behind HTTP API Gateway | Auth, tenant/owner checks, bounded request work |
| Scheduled work | `services/worker`, EventBridge-scheduled Lambda | Resumable ingest, bank building, mastery/readiness jobs |
| Storage | Supabase Postgres with pgvector and private attachment storage | [Database policy](database.md), feature schemas and RLS |
| Models | Provider router in `services/api/app/ai/` | [AI platform](../features/ai-platform/README.md); partial sanitization |

Feature code stays in its feature and exposes a small public `index.ts` surface. App-wide hooks belong in `src/hooks`; imported API types are generated from OpenAPI. API and worker use separate uv projects/locks and separate test processes. There is no implemented shared `packages/ui` installation workflow: frontend primitives live under `apps/web/src/components`. [DESIGN.md](../../apps/web/src/styles/DESIGN.md) governs tokens and narrow dock/mascot exceptions.

Use [local development](local-development.md) for commands and test limitations, [runbooks](runbooks/README.md) for operations, and [feature registry](../features/README.md) for current contracts. Planned admin, research and AGS surfaces are not shipped capabilities. Never infer hosted readiness from a source diagram or a local test.
