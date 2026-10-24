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

## Final local integration — 2026-10-25

The first-pass results above are preserved history. Coordinator reviewed complete refreshed reports and merged the close-out code in the required order:

| Lane | Accepted revision | Local merge | Review and limits |
| --- | --- | --- | --- |
| I identity | 15fefa1ccee5268a8935f99ae396abb9b9b1271f | 44079a8 | 579 lane API/117 worker; 31 dedicated scenarios, 103 focused; real local Postgres/PostgREST persistence check. Complete non-empty fetch/member success required before removals. Auth spec/evidence retained. No history repair or hosted validation. |
| G availability | 9bc8479965fa8309e74e9e3692ee6653e9114cf2 | d70698a | Final lane API579, 31 dedicated cases; 21 real local REST query checks. Earlier574 result superseded by additional edge-case coverage. Full eligible-pool/history scans and snapshot/page-cap limitations remain documented. |
| U close-out | db2bb75437437f35bf3fadde13ae0605957fab6d | 8bc569e | H05–H11, H12 and legacy/count compatibility; 110 new and430 retained browser assertions,21 frontend+4 Study tests. No backend/identity data repair. |
| C2 configuration/cost docs | a4ae528b4450b7ff171cd69962ef8325c42d63b1 | 9f86fb0 | Names-only precedence evidence, exposure log preserved; cost inputs remain unpriced placeholders. Config inventory check passed after merge. |
| R runbooks | 74345ac31466f6f5ae07035d12ad248e84bcf7b0 | 31b9e50 | 13 procedures/15 files;187 links/one anchor, six shell syntax blocks and Python syntax validated. All execution-unverified; hosted/bootstrap unknowns remain explicit. |
| P feature specs | 46ace47a2baba88bcd22f8c006ce8fa1f6b2a51f | merge recorded in Git after4a6ccac | Eight changed specs;50 requirements:37 implemented,11 partial,two planned. Accepted presentation IDs and Lane S requirement preserved. Auth byte-identical to I/main. Explicit draft-ID mapping resolves Twin/Instructor collisions. Docs checks pass; historical runtime results not reused as current acceptance. |

### Combined checks

Runtime integration base:8bc569e36b52488b4e05202a90cb18c8ba0db589. Generated files refreshed under shared isolation during this run; the sole resulting change was the Diagnostic status description, committed at40720dd. No runtime edits followed the checked source. Subsequent changes are reviewed documentation only.

- Full API: **610 passed**,30 existing dependency warnings,27.99s pytest time.
- Worker: **117 passed**.
- Frontend Node: **21 passed**; Study component tests: **4 passed** with the existing external renderer fixture.
- Web lint/typecheck/build: **passed**;18 existing Fast Refresh warnings, route-generator circular warning and bundle-size warning remain.
- config_inventory --check: **passed**.
- Browser suites against the one main5173 server: Tutor/Diagnostic **219**, Twin **148**, instructor **63**, close-out **110** assertions: **540 passed** total. APIs/auth were synthetic and non-local traffic blocked. These counts are not live acceptance.
- Scope: only added0037 under migration paths versus published4f3ec29; no historical migration or infra/terraform file changed. `git diff --check` passed.

Logs: /tmp/kala-approval06-checks/combined-main, combined-browser and combined-closeout.log. Captures: combined-browser/screenshots and combined-closeout-screenshots. Commands remain those in the first-pass section, plus `node apps/web/src/features/diagnostic/tests/frontend-closeout.browser.mjs` with the same browser environment. Inspected first-pass Tutor desktop/Diagnostic mobile captures; U inspected the required recovery views at375/1440. The coordinator's second VitePID38458 was stopped after final browser tests. U fast-forwarded its clean codex/ui-closeout branch to4a6ccac, restarted strict5173 asPID39396 and confirmed localHTTP200. Original codex/ui-overhaul remains e1b0250. No worktree cleanup before FG-5; Kala Audit retained.

### Findings still open

- [WI-24](../work-items/WI-24-dev-identity-history-repair.md): old dev identity histories remain split; no data merged. Alfred's older40 events remain outside the canonical roster until repair.
- [WI-25](../work-items/WI-25-full-history-evidence-paging.md):20/25-event windows disclosed, full history deferred.
- [WI-26](../work-items/WI-26-instructor-course-authorization.md): source-confirmed caller course-gate and direct recommendation visibility gaps; outside this approved code scope, not a production security sign-off.
- G's eligible-pool/history scan cost, missing typed Diagnostic OpenAPI response models, partial sanitizer coverage and existing planned timeout/observability/frontend-runner work remain.
- All13 runbooks need human execution evidence; account/plan/price/rollback setup unknowns remain. Lead designer review remains pending.
- DB still awaits FG-2. No hosted schema drift file was supplied in this round.

### Fred gates

FG-3 instructions were sent after first integration was green: exact0037 checksum, full runbook pre-checks, apply once, post-checks, rollback by retaining the additive column. No result is reported yet. FG-1 provider recovery, FG-2 PG major, FG-3 application, FG-4 deploy/push and FG-5 click-through remain unconfirmed. [Prepared live acceptance record](acceptance-2026-10-25.md) has only not-run/pending entries. No push, deployment, key rotation, hosted mutation or historical repair performed. Do not proceed past FG-3 without Fred's results.

## AUDIT REPORT

```text
Task / brief ID: APPROVAL-06 coordinator, H01–H12 integration and audit review
Branch and worktree: main; /Users/fred/Documents/Repository/kala
Base revision: published4f3ec29; first-pass runtime5afe695; combined runtime8bc569e
Files changed: approved X/B/U/I/G source and tests, generated API artifacts,
  shared specs/design, handover evidence/work items, reviewed R/P/C2 docs.
  Exact manifest: git diff --name-status 4f3ec29..main.
REQ / WI IDs touched: AUTH002/003/006; DIAG009–013 plus existing presentation;
  TUTOR002–011; AI002; TWIN/INSTR presentation and mapped P requirements;
  WI01/05/06/07/08/21/22/24/25/26.
Commands run and results:610 API,117 worker,21 frontend,4 Study,540 browser
  assertions passed; lint/typecheck/build/config inventory/diff checks passed.
Spec changes made: separate G/U spec commits before release; accepted Tutor/AI/
  DESIGN reconciliation; honest windows; preserved auth and presentation IDs.
Evidence added: this report, lane audits, real-local fixture evidence,
  prepared not-run live acceptance record and explicit remaining work.
Anything not done, and why: Fred gates pending; no deploy/push/hosted writes,
  migration application, rotation, historical identity repair or cleanup.
Risks or questions for planner: FG-3 results required; provider/live acceptance
  unverified; WI-26 security findings and G query-scaling limits remain open.
Secrets printed: none (confirmed).
```

## Subsequent read-only provider and migration checks

On2026-10-25 Fred requested current model-state verification and0037 pre-checks. [Dedicated evidence](provider-and-0037-prechecks-2026-10-25.md) records actual account credit, endpoint availability, shared hint/Tutor routing, successful target-table pre-checks, PG17.6 and the incomplete hosted migration-history finding. This supersedes only the earlier “pre-checks not performed” state; model configuration, migration application/post-checks, deployment and live acceptance remain pending. No runtime files changed or suites rerun.
