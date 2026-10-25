# AGENTS.md: Kala repository instructions

This file is the entry point for every coding agent (Codex, Claude) and every new maintainer. It is a router. It says what Kala is, the rules that never bend, and where the authority for each kind of question lives. `CLAUDE.md` contains one line pointing here. Current operational authority is this router, [the documentation guide](docs/README.md), the selected current feature spec, and the applicable engineering runbook. Initiative approvals and evidence are records; durable constraints are stated here and in those current documents.

## 1. Start here

```text
AGENTS.md
  -> docs/README.md (Task Router)
  -> the selected feature spec in docs/features/<feature>/README.md
  -> the selected work item in docs/work/<initiative>/
  -> source and tests
```

Do not read docs/archive/** or docs/work/**/evidence/** unless the task explicitly names them.

Do not pick requirements or next steps from file dates, search ranking, old session recaps or chat history. If the task does not name a feature or work item and more than one fits, stop and ask.

## 2. What Kala is

Kala is an AI learning companion and digital learning twin that runs as an intelligence layer on top of the LMS. Users enter through an LTI 1.3 link in Blackboard Learn. Kala never hosts courses. The LMS is the source of truth for content and grades. Supabase is the source of truth for learning evidence.

Runtime: React and Vite SPA on Vercel, FastAPI on AWS Lambda behind HTTP API Gateway, an EventBridge-scheduled worker Lambda, Supabase Postgres with pgvector, model calls through the provider router in `services/api/app/ai/`.

## 3. Spec-first rule

1. Feature specs in `docs/features/` define intended behavior. Code and tests show observed behavior. A difference is investigated, never silently resolved either way.
2. A change to intended behavior updates the spec first, in the same branch, with the affected `REQ` IDs and an entry in the spec's change log. Implementation follows the spec.
3. A bug fix that restores behavior the spec already describes does not change the spec. It adds an evidence entry instead.
4. If the spec itself was wrong, fix the spec first, then the code.
5. Every PR names the `REQ` and `WI` IDs it touches.

## 4. Golden rules (unchanged from the original build)

1. Multi-tenant always. Every persisted row carries `institution_id`, resolved from the LTI launch (`iss` + `deployment_id`). Isolation is enforced by Postgres RLS.
2. Auth comes from the LMS. Never trust a client-supplied `institution_id` or `role`.
3. State has one owner. Server data in TanStack Query, auth in the session, ephemeral UI in Zustand.
4. De-identify before any model call. Student learning data is personal data under the Philippine Data Privacy Act.
5. No secrets in the client. Only `VITE_*` public values reach the browser.
6. Validate at the boundary with Pydantic and Zod. Frontend API types are generated from OpenAPI.
7. Design tokens only. See `apps/web/src/styles/DESIGN.md`.

## 5. Secrets rule

- Never print, paste, log or commit a secret value. Report only whether a variable is set and, for URLs, the host.
- Never read `.env` files aloud into a chat, a report or a doc.
- The only list of secrets is `docs/engineering/secrets.md`, which holds names, stores and owners, never values.

## 6. Database rule

- Migrations are forward only. Never edit a migration that has been applied to any hosted environment, including comments. APPROVAL-01 keeps the numeric filenames unchanged; Lane DB moves SQL byte for byte with checksum proof. Keep the historical old-path comment in 0036. Fix forward with a new file.
- Every new SQL function or statement runs once against a real local Postgres (local Supabase) before it counts as done. Mocked tests are not enough.
- Production migrations are applied by the maintainer, never by an agent, after review. Each has a runbook entry with pre-checks and post-checks.

## 7. Production rule

Agents never deploy, apply migrations, rotate keys or write to hosted data. They prepare the change, the runbook and the checks. A named human runs it and records evidence. Do not change infrastructure (Terraform, Vercel config, Docker, CI, Lambda, EventBridge) unless the task explicitly asks.

## 8. Parallel work with git worktrees

- One task per worktree, one branch per worktree, prefix `codex/`.
- Each task owns a disjoint set of paths, named in its brief. Do not edit outside them.
- Narrow shared-file exception: one lane may make a comment-only edit while another makes an attribute-only or comment-only edit on non-overlapping lines. Merge in sequence; the second lane rebases, proves both edits survive and verifies the executable diff contains only the approved attribute (or no executable change when both edits are comments). Rerun its relevant tests and web checks after the rebase. Any other shared-file change stops for planner resolution.
- Smoke test from the worktree that changed. Only one dev server on port 5173 at a time (the API CORS allows only that origin).
- Never `git pull --rebase` when `main` has merge commits. Fetch, confirm `origin/main` has not moved, push fast-forward.

## 9. Every agent task ends with this block

```text
AUDIT REPORT
Task / brief ID:
Branch and worktree:
Base revision:
Files changed:
REQ / WI IDs touched:
Commands run and results (tests, lint, typecheck, build):
Spec changes made (or "none"):
Evidence added (or "none"):
Anything not done, and why:
Risks or questions for the planner:
Secrets printed: none (confirm)
```

## 10. Source-adjacent conventions carried forward

- Before editing an area, read its local `CLAUDE.md` if one exists, then follow the [task router](docs/README.md). Missing historical guides are recorded in the inventory; do not assume a template folder exists.
- Feature-first: feature-specific components, hooks, API clients and schemas stay in that feature. Expose a small `index.ts` public surface; import another feature through its public surface rather than its internals. App-wide hooks belong in `src/hooks`.
- Use the `@/` import alias in the web app. Keep components focused; split components that grow beyond a few hundred lines.
- UI copy is sentence case; buttons name the action. Use [DESIGN.md](apps/web/src/styles/DESIGN.md) for all visual rules. Keyboard focus, mobile layouts and reduced motion are part of done.
- Auth/session belongs to Supabase/the validated session. The LTI path has no separate password signup. Backend identity and tenancy come from validated tokens, not client role/tenant claims.
- API and worker use uv with their own `pyproject.toml` and `uv.lock`. `requirements.txt` is a generated Lambda export (`uv export --no-hashes --no-dev -o requirements.txt`), never hand-edited.
- Model calls must de-identify first. The existing sanitizer covers only emails and `name:` patterns; broader protection remains partial and planned. Never describe it as comprehensive anonymization.
- Before creating a feature, write its spec from [the feature template](docs/engineering/documentation/templates/feature-spec.md), then implement the scoped public surface and register routes in `src/app/router.tsx`.

## 11. Commands

See `docs/engineering/local-development.md` for the full list. The common ones:

```sh
pnpm setup
pnpm dev                     # web on :5173
pnpm api:dev                 # api on :8000
pnpm --filter web gen:api    # OpenAPI export + frontend types
pnpm --filter web lint && pnpm --filter web typecheck && pnpm --filter web build
cd services/api && uv run pytest
cd services/worker && uv run pytest
```

## 12. Documentation checks

Use Python 3.10 or newer. Run `python3 scripts/docs_check.py` and `python3 -m unittest discover -s scripts -p 'test_docs_check.py'` for documentation changes. The checker covers tracked and non-ignored new text files under docs/ plus this router. Links from current truth documents into archive/evidence belong only under Historical sources or Verified by headings, or in an explicit Verified by requirement field. Fenced examples are not live links. Machine-local paths must become repo-relative references or carry the exact marker “local only, not retained” on their line. Ignored local originals are audited separately and never silently promoted.

For comment-only edits, compare executable AST/token streams before and after. Applied migrations remain byte-for-byte immutable, including comments; preserve a current pointer at their retained documentation target instead. Stop at the audit report before merge or push.

## Historical sources

The accepted handover decisions were recorded in [APPROVAL-01](docs/work/handover-2026/approval-01.md), [02](docs/work/handover-2026/approval-02.md), [03](docs/work/handover-2026/approval-03.md), [04](docs/work/handover-2026/approval-04.md), [05](docs/work/handover-2026/approval-05.md) and [06](docs/work/handover-2026/approval-06.md). Read them only when a task names the record; do not derive new requirements or release status from them. Documentation hygiene is the user-approved docs-only freeze exception.
