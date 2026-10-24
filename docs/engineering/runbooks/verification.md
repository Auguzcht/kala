# Lane R draft verification — WI-06 / WI-07

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
