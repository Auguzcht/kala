# Kala handover closeout (DRAFT)

Prepared for: Mapúa Malayan Colleges of Mindanao ITO
Prepared by: Alfred Nodado (Auguzcht), with planner and coordinator agents, for the Office for Artificial Intelligence Curriculum Integration (OAICI)
Date: October 28, 2026
Status: DRAFT. Frontend frozen at `bdba160`; local integration verified separately from live acceptance. Formal project-wide freeze time: [Fred to confirm]. This initiative is record, not operational authority.

## What Kala is

Kala is an AI learning companion and digital learning twin. It runs as an intelligence layer on top of Blackboard Learn. Students and instructors enter through an LTI 1.3 link. Blackboard owns course content and grades. Supabase owns learning evidence.

Runtime: React and Vite SPA on Vercel, FastAPI on AWS Lambda behind HTTP API Gateway, an EventBridge-scheduled worker Lambda, Supabase Postgres 17.6 with pgvector, model calls through the provider router in services/api/app/ai/.

## Start here

1. [AGENTS.md](../../../AGENTS.md): repository rules, the spec-first process and agent rules.
2. [docs/README.md](../../README.md): the task router and which document wins when two disagree.
3. [docs/features/README.md](../../features/README.md): the feature registry and specs.
4. [docs/engineering/runbooks/](../../engineering/runbooks/README.md): environments, secrets (names only), database, security limits and 13 runbooks.
5. This file's open-items list.

ITO provisions its own AWS, Supabase, Blackboard registration and model provider, then builds from the migrations. No data, keys or accounts carry over.

## What is live at handover

| Component | Version |
| --- | --- |
| API Lambda | [Post-APPROVAL-09 live alias/version: Fred to confirm] |
| Worker Lambda | [Post-APPROVAL-09 immutable image digest: Fred to confirm] |
| Frontend (Vercel) | [New production Ready SHA after separately delegated push] |
| Application source | `502c5a2c1105c714c9ae5bfcb3c5377a5a3824b1`; the final closeout commit changes documentation only |
| Database migrations | 0001–0039 reported applied; FG-6 accepted by Fred. All 39 SQL files are byte-identical to the pre-09 baseline |

Known gap: 0001 to 0036 were applied by hand, so the hosted migration history table does not list them.

Rollback points: API alias v8 (and v7), the previous Vercel deployment, the saved worker image.

## Verification at handover

Local on merged main, with committed backend test isolation and synthetic browser fixtures:

| Check | Result |
| --- | --- |
| Full API suite | 1,016 passed |
| Worker suite | 117 passed |
| Student enrollment matrix | 116 passed |
| Frontend units, including Study components and routes | 62 passed, no skips |
| E3 | 56 passed, all seven historical proofs retained |
| Routes, repeated separately | 5 passed |
| Browser suites | All 12 passed sequentially, 4,991 assertions. Includes the prior 11 plus prompt-history coverage |
| Web lint / typecheck / build | Pass; 18 existing lint warnings, route-generator and bundle warnings remain |
| OpenAPI and frontend API types | Isolated regeneration, zero diff |
| Config inventory | Pass |
| Documentation and checker unit tests | Zero violations; 18 unit tests passed |
| Scope / E1 / migrations | Only the `_SYSTEM` literal changes in application backend; all 19 guard ASTs and all 39 SQL files unchanged |

All browser results use synthetic fixtures. Main server PID 98534 replaced the frozen frontend server PID 40695 for verification. Both were stopped; port 5173 has no listener. Live acceptance is FG-9 below.

## Human gates

| Gate | Result |
| --- | --- |
| FG-6, migrations 0038 and 0039 | Accepted with one finding (grant drift, below) |
| FG-8, deploy and publish | [Fred backend redeploy, separately delegated push and production Ready confirmation] |
| FG-1b, chat model swap | Secret update applied by Codex under Fred’s explicit CLI delegation; 26 → 27 entries, two approved targets verified, all others unchanged. [New-runtime refresh and post-swap live sample/aggregates pending] |
| FG-7, identity repair | Deferred to ITO. Legacy pairs not proved |
| FG-9, live click-through | [results table in the acceptance checklist] |

## Open items for ITO, in priority order

1. WI-14, lesson generation. First-open lesson generation runs inline and can exceed the 30 s Lambda timeout. Eight API Lambda kills at 30,000 ms were observed, but route-specific attribution to the reported lesson URL was not logged. Non-ready lessons are reclaimed on reopen. Move generation to the worker with a preparing state and a duplicate guard. guided_lessons.status already supports generating, ready and failed. Estimate: 2 to 3 days without a migration, 3 to 5 with retry metadata.
2. WI-31, Tutor latency. The retained incident sample has 10 primary successes (chat p50 9.27 s, max 20.93 s), three fallback successes (chat p50 7.04 s, max 8.88 s) and two handler timeouts at about 23.02 s. This is pre-swap, small-sample evidence, not a current latency benchmark. Add a primary-attempt limit that keeps fallback time, then stream answers.
3. WI-24, duplicate identity repair. Hanna Sato and Alfred Nodado each have split records from the old LTI vs REST identity bug. The cause is fixed. Old records are not merged. Script and runbook are ready (scripts/repair_identity_split.py, identity-repair runbook). The legacy pairs must be proved before any apply.
4. WI-32, side-effect-free reads. Several GET routes enqueue work, generate content, claim cards or record exposures. Prove fixes by database writes or a side-effect log, not HTTP method.
5. WI-30, student tour. Hidden for students because of item 4. The 12-step rework with fallbacks is preserved on branch codex/tour-rework. The 27-step instructor tour passes synthetic read-only checks locally. [New frontend publication and live walkthrough pending].
6. WI-29 / TUTOR-REQ-015, edit a sent prompt. Deferred. Messages lack an exchange and revision contract.
7. Tutor image attachments. Planned. The sanitizer is text-only, so images are a Data Privacy Act risk.
8. De-identification coverage. The sanitizer covers emails and name: patterns only. Names in course material reach the model. One such name was used to greet a student, and the merged `_SYSTEM` prompt rule now forbids addressing students by name. [Fred backend redeploy and live greeting acceptance pending].
9. Hint telemetry. Flashcard hint requests are not counted. The instructor card now reads "With evidence" until tracking is complete.
10. Instructor insights. Upstream percentile arithmetic needs review. The recommendation source label shows the configured primary, not the model that answered when the fallback ran.
11. Database drift. SELECT grants differ from the local replay on 14 tables (RLS-gated, no anon or public policies). Run the Lane DB drift check, move migrations to supabase/migrations, and add local db:* scripts.
12. Logging. Tutor timing logs include user_id_prefix. Review under the Data Privacy Act.
13. Data note. Study history from before the October 27 fix may contain duplicate review rows.
14. Long requests. The earlier endpoint audit found nine model/LMS paths at risk of exceeding the request window. Inline lesson generation remains unbounded in source; the API timeout aggregate is not a route-level proof.
15. Planned features with no shipped code: admin console, researcher portal, AGS grade passback. The Practice/Test spec is not fully authored.
16. Design exceptions awaiting lead designer review: pill-shaped chat docks and the Tutor empty-state mascot.
17. Test fixtures. Some renderer and browser fixtures live outside the repo (WI-20).

## Security and cutover

- Every credential is replaced at cutover, when ITO provisions its own accounts.
- docs/engineering/secrets.md lists every secret by name, store and owner, plus the exposure log. It holds no values.
- Credentials exposed during development are logged there by name. By decision, the AWS access key was not rotated before handover because cutover replaces it.
- The OpenRouter account ends with a low balance and is not topped up. ITO connects its own provider account.
- Instructor course access is enforced: 403 for the wrong role, 404 for a course you don't teach.

## Key decisions

Full records are in docs/decisions/ and the approval records.
- Migrations are the only database authority. They are forward only, and applied migrations are never edited.
- Spec first: behavior changes update the spec before code.
- No :free models in production config.
- The tour never writes data.
- Roster sync is by Blackboard REST uuid. Removals happen only after a complete roster fetch.
- Duplicate repair refuses pairs with mismatched consent or data-request records.

## Release boundary

The greeting fix is present in local main and **requires Fred’s backend redeploy**. The secret swap is already saved; a secret save alone does not prove a warm runtime loaded it. Fred deploys the final reviewed source, verifies the new API version/live alias and worker digest, then delegates publication separately. No push, deploy, hosted SQL, data repair or cleanup is performed by this integration. Live and gate placeholders remain intentionally unresolved.

The full student-tour rework branch remains preserved for ITO. Safe chat/worktree/branch cleanup and the human-facing root README, transparent logo, licensing and attribution pass remain separate follow-ups. License selection has not been inferred.

## Historical sources

- [APPROVAL-08 closeout snapshot before this draft](evidence/approval-08-closeout-before-09.md)
- [APPROVAL-09 integration review and checks](evidence/approval-09-final-integration.md)
- [APPROVAL-09](approval-09.md), including Amendment 2 recorded during integration
