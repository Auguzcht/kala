# APPROVAL-06 coordinator integration evidence

Date: 2026-10-25. Environment: local. Coordinator checkout: /Users/fred/Documents/Repository/kala, branch main. Authority: [APPROVAL-06](../approval-06.md). Published comparison base: 4f3ec29. Existing main descended from cab26de with approved documentation; it was preserved, not reset.

## First integration pass

| Exact approved lane revision | Local merge | API | Worker | Frontend | Study component |
| --- | --- | --- | --- | --- | --- |
| X 7f484bb | 1426ea2 | 515 passed | 117 passed | 14 passed | 4 passed |
| B 0ccbb22 | 460804e | 548 passed | 117 passed | 14 passed | 4 passed |
| U e1b0250 | 5afe69518bf51c728a76753527f1682d64041d71 | 548 passed | 117 passed | 21 passed | 4 passed |

Every row also passed web lint, typecheck, build and config_inventory --check. Existing lint warnings (18), dependency deprecations and bundle-size warnings remain; no new success claim is made for live providers. X verification overlapped the documentation-only ownership commit f2c30eb; application source was unchanged during that run.

Commands: each service runs `uv run pytest` in its own directory under committed services/conftest.py (dotenv disabled, generated fake signing key, sockets blocked). Frontend uses Node --test over checked-in *.test.ts/*.test.mjs files; Study uses `node --experimental-vm-modules --test apps/web/src/features/flashcards/tests/study-deck.test.mjs` with KALA_STUDY_TEST_DEPS=/private/tmp/kala-lane-f-renderer. Then `pnpm --filter web lint`, `typecheck`, `build`, and `uv run --project services/api python scripts/config_inventory.py --check`. The external renderer remains a WI-20 limitation; no dependency added. Raw logs: /tmp/kala-approval06-checks/merge-x, merge-b and merge-u.

Three browser suites ran against main 5afe695 on the sole strict-port Vite server at localhost:5173: Tutor/Diagnostic 219 assertions, Twin 148, instructor feedback 63, all passed. Synthetic authenticated fixtures intercepted API traffic and blocked external traffic; these are not Blackboard/Lambda acceptance. Commands: node apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs; node apps/web/src/features/twin/tests/presentation.browser.mjs; node apps/web/src/features/instructor/tests/review-feedback.browser.mjs. Bundled Playwright/Chrome supplied through KALA_BROWSER_TEST_DEPS and KALA_BROWSER_EXECUTABLE. Logs/screenshots: /tmp/kala-approval06-checks/initial-browser. Coordinator stopped its own Vite PID32455 and returned port5173 to U afterwards.

Migration/infra scope: `git diff --name-status 4f3ec29..5afe695 -- packages/db/migrations supabase/migrations infra/terraform` contains only added packages/db/migrations/0037_tutor_conversation_pin.sql. Historical SQL unchanged; no Terraform change. 0037 checksum: 82c9297ea08b4c16c3ba03bb2cc64eb222e67dd4276e9b4f7a8db22efe873450. Real local SQL verification is in [0037 runbook](../../../runbooks/0037-apply.md); hosted application remains FG-3.

## Coordinator reconciliation and generation

Committed G spec009–011 separately at1af50f1 and U spec012–013/cross-surface recovery separately at3128e2c before releasing affected implementation. I's explicit UUID/removal guard policy is recorded at992dae2. Auth implementation retains removals after a complete non-empty fetch; additive sync is rejected. Historical duplicate users retain history; [WI-24](../work-items/WI-24-dev-identity-history-repair.md) stays planned.

Tutor/AI/DESIGN reconciliation follows the accepted e1b0250 handoff and APPROVAL-06 section2: starters retired, memory-only attachments until Send, resizable history, scoped visual/interaction refinements, diagnostic logging implemented locally, and honest20/25-event windows. Lead designer and live acceptance remain pending.

OpenAPI export executed in a fresh Python process after loading the committed services/conftest.py isolation, then scripts/export_openapi.py; no dotenv or live service access. Regenerated web types with pnpm --filter web exec openapi-typescript ../../services/api/openapi.json -o src/lib/api/types.gen.ts. Compared parsed OpenAPI against pre-generation main: sole semantic change is an existing flashcards deck description correction; other JSON changes are ordering. Full type regeneration also resolves older generated-type drift (existing memory-summary, retake/results and card-browse routes), with no runtime source/route change. B's PATCH/list contracts match regenerated source. Web typecheck/build rerun after generation.

## Remaining gates and lane state

I/G/U close-out implementation runs independently on owned branches and returns complete audits before merge. R/P/C2 documentation reports have been read; P's Twin/Instructor requirement IDs overlap accepted U presentation IDs and require deliberate reconciliation, with auth held for I. DB awaits FG-2. These are not evidence of deployment readiness.

FG-1 paid fallback/runtime refresh and live hint recovery: pending Fred. FG-2 hosted PG major: pending Fred. FG-3 migration0037: pending Fred. FG-4 deploy/push and FG-5 role/feature/viewport acceptance: pending Fred. No hosted mutation, deployment, push, key rotation or historical identity repair performed. Secrets printed: none.
