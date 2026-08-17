# apps/web — Kala frontend (React + Vite)

The product UI. Read `docs/stack.md` for the frontend decisions and this folder's `CLAUDE.md` (plus the per-feature `CLAUDE.md` files) for the rules.

## Run locally
Managed with [pnpm](https://pnpm.io) workspaces, run from the repo root or from here.
```
pnpm install
cp .env.example .env.local   # fill in Supabase + API base URL
pnpm dev
```

## Scripts
```
pnpm dev         # Vite dev server
pnpm build       # production build (tsc -b && vite build)
pnpm lint        # eslint
pnpm typecheck   # tsc --noEmit
pnpm gen:api     # regenerate src/lib/api/types.gen.ts from services/api's OpenAPI export
```

## What is here
See the repo root `CLAUDE.md` for the full layout. Start with `src/app` (router, providers), `src/features` (feature-first modules), and `src/styles/DESIGN.md` before any UI work.
