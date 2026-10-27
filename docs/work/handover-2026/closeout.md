# Kala handover closeout

Prepared for: Mapúa Malayan Colleges of Mindanao ITO
Prepared by: Alfred Nodado (Auguzcht), with planner and coordinator agents, for the Office for Artificial Intelligence Curriculum Integration (OAICI)
Date: October 28, 2026
Status: development ended. Frontend frozen at `bdba160`. The final closeout commit starts the freeze at 2026-10-28T03:44:49+08:00 (Asia/Manila; 2026-10-27T19:44:49Z UTC). Docs-only changes after this commit need Fred. This initiative is record, not operational authority.

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
| API Lambda | alias `live`, version **9**, no weighted routing; Active/Successful |
| Worker Lambda | `sha256:4ceb1efc6a497fbab458260ecf8ed7beb9af57e145e0a2eb961b1c3066ec2b4d`; Active/Successful |
| Frontend (Vercel) | `b3b636f30bdef744a0e412c4b9f6e1af673dd9d9`, Vercel production Ready; host `kala-ak1zr2254-auguzchts-projects.vercel.app` |
| Application source | `b3b636f30bdef744a0e412c4b9f6e1af673dd9d9`; final closeout changes documentation only |
| Database migrations | 0001–0039 applied; FG-6 accepted by Fred. All 39 SQL files are byte-identical to the pre-09 baseline |

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
| FG-8, deploy and publish | Complete: backend v9/images verified; `b3b636f` pushed by Codex under Fred’s delegation, Vercel production Ready |
| FG-1b, chat model swap | Applied; added entry **`OPENROUTER_MODEL_CHAT`** confirmed from secret-version membership (26 → 27); the primary previously used its code default. Other entries unchanged except the approved fallback swap. v9 deployed. not enough samples since v9, post-swap latency unverified, ITO to measure under WI-31 (0 timing requests in the conservative window) |
| FG-7, identity repair | Deferred to ITO. Legacy pairs not proved |
| FG-9, live click-through | Accepted by Fred on live, October 28. The no-name greeting and model swap went live with v9 after the walkthrough. Fred spot-checks the greeting. |

## Open items for ITO, in priority order

1. WI-14, lesson generation. First-open lesson generation runs inline and can exceed the 30 s Lambda timeout. Eight API Lambda kills at 30,000 ms were observed, but route-specific attribution to the reported lesson URL was not logged. Non-ready lessons are reclaimed on reopen. Move generation to the worker with a preparing state and a duplicate guard. guided_lessons.status already supports generating, ready and failed. Estimate: 2 to 3 days without a migration, 3 to 5 with retry metadata.
2. WI-31, Tutor latency. The retained incident sample has 10 primary successes (chat p50 9.27 s, max 20.93 s), three fallback successes (chat p50 7.04 s, max 8.88 s) and two handler timeouts at about 23.02 s. This is pre-swap, small-sample evidence, not a current latency benchmark. Add a primary-attempt limit that keeps fallback time, then stream answers.
3. WI-24, duplicate identity repair. Hanna Sato and Alfred Nodado each have split records from the old LTI vs REST identity bug. The cause is fixed. Old records are not merged. Script and runbook are ready (scripts/repair_identity_split.py, identity-repair runbook). The legacy pairs must be proved before any apply.
4. WI-32, side-effect-free reads. Several GET routes enqueue work, generate content, claim cards or record exposures. Prove fixes by database writes or a side-effect log, not HTTP method.
5. WI-30, student tour. Hidden for students because of item 4. The preserved rework is available to ITO as **origin/codex/tour-rework** at **beccf5915c4caea045fc5a6e8be2945aaf8812ad**, verified on origin. Its local worktree is retained. No merge of the rework was performed during this release. The 27-step instructor tour passes synthetic read-only checks locally. Frontend `b3b636f` is production Ready. Fred accepts FG-9 on live; the post-v9 greeting spot-check remains his final confirmation.
6. WI-29 / TUTOR-REQ-015, edit a sent prompt. Deferred. Messages lack an exchange and revision contract.
7. Tutor image attachments. Planned. The sanitizer is text-only, so images are a Data Privacy Act risk.
8. De-identification coverage. The sanitizer covers emails and name: patterns only. Names in course material reach the model. One such name was used to greet a student, and the merged `_SYSTEM` prompt rule now forbids addressing students by name. The rule is deployed in v9. Fred spot-checks the greeting after the accepted walkthrough.
9. Hint telemetry. Flashcard hint requests are not counted. The instructor card now reads "With evidence" until tracking is complete.
10. Instructor insights. Upstream percentile arithmetic needs review. The recommendation source label shows the configured primary, not the model that answered when the fallback ran.
11. Database drift. SELECT grants differ from the local replay on 14 tables (RLS-gated, no anon or public policies). Run the Lane DB drift check, move migrations to supabase/migrations, and add local db:* scripts.
12. Logging. Tutor timing logs include user_id_prefix. Review under the Data Privacy Act.
13. Data note. Study history from before the October 27 fix may contain duplicate review rows.
14. Long requests. The earlier endpoint audit found nine model/LMS paths at risk of exceeding the request window. Inline lesson generation remains unbounded in source; the API timeout aggregate is not a route-level proof.
15. Planned features with no shipped code: admin console, researcher portal, AGS grade passback. The Practice/Test spec is not fully authored.
16. Design exceptions awaiting lead designer review: pill-shaped chat docks and the Tutor empty-state mascot.
17. Test fixtures. Some renderer and browser fixtures live outside the repo (WI-20).
18. License selection. Owner: project owners, Fred or ITO. The human-facing root README, existing transparent logo and Alfred Nodado / Auguzcht and OAICI attribution were completed in the October 28 after-freeze, Fred-approved docs pass. The README states “Not yet selected. To be decided by the project owners.” No license has been inferred or granted, and no LICENSE file or logo asset was added or changed.
19. Local worktree codex/tour-refresh-handoff holds unreviewed, uncommitted pre-APPROVAL-08 tour edits. Not part of the release and not handed over. Fred discards or reviews it later.
20. Local worktree fg1b-preparation (merged, clean) is retained as this task's primary checkout. Fred removes it after the session.


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

## Release verification and freeze

Fred deployed the backend; Codex performed read-only verification. API alias live is v9 with no weighted routing, API and worker are Active/Successful, the worker CodeSha256 matches the digest above, and /health returned 200. API image digest: `sha256:d4ffa142dbae15b907792f6c81a8ddd3def700e97fccbb0f38208d428c55a750`. The corresponding local image archives match deployed digests and the tracked source at b3b636f: 62 API files and 30 worker files, including each requirements export. No backend redeploy or configuration edit was performed by this release task.

FG-1b membership was verified by comparing the previous/current secret versions in memory, with no values printed or retained. The added key is OPENROUTER_MODEL_CHAT. Timing uses Fred’s conservative start, 2026-10-27T19:22:00Z (October 28, 03:22 Asia/Manila), derived from his API update at 19:21:18Z and alias-v9 response before the 19:21:34Z worker update. The aggregate query ends at 2026-10-27T19:33:17.081306+00:00, filters version 9 log streams and finds 0 tutor_timing records: not enough samples since v9, post-swap latency unverified, ITO to measure under WI-31. No raw log rows or identifying fields were projected. This does not reopen the release gate.

Freeze starts at 2026-10-28T03:44:49+08:00 (Asia/Manila; 2026-10-27T19:44:49Z UTC), the final closeout commit timestamp. Development has ended. Any later docs-only change needs Fred. All open items above remain with their named owners; live acceptance is Fred’s recorded decision, not inferred from synthetic tests or health.

The full student-tour rework branch/worktree stays preserved for ITO. Cleanup is local only and limited to clean merged worktrees/branches; no unmerged or dirty work is deleted. Sixteen clean merged worktrees and 33 merged local branches were removed; two already-absent worktree registrations were pruned. The three explicitly retained worktrees remain. The exact inventory and verification are in the release report; the final documentation publication result is reported after its commit.

## Change log

| Date | Approval | Change |
| --- | --- | --- |
| 2026-10-28 | **after freeze, Fred-approved** | Rewrote the root README as a short human-facing landing page: existing transparent logo, closeout-first status, documentation links, stack, repository map, Alfred Nodado (Auguzcht) / OAICI attribution and explicit undecided license. README-only commit: `ff8cb36b57ee25d2b374e25c0f66a57c0397eb6e`. All 18 local link/image targets resolve and the sole hosted link, the production app, returned HTTP 200. Logos are unchanged; no LICENSE file added. This closeout entry is a separate docs-only commit so the README commit changes only README.md. The original freeze timestamp is unchanged. |

## Historical sources

- [APPROVAL-08 closeout snapshot before this draft](evidence/approval-08-closeout-before-09.md)
- [APPROVAL-09 integration review and checks](evidence/approval-09-final-integration.md)
- [APPROVAL-09](approval-09.md), including Amendment 2 recorded during integration

- [Delegated release, timing and cleanup record](evidence/release-closeout-2026-10-28.md)
