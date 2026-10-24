# Lane R draft verification — WI-06 / WI-07

The initial record below describes the 4f3ec29 draft. The appended APPROVAL-06 refresh supersedes its current-state statements about migration count, B status, approval location and provider diagnostics; the old validation/source record is retained as historical evidence.

Date: 2026-10-25 (Asia/Manila). Approval: APPROVAL-05 rev 2 supplied as the task attachment. Base: `4f3ec29d3f827a1db92e90c4f395947d37744479`. Branch: `codex/handover-runbooks`. Worktree: `/Users/fred/.codex/worktrees/97b5/kala`.

## Scope and result

Drafted all 13 registered runbooks, prioritizing 03, 04 and 08, and revised the registry. Existing 02/07 partial extracts are expanded, with their extraction history preserved. **All 13 remain execution-unverified.** Unknowns are marked `[Fred to confirm]`, not filled from parent-chat history or imagined setup transcripts. No feature behavior or requirement was changed.

Write ownership is only this directory. No overlapping write path was identified: B owns its separate migration/apply note, DB owns the local workflow, and C2 owns the catalogue/infrastructure-requirements edits. No files in those paths were edited. No other worktree, existing Audit chat, dev server or port was changed. The lane uses the assigned worktree and creates only its own branch; no subagent or new chat was created here.

`git merge-base --is-ancestor cab26de 4f3ec29` passed. `git diff --stat cab26de..4f3ec29` showed only the handover README and dated deployment-evidence document. This verifies the requested current-main ancestry exception. No fetch, merge, push or deploy was performed.

## Source review

Read AGENTS.md, root CLAUDE.md, docs/README.md, documentation template/contract, WI-06/WI-07 in the handover initiative, APPROVAL-01 through 04 and the whole supplied APPROVAL-05 rev 2. No closer CLAUDE.md exists under docs/engineering/runbooks/. Read relevant infra/API/worker/database routing guides, READMEs, committed configuration/source, LTI/security/connector/tests, archived MEMORY/closeout, migration replay/apply notes, incident records and v6 evidence. Historic material supplies evidence only; current approvals/source establish constraints.

Read the Supabase skill from `/Users/fred/.agents/skills/supabase/SKILL.md` during authoring. The skill's generic guidance does not override the accepted Kala migration policy. Consulted official [Supabase environment guidance](https://supabase.com/docs/guides/deployment/managing-environments), changelog and [Postgres minor-release note](https://supabase.com/changelog/postgres-15-19-17-11-breaking-changes), plus official AWS CLI references linked in 13. Public references check documented interfaces, not current hosted state.

No dotenv file, secret payload, Terraform state/tfvars, parent-chat history or credential store was opened. Read-only source inspection never called an application settings loader or live provider. Historic source previews were filtered for credential-like lines; no raw provider payload was copied into these drafts.

## Evidence Fred must supply

| Runbook | Blocking evidence / decision |
| --- | --- |
| 01 | [Fred to confirm] institutional role/region, state backend and restore ownership, budget recipient, actual concurrency quota/allocation. |
| 02 | [Fred to confirm] hosted Postgres major, accepted Lane DB workflow/two clean verification runs, fresh-project manifest application/history method and RLS/application acceptance. Current path stays `packages/db/migrations`, 36 files; 0037 is pending B work. |
| 03 | [Fred to confirm] school test access or supported VMDK/licence/expiry/checksum; import manifest, IAM/boot/storage/size, stable address/DNS/TLS and synthetic enrollment screenshots. |
| 04 | [Fred to confirm] current Portal fields/screenshots/entitlements, whether one app record covers LTI and REST, private custody and placeholder support. |
| 05 | [Fred to confirm] actual payload membership, secure population and coordinated API/worker configuration refresh with version mapping. |
| 06 | [Fred to confirm] approved state/bootstrap inputs, saved-plan handoff, quota readiness, scheduler first-run safety and fresh-account execution. |
| 07 | [Fred to confirm] institutional deploy invocation/window, compatible previous images/config, explicit API/worker recovery commands and rehearsal. |
| 08 | [Fred to confirm] current Learn registration/placement/REST permission screenshots, issuer/platform endpoints, allowlisted deployment and real two-role launch. |
| 09 | [Fred to confirm] institutional Vercel project/root/build settings, domain/DNS, effective backend-origin update and recovery controls. |
| 10 | [Fred to confirm] approved synthetic identities, ingest trigger/completion window, private authorization-check method and complete live results. |
| 11 | [Fred to confirm] credential-specific overlap/revocation and consumer refresh, HS256/session impact and a tested LTI fixed-key rollover plan. No generic zero-downtime claim. |
| 12 | [Fred to confirm] incident contacts/response targets, deployed log fields/request correlation, provider cause and sustained recovery observation. |
| 13 | [Fred to confirm] exact target/region/profile, EBS layout, address/TLS, startup readiness, stop window, backup/expiry replacement plan. No original EC2 operation transcript was located. |

The registry's old linear order had bootstrap cycles. Drafts make 05/06 phased and 04/08 provisional until real endpoints exist. Runbook 09 corrects the suggestion to update only the frontend-origin secret: the Terraform-declared Lambda value wins. Runbook 11 records a source mismatch with the catalogue's aspirational JWKS overlap: source currently emits one fixed key ID. These findings are documented here without editing the other lanes' files.

## Checks and limits

- Source/ownership review: changes confined to `docs/engineering/runbooks/`; migration count is 36 at base. No SQL, infrastructure, service, dependency, spec or test edits.
- Markdown checker: local inline-link targets and local header fragments in this directory, all six front-matter fields, seven template sections, balanced code fences and the unknown marker in each of 13 procedures. Final result: 15 Markdown files (13 procedures plus registry/evidence), 167 local-link occurrences, one local anchor, zero failures; all 13 pass the required fields/sections/unknown-marker checks.
- Shell snippets: five shell blocks pass `bash -n`, which checks syntax only; it does not execute `make`, Terraform or AWS examples. CloudWatch query syntax and operational effect are not tested against hosted services.
- Bounded sensitive-pattern scan: AWS access-key identifiers, provider key formats, JWT-like payloads and private-key blocks in this directory; zero hits; counts only, no match values printed. This scan is not a proof of comprehensive de-identification.
- Repo-wide `docs/**/*.md` inline local-path comparison against the base: **32 missing-link occurrences before; 19 after; zero newly missing paths**. Thirteen occurrences resolved: 12 now resolve to authored runbooks, and 02's premature link to the uncreated database guide was replaced by an explicit Lane DB gate. Remaining inherited missing links: five database-guide references, 13 missing feature-spec references and one security/privacy-guide reference. They remain outside Lane R ownership. This comparison excludes fenced examples, external HTTP checks, reference-style links and anchor validation outside this directory.
- `git diff --check` passes. API/worker pytest, web lint/typecheck/build and runtime/hosted smoke are not run for Markdown-only drafts. No executable behavior changed; committed shared test isolation remains untouched. Prior integration results are attributed rather than rerun or claimed as this lane's results.

## Review gate

Commit on the lane branch only, then stop with the full AUDIT REPORT for coordinator review. No merge, push, deployment, hosted write/migration, key rotation or autonomous message to another chat. Secrets printed: none.


## APPROVAL-06 refresh — source base 6e21eed

Date: 2026-10-25 (Asia/Manila). Coordinator continuation: rebase onto local main, update only owned runbooks for 37 migrations and the exact 0037 maintainer procedure, trace current generation/tests and Fred-only release gates, then stop at the audit. Branch/worktree remain unchanged.

### Rebase and ownership

Worktree was clean at original `ffeaf28d5e15ddc8771d16af3769c5701b697aa9`. Local main was `6e21eed186cea468e7a06a0e0bca06d467bb56f0`; 4f3ec29 ancestry passed and main had no changes under this lane's directory. `git rebase main` succeeded without conflicts, replaying the original docs as `f94238b114cf4629e3b2e39a5781b4761f48f6be`. No pull/rebase of main, fetch, merge, push, hosted action or other-worktree change occurred. The refreshed delta touches only 02, 07, 10, 12, registry and this evidence file; all 15 lane files remain under the original ownership boundary.

### Current source and instructions

- Read updated AGENTS.md, router, [APPROVAL-06 rev 2 with confirmed amendments](../../work/handover-2026/approval-06.md), [integration/generation evidence](../../work/handover-2026/evidence/approval-06-integration.md), [exact 0037 runbook](../../runbooks/0037-apply.md), its SQL, manifests, export script, committed service isolation and current diagnostics source. Existing root/area CLAUDE.md remain routing guides; there is no closer runbooks guide.
- Filesystem count is **37 SQL files** under `packages/db/migrations` (0001–0037). Relocation and local package scripts remain gated by FG-2. Do not convert this source count into a hosted applied-state claim. Historical 36-file audit evidence stays attributed; B's 0037 note separately records its 37-file local replay, real SQL checks and temporary rolled-back fixture-grant limitation.
- FG-3: Fred confirms exact checksum/project/0001–0036 baseline, absence of pinned_at, RLS/policies/grants, service-role SELECT/UPDATE and counts; applies reviewed 0037 once; records nullable/no-default metadata, preserved rows/null pins and unchanged access controls. Stop on existing column/missing prerequisites; SQL editor does not automatically record CLI history. No SQL was run here. B's runbook and SQL remain unedited.
- FG-4: after final coordinator checks and FG-3, Fred deploys, verifies alias/worker/startup, pushes main and waits for Vercel Ready. FG-5 is his live acceptance; FG-R is his API/Vercel rollback. FG-1 provider paid fallback/runtime refresh/hint retest is also Fred-only. FG-2 blocks Lane DB only. Same-day gates supersede initial approval timing and stale lane-state snapshots.
- Runbook 07 documents generation using a fresh API Python process loading committed conftest before export, then direct frontend type generation, as the coordinator recorded at 7036f27. The bare web gen:api pre-hook is not implicitly pytest-isolated. Both service suites use committed isolation and separate processes; current frontend/browser commands and external fixtures are attributed to coordinator evidence. No generation, application suite, browser server or deployment command was run by Lane R.
- Runbook 12 now reflects merged JSON embed/chat diagnostics (nullable status/model, budget request ID); code presence does not establish live rollout. APPROVAL-06 records primary 429, with FG-1 recovery pending. Runbook 10 follows current memory-only file staging until Send and retired new-chat starters, and marks I/G/U close-out checks conditional on the final included/deployed revisions.

### Refreshed validation

Complete rebased-directory validation passed: 15 Markdown files / 13 procedures; all required fields/sections/unknown markers; 187 local-link occurrences and one local anchor resolve; six shell blocks pass bash -n; the embedded generation Python snippet parses with ast.parse without execution; bounded sensitive-pattern scan has zero hits. Read-only manifest/checksum checks confirm 37 files and the exact 0037 checksum from B's apply note. Branch diff against 6e21eed is confined to the 15 owned files; this refresh changes six of them. Repo-wide inline local-path check improves 29 missing occurrences at the new base to 16, with zero new missing paths (the remaining 16 are inherited outside this lane). git diff --check passes. Tests, lint, typecheck, build, generation and browser/runtime/hosted checks were not run for these Markdown-only changes. Operational verification remains unperformed and all 13 procedures remain execution-unverified. No secrets/dotenv/secret payload, parent-chat history or hosted configuration was read. Review gap list above remains applicable except its superseded migration/B/logging snapshots: hosted Postgres major, FG-3 application, remaining account/setup decisions and live recovery/acceptance are still [Fred to confirm].
