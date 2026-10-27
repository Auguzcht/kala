# APPROVAL-09 — Fred's direct frontend polish

2026-10-27. Source base: eb9409a8dc5617f01f9dc20d888775009894ec78. Branch codex/fred-polish. Fred edits application code; Codex prepares the workspace/specifications, read-only privacy audit and final checks. A final push needs Fred's separate delegation. No backend, migration, hosted change or sent-message edit work is authorized. A cross-user leak finding stops everything immediately.

## Workspace and specification boundary

Web on5173 must run from this worktree with no competing server. Existing private web settings are reused without printing values. They currently target the deployed API; a second local API is unnecessary for that configuration. If later needed, an existing-env local API connects to hosted Supabase: local clicks write real hosted rows, the same as live. Do not substitute test secrets or assume localhost implies a disposable database.

Before Fred's edits land, coordinator specifies TUTOR-REQ-017 message copy, TUTOR-REQ-018 assigned Tutor Start prefill, TWIN-REQ-011 unified Next paging, the corresponding existing TWIN/INSTR paging clauses, and DESIGN-REQ-001/002 selection tokens/shared column edges. Copy is clipboard-only with truthful Copied feedback; no sent-message edit control. Start prefills a new, unsent skill draft without create/ask/plan-state mutations. Last-loaded Next fetches H's next keyset batch, preserving errors, scope, order, instructor behavior and backend contracts. The shared edges apply to Study and Tutor. Selection background becomes the scoped #BCD3F4 token, without changing primary brand colors.

## Source findings and Fred's file pointers

Line references below are at the approved base; Fred's edits may move them. Frontend sources and matching affected tests are Fred-owned. Coordinator edits specs/DESIGN and this record, not UI source. Preserve current data-tour anchors and E3's seven historical proofs; E3 is a check, not an editable escape hatch.

| Area | Files / lines | What to inspect |
| --- | --- | --- |
| Study stream/content | apps/web/src/components/study/StudyStream.tsx:47–48 | U2 moved horizontal padding to the800px inner stream column |
| Study dock | apps/web/src/components/study/ComposeDock.tsx:86–88; components/ai-elements/dock-layout.ts:13–15 | Footer px-4 plus dock's separate max-width/content wrapper; compare actual outside edges |
| Tutor messages/dock | apps/web/src/features/tutor/components/TutorChat.tsx:299,365–370 | Messages use StudyStream; dock has a separate footer/800px wrapper and empty-state padding |
| Tutor composer | apps/web/src/features/tutor/components/TutorComposer.tsx:191,263–279 | PromptInput container and internal row/textarea padding differ from outer column edges |
| Selection | apps/web/src/styles/globals.css:1,14; components/ui/input.tsx:11 | No authored global ::selection found at base. Input explicitly uses selection:bg-primary / selection:text-primary-foreground. Fred adds the scoped token/global rule and reconciles overrides |
| Tutor message copies | apps/web/src/features/tutor/components/TutorChat.tsx:304–335; components/study/UserBlock.tsx:4,17; AssistantBlock.tsx:18,47 | Saved, returned-unsaved and pending user turns render here. Add Tutor-only opt-in copy behavior; shared Study defaults stay unchanged |
| Shared ledger pager | apps/web/src/components/kala/evidence-ledger.tsx:45–53,118–119 | Local ten-row page state and currently disabled final-loaded Next |
| Older server batch | apps/web/src/features/twin/components/EvidenceHistoryLedger.tsx:14–18,32,38–52 | Hook ownership, error/Retry/Reload states and the separate older-batch button to replace |
| Keyset/cache contract | apps/web/src/features/twin/hooks/use-evidence-history.ts:7–23 | Keep H's cursor, identity/role/course key, deduplication and next-page state |
| Instructor reuse | apps/web/src/features/twin/components/TwinBody.tsx:471; features/instructor/components/LearnerRecord.tsx:260 | Both use EvidenceHistoryLedger; same new Next behavior, unchanged instructor errors/data boundaries |
| Assigned Tutor Start | apps/web/src/features/plan/components/InstructorPlan.tsx:40,110–112 | Tutor item maps to the route; current Start passes no skill draft |
| Current prefill behavior | apps/web/src/components/shell/TourRunner.tsx:122–127 | Empty textarea only, native value/input event, never send. It is tour-local, not an existing exported navigation API. Do not enable/edit the hidden tour |
| Tutor navigation/draft seam | apps/web/src/routes/course/tutor.tsx:11–24; features/tutor/components/TutorChat.tsx:50–63; TutorComposer.tsx:76,268–274 | Search schema currently accepts only conversation; draft is controlled locally. A frontend handoff is required for plan Start; no backend change |

The two findings above are recorded rather than invented as already-existing global selection/prefill APIs. Fred may wire the frontend handoff within the approved Tutor/plan route/component scope. Any extra path or behavior outside those frontend concerns is reported before proceeding; no backend route/config or sent-message editing is a workaround.

## Privacy priority — Hello Clyde

Codex traces system/style, current question/embedding, owned history, institution/course chunks, owned attachments, any memory/summary and profile/name inputs. Prepare scoped read-only COUNT queries for Fred; do not run them, retrieve raw rows or search another user's content. Current sanitizer removes emails/explicit name: patterns only. Ordinary names survive. No fix before planner review.

Static source alone cannot honestly classify the reported incident. Course-material, this-user-history and cross-user-leak classifications require request-specific evidence. Keep unresolved cases explicitly unresolved; do not declare a leak absent or material harmless from an unobserved prompt. Stop immediately on a cross-user finding. The own-history query excludes the reported assistant reply to avoid circular attribution.

## End-of-edit gate — not executed yet

After Fred says his edits are finished, Codex checks the complete diff against this boundary and runs web lint/typecheck/build; affected Study, Tutor, Twin/history/instructor and workspace browser suites at375px/1440px; E3; docs checker/unit tests. Preserve H's fixtures, keyset/error/scope assertions. If old button/copy assertions legitimately change, map them to the new REQ, never skip or weaken permission/data assertions. Report exact files/results and stop. No merge/push/deploy, hosted write, backend or migration change is delegated here.

## Historical sources

- [Read-only privacy trace](evidence/approval-09-privacy-trace.md)
- [Counts-only SQL prepared for Fred, not run](evidence/approval-09-clyde-counts.sql)


## Amendment1 — Fred classifies Hello Clyde and authorizes a prompt-only fix

Finding: course material. Fred reports1 embedded AWS101 chunk containing the name; prior history, own attachments/display name/memory and ownership mismatch counts0, with no cross-user data. The source is the only match found; no per-request retrieval trace proves attribution. Record names from course material can reach the model under the existing email/name:-pattern sanitizer.

Named exception to the backend-change stop: branch codex/no-name-greeting from main. Coordinator first specifies TUTOR-REQ-019, then changes only the existing _SYSTEM literal to prohibit addressing the student by name and treat names in material as people in that material. Extend only the existing small-talk prompt test. E1 whole-module proof plus all19 identical guarded functions, full API and enrollment matrix required. No other backend/config/migration/sanitizer change. Merge with Fred's frontend only after all its checks. Fred runs make deploy and separately delegates the frontend push; Codex performs no deploy, push or hosted action.


## Preparation checkpoint —2026-10-27

Frontend specifications were committed before application edits at223aa36. Source base remains eb9409a8dc5617f01f9dc20d888775009894ec78. Web PID40695 serves the Fred worktree on5173, HTTP200 verified; the private web env uses the deployed API, so no8000 API was started. Existing dependency links/private env are local only, not retained. Codex has made no frontend application change.

Prompt branch candidate65e539ab177c632b0b51de6857021a7c1cb42793 is prepared separately from main. Spec-first e784d01, API1016/enrollment116, E1 single-literal AST and all19 unchanged guarded functions pass; seven other routers are byte-identical. Both branches' documentation checks have zero violations and18 unit tests pass. The backend implementation report is on that branch at docs/work/handover-2026/evidence/approval-09-no-name-greeting.md. It has not been merged, deployed or pushed.

Fred's frontend implementation/end-of-edit gate remains pending. After completion, review actual UI paths and matching tests, then run all required web/browser/E3/docs checks before combining branches. No sent-message edit, sanitizer/config change or hosted operation is authorized. The root coordinator retains sole ownership of shared specifications during that integration.


## Amendment 2 — final frontend freeze and coordinator integration

Fred approves `codex/fred-polish` at `bdba1601d628897b8ef7de22fcfe6ffde979f43a`; no further commits on that branch. Coordinator reviews the six commits beyond `2b6789f` before merging: E3 retains all seven historical comparisons/checksums with no skips or weakened assertions; prompt history is frontend-only and uses the existing ask/sanitizer/deadline/access path; all 27 instructor steps advance with Next and no write requirement; student tour stays hidden; lesson scrolling changes presentation only. Specifications and WI-34 must cover the behavior.

If review passes, merge frontend, no-name greeting, then FG-1b preparation in that order. Prove E1, all 19 guarded-function ASTs, immutable 0001–0039 SQL and no infrastructure/CI/Vercel/config-file changes. Run full API/worker/frontend/E3/routes, every browser suite sequentially on one main server, lint/typecheck/build, isolated OpenAPI zero diff, config and docs checks. The frozen source now has 12 browser suites, including the additional prompt-history suite; run all 12 rather than omit it from the requested prior eleven. Stop the server and commit the planner closeout as DRAFT with only proven values filled. Report main SHA/ahead/behind and that the greeting requires backend redeployment. No push, deploy or cleanup.
