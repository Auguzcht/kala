---
initiative: handover-2026
profile: light
status: in-progress
owner: Alfred Nodado (student assistant developer) until 2026-11-08, then ITO
---

# Handover 2026: make Kala maintainable by ITO

## Goal
By 2026-11-08, someone who has never seen Kala can run it locally, understand what each feature is supposed to do, rebuild every environment from the runbooks, and see exactly what is unfinished and why.

## Source authority
- Training plan OVPAA-0004, phase 10 (final documentation, architecture write-up, handover).
- Supervisor direction: hand over directly to ITO. ITO will find a maintainer.
- ITO infrastructure meeting: ITO provisions its own AWS (Mapua landing zone), Supabase, Blackboard and models. Full transfer, built from our migrations. Projects deploy one at a time after sponsor sign-off.
- Feature freeze: Oct 28 (agreed by the developer).
- This initiative does not add features. Feature work after the freeze is limited to fixing behavior the specs already describe.

## Approved lane state — 2026-10-24

[APPROVAL-01 including confirmed section 5](approval-01.md) is the scoped implementation authorization. All four audits are accepted. This lane does not assert other lanes have passed or merged.

| Lane | Scope / feature requirements | State / gate |
| --- | --- | --- |
| S | [LMS ingest spec](../../features/lms-ingest/README.md), INGEST-REQ-001; upload comment correction only | Authorized; Lane S owns spec and source checks. |
| T | [Tutor](../../features/tutor/README.md), TUTOR-REQ-001; [AI platform](../../features/ai-platform/README.md), AI-REQ-001 | Authorized; sanitizer coverage remains partial; non-tutor timeout defaults unchanged. |
| F | [Study](../../features/study/README.md), STUDY-REQ-001/002/003 | Authorized; SQL changes require planner stop/report; Lane F owns spec. |
| C | [Secrets catalogue](../../engineering/secrets.md) and placeholder examples | Authorized; excluded from Lane D ownership. |
| D | Framework, accepted archive moves, five durable reports, recap knowledge | Implemented locally; audit report and planner acceptance required before merge. |
| DB | [Database workflow](../../engineering/database.md), numeric migrations byte for byte, existing generated types path | Pending Fred's hosted Postgres major. Rebase after Lane D merge, then update post-archive references. Two clean db:verify runs required. Drift awaits Fred's schema-only dump. |

C/D merge only after green checks and planner review. S/T/F require their tests and web lint/typecheck/build plus planner approval. Fred deploys after integration, then performs the student/instructor runs in [TESTING.md](../../TESTING.md) and approved tutor/Study/auth checks. No lane merges itself. Lane DB has a separate gate and does not deploy the application.

## Calendar

| Week | Dates | Focus |
| --- | --- | --- |
| 13 | Oct 26 to 30 | Freeze features after Oct 28. Fix unreachable production endpoints. Inventory and route all docs. Write runbooks 03, 04, 08 first. Migration replay and drift check |
| 14 | Nov 2 to 6 | Feature specs for active features. Remaining runbooks. Backlog written as planned work items. Handover walkthrough with ITO. Account transfer list |
| End | Nov 8 | Semester ends. Repo, docs and account list handed to ITO |

## Work items

| ID | Title | Depends on | Status |
| --- | --- | --- | --- |
| WI-01 | Find and fix unreachable live endpoints (starting with `POST /tutor/ask` 502) and the Study "Reload deck" vs "All caught up" mix-up | none | planned |
| WI-02 | Inventory every Markdown file in the repo and classify it (authority, merge into spec, runbook source, archive, delete) | none | confirmed-done (audit accepted 2026-10-24, APPROVAL-01) |
| WI-03 | Install the documentation framework (AGENTS.md, docs/README.md, contract, templates) and move archived docs with pointer headers | WI-02 | done-awaiting-confirmation (local documentation checks; planner review pending) |
| WI-04 | Local throwaway Supabase stack: move to `supabase/migrations`, replay from zero, seed, generated `schema.sql` and types, one drift check against dev-hosted (see [database.md](../../engineering/database.md)) | none | planned |
| WI-05 | Secrets inventory generated from config files, `.env.example` files complete, exposure log, rotation plan | none | planned |
| WI-06 | Runbooks 03, 04, 08 (Blackboard instance, Developer Portal app, LTI registration) | none (needs the developer's memory) | planned |
| WI-07 | Runbooks 01, 02, 05, 06, 07, 09 to 13 | WI-05 | planned |
| WI-08 | Feature specs for every `active` feature in the registry, from code and tests | WI-03 | planned |
| WI-09 | Decision records from session recaps (attempt identity, XP rule, retake rules, thresholds, tour never writes, and others) | WI-03 | planned |
| WI-10 | Backlog as `planned` or `deferred` work items: admin, research portal, grade passback, instructor improvements, observability gaps, key rotation | WI-08 | planned |
| WI-11 | Carry-over from Checkpoint 1.1: lesson check reassignment, production click-through, retire 0.97 duplicate, regenerate 3 thin steps, worktree cleanup | none | planned |
| WI-12 | Handover walkthrough with ITO and project sign-off sheet | WI-07, WI-08 | planned |
| WI-13 | Infrastructure requirements and cost drivers for ITO and the sponsor sign-off (`engineering/infrastructure-requirements.md`), with real numbers from dev billing | none | planned |

## Historical sources (no authority)
Session records for Weeks 1 to 12, Checkpoint 1 and 1.1 records, `docs/masterplan.md`, `docs/stack.md`, root `CLAUDE.md` before this initiative, `*.PATCH.md` and `*.ADD_THESE_FIELDS.md` notes in source folders.

## Six recorded pre-freeze findings (planned)

- [WI-14: Bound inline lesson generation](work-items/WI-14-lesson-request-budget.md) — `planned`.
- [WI-15: Bound content upload work](work-items/WI-15-content-upload-budget.md) — `planned`.
- [WI-16: Add whole-request deadlines to LMS paths](work-items/WI-16-lms-request-deadlines.md) — `planned`.
- [WI-17: Define explicit Bedrock timeout and retry policy](work-items/WI-17-bedrock-timeout-policy.md) — `planned`.
- [WI-18: Decide API Gateway access logging with ITO](work-items/WI-18-api-gateway-access-logs.md) — `planned`.
- [WI-19: Extend de-identification coverage deliberately](work-items/WI-19-sanitizer-coverage.md) — `planned`.

Grade passback (AGS), admin and researcher features remain planned in the registry. The presence of legacy REST grade routes does not mean AGS is implemented. Full specs are WI-08, full runbooks WI-06/WI-07, remaining ADR seeds WI-09 and consolidated backlog WI-10. No missing full spec or cross-lane catalogue is silently filled by this framework lane.

## Durable evidence

- [Endpoint inventory and timing trace](evidence/audit-endpoints.md), with all 60 routes and 42 frontend call sites.
- [82-file docs inventory](evidence/audit-docs-inventory.md) and [complete disposition map](evidence/migration-map.md).
- [Migration replay report](evidence/audit-migration-replay.md), including all 36 results and all 13 notices (Part A only).
- [Configuration report](evidence/audit-config.md), including the complete names-only inventory and API/worker parity tables.
- [Tutor CloudWatch queries](evidence/tutor-cloudwatch-queries.md), preserved for Fred; never executed by this lane.
- [Recap-only knowledge](evidence/recap-knowledge.md) and [nine local guide extracts](evidence/local-guide-knowledge.md).
- [Lane D verification](evidence/docs-framework-verification.md) and [docs link check](evidence/docs-link-check.md).

The accepted four audits are historical evidence at `e9de105`. Original audit wording about pending implementation approval is preserved as history and superseded by APPROVAL-01. Missing external scratch outputs are explicitly unpromoted. Live Blackboard, tutor recovery and deployed behavior remain unverified in this lane.
