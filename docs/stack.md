# Kala Stack Decisions

Companion to `masterplan.md`. This document is authoritative for frontend and development-stack choices and supersedes any framework mention in the masterplan. ADR-style: each decision records the choice and why.

---

## Context

- Kala's frontend is auth-gated behind an LTI launch and internal. No SEO requirement.
- The backend is a separate FastAPI service (Lambda). The frontend does not need server-side rendering or server-side data functions.
- The team is comfortable and fast in React + Vite with a feature-first folder structure.
- The product is multi-tenant (one tenant per LMS deployment) and may become a startup product (Sayon Ventures), so decisions should preserve that path cheaply.

---

## Decision 1: React + Vite SPA (not a meta-framework)

**Choice:** Build the app as a React + Vite single-page app.

**Why:**
- "Multipage" does not require SSR. Client-side routing serves as many pages as needed.
- SSR only buys SEO and faster first paint on public pages; neither applies to an internal, auth-gated tool.
- A separate FastAPI backend means Next.js server features would go unused.
- Fast HMR and simple mental model suit the September timeline.

**Routing:** TanStack Router (Vite-native, best-in-class type safety for dashboard-heavy internal tools, integrates tightly with TanStack Query). React Router v7 data mode is an acceptable alternative if the team already knows it.

**SSR upgrade path (if production ever needs it):** TanStack Start (built on TanStack Router) or React Router v7 framework mode. Both are Vite-based, so SSR can be added in place without leaving Vite or rewriting. Starting as an SPA locks nothing out.

---

## Decision 2: Hosting

**Choice:** Host the static SPA on any static host. Vercel is fine; S3 + CloudFront or AWS Amplify keeps it inside the school-governed AWS org account.

**Why:** It is now a static SPA, so the host is a low-stakes, reversible choice. Keeping it in AWS simplifies governance and billing if that matters to the school.

---

## Decision 3: Package manager: pnpm (workspaces)

**Choice:** pnpm with workspaces for the monorepo (`apps/web`, `packages/*`).

**Why:** Best balance of speed, strict correctness, disk efficiency, and monorepo support; works on all CI and hosts. Bun is a valid faster alternative if desired; npm is the fallback but least ergonomic for workspaces. The backend is Python, so the JS package manager governs only frontend and shared JS packages.

---

## Decision 4: State management, split three ways

Each kind of state has exactly one owner. Do not let them overlap.

| State kind | Owner | Examples |
|---|---|---|
| Server / remote data | **TanStack Query** | courses, mastery, dashboards, evidence |
| Auth / session | **Supabase (signed JWT)** | current user, tenant, role |
| Ephemeral client / UI | **Zustand** (or `useState`/context) | open tab, in-progress practice, modals, gamification animation |

**Why:** The common anti-pattern is dumping database data into a global store. TanStack Query already caches and revalidates server data. Auth belongs to the session, not a store. Zustand is for client-only UI state, and you will often need very little of it.

```ts
// Zustand holds ONLY ephemeral UI state
import { create } from "zustand";

interface UIState {
  activeCourseTab: string;
  practiceSession: PracticeSession | null;
  setTab: (t: string) => void;
  setPractice: (p: PracticeSession | null) => void;
}

export const useUI = create<UIState>((set) => ({
  activeCourseTab: "overview",
  practiceSession: null,
  setTab: (t) => set({ activeCourseTab: t }),
  setPractice: (p) => set({ practiceSession: p }),
}));
```

```ts
// Server data goes through TanStack Query, never Zustand
const { data: mastery } = useQuery({
  queryKey: ["mastery", courseId],
  queryFn: () => api.getMastery(courseId),
});
```

---

## Decision 5: Auth pattern (LTI to Supabase-compatible JWT to RLS)

**Choice:** Auth originates from the LMS via LTI. FastAPI validates the launch, then mints a short-lived Supabase-signed JWT carrying the claims RLS needs. The frontend holds that session. For sensitive reads, broker through FastAPI rather than hitting Supabase directly from the client.

**Flow:**
1. LMS launch to FastAPI. Validate the LTI 1.3 launch (`pylti1.3`).
2. Upsert the user in the database; resolve the tenant from the launch (`iss` + `deployment_id`).
3. Mint a JWT signed with the Supabase JWT secret, with claims: `sub` (user id), `institution_id` (tenant), `role`, and course context.
4. Set it as a first-party session for the SPA (httpOnly cookie preferred).
5. RLS policies isolate data by `auth.uid()` and `institution_id`.

```python
# FastAPI: after LTI validation, mint a Supabase-compatible session JWT
import jwt, time

def mint_session(user_id: str, institution_id: str, role: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": "authenticated",         # Postgres role Supabase expects
        "app_role": role,                # student | instructor | admin
        "institution_id": institution_id,
        "iat": now,
        "exp": now + 60 * 60,            # short-lived
    }
    return jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
```

```sql
-- RLS: isolate every row by tenant, plus per-user where needed
create policy tenant_isolation on mastery_state
  for all
  using ( institution_id = (auth.jwt() ->> 'institution_id') );

create policy own_rows on evidence_events
  for select
  using ( user_id = auth.uid()
          and institution_id = (auth.jwt() ->> 'institution_id') );
```

**Alternative (more setup, cleaner long-term):** Supabase Third-Party Auth can natively trust an external issuer if that issuer signs JWTs asymmetrically and exposes an OIDC discovery URL with a `kid` header. Consider this later; the self-minted HS256 token is simpler for September. Confirm your project's current JWT signing-key settings before wiring either path.

---

## Decision 6: Validation with Zod, types from OpenAPI

**Choice:**
- Forms: React Hook Form + `@hookform/resolvers/zod`.
- Boundaries: parse untrusted API responses with Zod.
- Types: generate frontend TS types from FastAPI's OpenAPI schema (`openapi-typescript`) instead of hand-maintaining them.

**Why:** Pydantic (backend) and Zod (frontend) stay aligned without syncing two schemas by hand. FastAPI already emits OpenAPI, so the frontend type layer is generated, not duplicated.

---

## Decision 7: Multi-tenancy (tenant = LMS deployment)

**Choice:** Stay multi-tenant. A tenant is an LMS deployment, resolved from the LTI launch (`iss` + `deployment_id`), confirmed on the REST side by FQDN. Every row carries `institution_id`; isolation is enforced by RLS.

**Why:**
- Each institution's data must be isolated (privacy requirement and PDPA alignment).
- No tenant-onboarding UI is needed; LMS registration is the onboarding.
- Building this in now costs one column plus policies. Retrofitting later is a rewrite.
- This is what makes the Sayon Ventures productization path technically real, and it maps to the Cintana "scalability across institutions" criterion.

For September there is one live tenant (MMCM), but the schema and policies are tenant-aware from the first migration.

---

## Feature-first folder structure (frontend)

```
apps/web/src/
  app/                 # router setup, providers (Query, session), root layout
  features/
    diagnostic/        # components, hooks, api, schema (Zod) for this feature
    practice/
    tutor/
    flashcards/
    twin/              # student mastery / readiness views
    instructor/        # class heatmap, at-risk, drill-down
    gamification/
  lib/
    api/               # generated types (from OpenAPI) + fetch client
    auth/              # session access, thin read-only auth context
    supabase/          # client init
  components/          # shared UI primitives
  stores/              # Zustand (ephemeral UI only)
```

Each feature folder owns its components, hooks, API calls, and Zod schemas. Shared primitives live in `components/`; cross-cutting concerns in `lib/`.

---

## Summary table

| Concern | Decision |
|---|---|
| Framework | React + Vite SPA |
| Routing | TanStack Router (React Router v7 data mode acceptable) |
| SSR path | TanStack Start / RR framework mode, both Vite-native, only if needed |
| Hosting | Vercel or AWS (S3+CloudFront / Amplify) |
| Package manager | pnpm workspaces |
| Server state | TanStack Query |
| UI state | Zustand (minimal) |
| Auth | LTI to FastAPI to Supabase-signed JWT to RLS |
| Validation | Zod + React Hook Form; types generated from OpenAPI |
| Tenancy | Multi-tenant, tenant = LMS deployment, `institution_id` + RLS |
