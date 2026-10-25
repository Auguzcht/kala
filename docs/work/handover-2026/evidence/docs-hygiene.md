# DOCS-HYGIENE — implementation audit

Status: ready for planner review; no merge, push or deployment. Date: 2026-10-25. Branch: `codex/docs-hygiene`. Base: `3a6a0aab27a8212f77b83e96b26127d830a696ba`. Worktree is the managed `docs-hygiene/kala` checkout; physical machine paths are deliberately not retained as operating links.

## Outcome and counts

Current docs no longer require archive/evidence reads for setup, checks or accepted behavior. Missing database/privacy guides are now factual current pages, architecture points to the implemented React/Vite runtime, portable fixture commands live in local-development.md, and absent planned/full specs are labeled rather than linked as if authored. No new feature or operational permission is introduced. Accepted ADR decisions are unchanged; only provenance-link placement changes.

Counts are occurrences, not affected lines. The same checker was applied to base-version documentation and final lane documentation; ignored originals are separately audited below. All published text files under docs/ and AGENTS.md are inputs; current files are all Markdown. No external HTTP checks were made.

| Check | Before | After |
| --- | ---: | ---: |
| Documentation files | 154 | 161 |
| Links into archive/evidence in the truth layer | 35 | 35 |
| Those links outside Historical sources / Verified by | 35 | **0** |
| Machine-local path occurrences | 187 | 99 |
| Machine-local paths without local-only marker | 187 | **0** |
| Machine-local paths marked `local only, not retained` | 0 | 99 |
| Missing local link targets in truth documents | 10 | **0** |

88 checkout-root occurrences became repository-relative identities; the remaining 99 historical/temp/runtime paths are explicitly local-only on their lines. Physical worktree identity is no longer an operating dependency; branch, revision and recorded result are retained. These are authorized hygiene annotations, not a rewrite of original verification results. Historical record bodies/files remain; no file deletion or move occurred.

## Disposition of every original record-link violation

The locations below refer to the base revision. Every provenance link is retained under Historical sources (the authoring verification page itself is explicitly a Historical sources record). Operating paragraphs retain their necessary facts, and instructions that previously required evidence commands now point to complete current instructions. No old benchmark/provider observation is promoted into a current guarantee.

| Original location | Record target | Current content / resolution |
| --- | --- | --- |
| `docs/README.md:21` | `docs/archive/README.md` | Task router / current operating boundary; provenance links only in Historical sources |
| `docs/README.md:48` | `docs/work/handover-2026/evidence/docs-link-check.md` | Task router / current operating boundary; provenance links only in Historical sources |
| `docs/README.md:50` | `docs/work/handover-2026/evidence/migration-map.md` | Task router / current operating boundary; provenance links only in Historical sources |
| `docs/decisions/ADR-016-legacy-flashcard-xp.md:6` | `docs/archive/session-recaps/MEMORY.md` | Context / Decision / Consequences retain the grandfathering gate unchanged |
| `docs/decisions/ADR-016-legacy-flashcard-xp.md:6` | `docs/work/handover-2026/evidence/audit-docs-inventory.md` | Context / Decision / Consequences retain the grandfathering gate unchanged |
| `docs/decisions/ADR-017-persona-feedback.md:6` | `docs/archive/session-recaps/DEEPSEEK_SEPT1_CLOSEOUT.md` | Decision / Consequences retain persona-feedback rationale unchanged |
| `docs/decisions/ADR-017-persona-feedback.md:6` | `docs/work/handover-2026/evidence/audit-docs-inventory.md` | Decision / Consequences retain persona-feedback rationale unchanged |
| `docs/decisions/README.md:30` | `docs/work/handover-2026/evidence/recap-knowledge.md` | Seed list explicitly remains unauthored; preserved accepted ADRs linked directly |
| `docs/engineering/environments.md:37` | `docs/work/handover-2026/evidence/audit-config.md` | Known gotchas / current database and release policy links |
| `docs/engineering/infrastructure-requirements.md:63` | `docs/archive/session-recaps/MEMORY.md` | Existing resource, secret ownership and quota/cost limits remain explicit; unverified numbers are not promoted |
| `docs/engineering/infrastructure-requirements.md:65` | `docs/work/handover-2026/evidence/recap-knowledge.md` | Existing resource, secret ownership and quota/cost limits remain explicit; unverified numbers are not promoted |
| `docs/engineering/local-development.md:29` | `docs/work/handover-2026/evidence/local-guide-knowledge.md` | Component provenance plus complete portable frontend fixture/check commands |
| `docs/engineering/runbooks/02-database-setup.md:26` | `docs/work/handover-2026/evidence/audit-migration-replay.md` | Steps state complete 37-file manifest, immutable SQL, local/hosted gates and replay limits |
| `docs/engineering/runbooks/02-database-setup.md:52` | `docs/archive/engineering/SUPABASE.md` | Steps state complete 37-file manifest, immutable SQL, local/hosted gates and replay limits |
| `docs/engineering/runbooks/README.md:23` | `docs/work/handover-2026/evidence/audit-migration-replay.md` | Authoring status and dependency/release gates; no required read of verification records |
| `docs/engineering/runbooks/README.md:23` | `docs/work/handover-2026/evidence/deployment-2026-10-25.md` | Authoring status and dependency/release gates; no required read of verification records |
| `docs/engineering/runbooks/aws-account-bootstrap.md:48` | `docs/work/handover-2026/evidence/recap-knowledge.md` | Current prerequisites, steps and quota/owner unknowns remain in the procedure |
| `docs/engineering/runbooks/blackboard-instance-ops.md:68` | `docs/archive/session-recaps/DEEPSEEK_SEPT1_CLOSEOUT.md` | Current metadata-only start/stop/verify procedure and expiry limits remain in the procedure |
| `docs/engineering/runbooks/blackboard-learn-instance.md:52` | `docs/archive/session-recaps/MEMORY.md` | Current acquisition/bootstrap prerequisites and unresolved vendor inputs remain explicit |
| `docs/engineering/runbooks/blackboard-learn-instance.md:52` | `docs/archive/session-recaps/DEEPSEEK_SEPT1_CLOSEOUT.md` | Current acquisition/bootstrap prerequisites and unresolved vendor inputs remain explicit |
| `docs/engineering/runbooks/deploy-backend.md:25` | `docs/work/handover-2026/evidence/approval-06-integration.md` | Steps and isolated generation method; commands now in local-development.md, not evidence |
| `docs/engineering/runbooks/deploy-backend.md:57` | `docs/work/handover-2026/evidence/deployment-2026-10-25.md` | Steps and isolated generation method; commands now in local-development.md, not evidence |
| `docs/engineering/runbooks/deploy-backend.md:74` | `docs/work/handover-2026/evidence/recap-knowledge.md` | Steps and isolated generation method; commands now in local-development.md, not evidence |
| `docs/engineering/runbooks/first-launch-smoke.md:37` | `docs/work/handover-2026/evidence/deployment-2026-10-25.md` | Role-based acceptance steps and explicit distinction from prior image/health observations |
| `docs/engineering/runbooks/incident-response.md:63` | `docs/work/handover-2026/evidence/tutor-cloudwatch-queries.md` | Current timing/provider metadata queries and rate-limit recovery guidance; historical incident is not a live-fix claim |
| `docs/engineering/runbooks/incident-response.md:63` | `docs/work/handover-2026/evidence/approval-06-integration.md` | Current timing/provider metadata queries and rate-limit recovery guidance; historical incident is not a live-fix claim |
| `docs/engineering/runbooks/incident-response.md:65` | `docs/archive/bugs/blackboard-rest-quota-exhaustion.md` | Current timing/provider metadata queries and rate-limit recovery guidance; historical incident is not a live-fix claim |
| `docs/engineering/runbooks/incident-response.md:71` | `docs/archive/incidents/INC-002-tutor-30s.md` | Current timing/provider metadata queries and rate-limit recovery guidance; historical incident is not a live-fix claim |
| `docs/engineering/runbooks/lti-tool-registration.md:53` | `docs/archive/bugs/blackboard-rest-quota-exhaustion.md` | Current registration/placement checks and throttling limits remain in procedure |
| `docs/engineering/runbooks/terraform-apply.md:59` | `docs/work/handover-2026/evidence/recap-knowledge.md` | Phased ECR/secret/image bootstrap and human plan/apply gates remain in procedure |
| `docs/engineering/runbooks/terraform-apply.md:59` | `docs/work/handover-2026/evidence/deployment-2026-10-25.md` | Phased ECR/secret/image bootstrap and human plan/apply gates remain in procedure |
| `docs/engineering/runbooks/verification.md:67` | `docs/work/handover-2026/evidence/approval-06-integration.md` | Whole document explicitly Historical sources: authoring record; not an operating input |
| `docs/features/README.md:33` | `docs/work/handover-2026/evidence/migration-map.md` | Completeness/missing-spec limits, source anchors and current Study boundary; no requirements inferred from disposition map |
| `docs/features/README.md:33` | `docs/work/handover-2026/evidence/local-guide-knowledge.md` | Completeness/missing-spec limits, source anchors and current Study boundary; no requirements inferred from disposition map |
| `docs/features/diagnostic/README.md:161` | `docs/work/handover-2026/evidence/diagnostic-availability-lane-g.md` | REQ-009–011 acceptance and verification limits already stated; historical Lane G proof retained only as provenance |

## The 27 local docs

[The complete 27-row table](docs-hygiene-local-docs.md) gives source identity, relevant content/coverage and disposition for each entry. Thirteen complete DeepSeek originals match their retained archive copies. The design brief is already retained. Current rules and relevant rationale are in specs, ADR-017, local development and existing evidence. No newly unique still-relevant accepted content was identified in available authored originals/extracts, so no new archive entry is proposed; none of the 27 originals is committed or deleted.

Limit: nine originals have already been replaced by routing pointers. Their current text and retained extracts were checked, but this is not a full-text re-audit of unavailable originals. The generated 40,447-line context export is classified by provenance/structure, not semantically re-audited as an independent spec. Those limits are explicit per row.

## Comment-only source changes and immutable exceptions

Six existing Python modules have identical executable ASTs after removing only module/class/function documentation-string nodes; ordinary string expressions elsewhere are preserved. Ten existing TS/TSX files have identical structural TypeScript ASTs (kind, flags, literal/identifier text and child structure, ignoring positions/trivia) and byte-identical emitted JavaScript with comments removed, using the installed TypeScript 5.9.3 compiler. No application call, type, import, runtime literal or JSX behavior changes. The only executable addition is the explicitly requested stdlib documentation checker and its policy tests. A routing-only Practice CLAUDE pointer now names the existing Study boundary rather than a missing Test spec.

Current citations name exact Study, Tutor, skills, LTI and ingest spec sections. Applied SQL remains byte for byte: SHA-256 comparisons pass for **all 37 migrations**. Three stale historical citations cannot be edited under the standing immutable-migration rule:

| Immutable source | Historical target | Resolution |
| --- | --- | --- |
| `packages/db/migrations/0010_tutor_sessions.sql:4` | `docs/AI_OVERHAUL_TODO.md` | Restore a small pointer at the historical path to current Tutor/Study specs; retain archived original plan. |
| `packages/db/migrations/0011_tutor_attachments.sql:4` | Same | Same pointer; SQL unchanged. |
| `packages/db/migrations/0019_async_item_generation.sql:9` | `docs/design/async-item-generation.md` | Add a historical-record header at the retained target pointing to current question-bank/Diagnostic contracts; original body stays. |

Executable output destinations and generator input arrays in scripts are outside the comment-only scope and remain unchanged; the benchmark docstring naming its output directory is not a requirements citation. The historical path comment in 0036 is unchanged.

Fred approved the sole shared file, `PracticePanel.tsx`: this lane changes only the comment; TOUR-REFRESH adds only its data-tour attribute on other lines. Merge docs first after approval; TOUR then rebases, proves both survive and that its combined executable diff against this base is exactly the approved attribute, and reruns tour browser/lint/typecheck/build. No tour file or tour spec was edited by this lane. The refined narrow shared-file rule is in AGENTS.md.

## Enforced check and verification

- `python3 scripts/docs_check.py`: zero violations. Fails misplaced archive/evidence links and unmarked machine paths. Handles relative/root-relative/encoded/hosted record targets, inline/reference/HTML links, ATX/setext section context and explicit Verified by fields. Code examples are not live links; machine paths in code examples still require the marker. Uses Git's tracked/non-ignored file set, not ignored local notes; UTF-8 text only, binary artifacts excluded.
- `python3 -m unittest discover -s scripts -p 'test_docs_check.py'`: **18 passed**. Covers forbidden links, heading reset/nesting, Verified by scope, reference use sites, HTML/encoded/nested targets, dot normalization, fenced/inline examples, host URLs, root router scope, non-Markdown text paths and marker line boundaries.
- Local-target existence comparison: **10 missing before, zero after** in truth documents. Planned admin/research/AGS and incomplete Test specs are labeled; database/privacy guides are authored. Not an external link or full repository-wide anchor check.
- Source AST/generated-output comparison: **6 Python + 10 TS/TSX passed**, as described above. Only docstrings/comments normalize; no application test body is edited.
- Migration SHA-256 comparisons: **37/37 identical**. Infrastructure changes: **0**. File deletions/moves: **0**.
- Shell syntax: **6 blocks** in local development/backend-release docs pass `bash -n` without execution. All **9** documented Node/browser entrypoint paths exist. Fixture install/setup commands were source-traced, not executed.
- Clean local clone of the committed lane: docs policy passes and all 18 checker tests pass without dependencies or dotenv; the throwaway clone is retained locally, not a deliverable.
- `git diff --check`: passed. Application API/worker/browser/lint/typecheck/build suites are not rerun for this lane because executable application AST/output is unchanged; TOUR-REFRESH owns its runtime checks. No server started or stopped, no hosted call or credential read, no dependency install/change in this worktree.

## Files changed

- `AGENTS.md`
- `apps/web/src/components/study/StudyStream.tsx`
- `apps/web/src/components/study/TopicLanding.tsx`
- `apps/web/src/features/flashcards/components/FlashcardDeck.tsx`
- `apps/web/src/features/instructor/components/AutoMatchedSection.tsx`
- `apps/web/src/features/instructor/components/SkillReviewPanel.tsx`
- `apps/web/src/features/instructor/schema/instructor.schema.ts`
- `apps/web/src/features/practice/CLAUDE.md`
- `apps/web/src/features/practice/components/PracticePanel.tsx`
- `apps/web/src/features/skill-hub/components/SkillHub.tsx`
- `apps/web/src/features/twin/lib/group-by-module.ts`
- `apps/web/src/routes/class/index.tsx`
- `docs/AI_OVERHAUL_TODO.md`
- `docs/README.md`
- `docs/decisions/ADR-016-legacy-flashcard-xp.md`
- `docs/decisions/ADR-017-persona-feedback.md`
- `docs/decisions/README.md`
- `docs/design/async-item-generation.md`
- `docs/engineering/architecture.md`
- `docs/engineering/database.md`
- `docs/engineering/environments.md`
- `docs/engineering/infrastructure-requirements.md`
- `docs/engineering/local-development.md`
- `docs/engineering/runbooks/02-database-setup.md`
- `docs/engineering/runbooks/README.md`
- `docs/engineering/runbooks/aws-account-bootstrap.md`
- `docs/engineering/runbooks/blackboard-instance-ops.md`
- `docs/engineering/runbooks/blackboard-learn-instance.md`
- `docs/engineering/runbooks/deploy-backend.md`
- `docs/engineering/runbooks/first-launch-smoke.md`
- `docs/engineering/runbooks/incident-response.md`
- `docs/engineering/runbooks/lti-tool-registration.md`
- `docs/engineering/runbooks/terraform-apply.md`
- `docs/engineering/runbooks/verification.md`
- `docs/engineering/security-and-privacy.md`
- `docs/features/README.md`
- `docs/features/diagnostic/README.md`
- `docs/features/lti-auth/README.md`
- `docs/features/study/README.md`
- `docs/work/handover-2026/README.md`
- `docs/work/handover-2026/closeout.md`
- `docs/work/handover-2026/evidence/0037-postchecks-2026-10-25.md`
- `docs/work/handover-2026/evidence/approval-02-coordinator.md`
- `docs/work/handover-2026/evidence/approval-03-integration.md`
- `docs/work/handover-2026/evidence/approval-04-verification.md`
- `docs/work/handover-2026/evidence/approval-05-coordinator.md`
- `docs/work/handover-2026/evidence/approval-06-integration.md`
- `docs/work/handover-2026/evidence/audit-config.md`
- `docs/work/handover-2026/evidence/audit-docs-inventory.md`
- `docs/work/handover-2026/evidence/audit-endpoints.md`
- `docs/work/handover-2026/evidence/audit-migration-replay.md`
- `docs/work/handover-2026/evidence/deployment-2026-10-25.md`
- `docs/work/handover-2026/evidence/diagnostic-availability-lane-g.md`
- `docs/work/handover-2026/evidence/docs-framework-verification.md`
- `docs/work/handover-2026/evidence/docs-hygiene-local-docs.md`
- `docs/work/handover-2026/evidence/docs-hygiene.md`
- `docs/work/handover-2026/evidence/docs-link-check.md`
- `docs/work/handover-2026/evidence/fg1-paid-fallback-2026-10-25.md`
- `docs/work/handover-2026/evidence/frontend-closeout.md`
- `docs/work/handover-2026/evidence/frontend-finalization-handoff.md`
- `docs/work/handover-2026/evidence/implementation-study-approval-02.md`
- `docs/work/handover-2026/evidence/implementation-tutor-approval-02.md`
- `docs/work/handover-2026/evidence/provider-and-0037-prechecks-2026-10-25.md`
- `docs/work/handover-2026/evidence/tutor-provider-502.md`
- `docs/work/handover-2026/evidence/ui-overhaul.md`
- `scripts/docs_check.py`
- `scripts/test_docs_check.py`
- `services/api/app/lti/routes.py`
- `services/api/app/routers/diagnostic.py`
- `services/api/app/routers/ingest_jobs.py`
- `services/api/app/routers/tutor.py`
- `services/worker/app/handler.py`
- `services/worker/app/jobs/embed_backfill.py`

## AUDIT REPORT

```text
Task / brief ID: DOCS-HYGIENE; WI-03 / WI-08 documentation continuity
Branch and worktree: codex/docs-hygiene; managed docs-hygiene/kala
Base revision: 3a6a0aab27a8212f77b83e96b26127d830a696ba
Files changed: full inventory above; no deletions or moves
REQ / WI IDs touched: no new REQs; existing Study/Tutor/SKILL/AUTH/INGEST
  citations and recorded boundaries; WI-03/WI-08; DOCS-HYGIENE
Commands run and results: docs policy zero violations; 18 checker tests;
  6 Python + 10 TS/TSX AST checks; 37 migration checksums; 6 shell syntax
  blocks; 9 documented entrypoints exist; truth missing links 10 -> 0;
  clean-clone docs policy + 18 tests passed; git diff --check passed
Spec changes made: Study retains existing mode/session rationale;
  registry labels missing full/planned specs; no intended behavior change
Evidence added: this audit, 27-row local-doc table, explicit incomplete
  closeout record; historical machine paths annotated or made relative
Anything not done, and why: no original-guide recovery/full generated
  context review; no immutable SQL comment edits; no runtime suites,
  hosted checks, merge, push, deploy or deletion in this docs-only lane
Risks or questions for the planner: nine replaced originals cannot be
  re-audited in full; institutional runbooks remain execution-unverified;
  TOUR must rebase/check the approved shared-file exception after docs
Secrets printed: none (confirmed)
```

## Subsequent release authorization and correction

2026-10-25: Fred approved TOUR-REFRESH 627ba9b subject to the docs-first rebase gate, then explicitly authorized the coordinator to push origin/main once all required checks pass and complete closeout. The earlier stop-before-push statement records the prior gate, now superseded for this release. Documentation-first merge, narrow PracticePanel comment/attribute coexistence, fresh tour/219/110/frontend/web checks and no backend deploy remain the sequence. Release evidence/current runbooks/closeout now record v7 at 00:04 UTC after the 00:01 UTC paid fallback change, runtime refresh complete, I/G/U backend present, frontend pending publication, and FG-5 live success unconfirmed. WI-24/25/26 statuses remain nonterminal and owner ITO.
