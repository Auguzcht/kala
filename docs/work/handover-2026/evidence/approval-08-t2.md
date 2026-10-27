# APPROVAL-08 T2 implementation report — reviewed locally

2026-10-27. Lane codex/tutor-polish; basebeccf5915c4caea045fc5a6e8be2945aaf8812ad; candidate4da230446b08b3d8c5ff9591c21ae9283c542b61. Coordinator reviewed source and synthetic1440px/375px dialog screenshots, independently proved E1/all19 admission guards, then merged at3375647f4af2d9870658f833b56652c75e650035. No app push/deploy/hosted write.

## Implemented and bounded

Rename uses existing Dialog/root/portal/overlay/header/footer primitives with accessible content, exact title/helper, selected prefilled title, trimmed blank/unchanged lock, one-submit guard, Enter, Escape/Cancel, safe error and trigger focus return. Save alone carries its pending spinner. Tutor model waiting is one existing shimmer with stable disabled Send, no second spinner/Thinking control. Conversation/file-preview loading uses skeleton/text; pin/file-status spinners removed. Existing upload/type/capability/pin/delete/recovery behavior retained.

E1 is exactly one module-level _SYSTEM Constant value change. Mocked provider sees brief friendly small-talk/no-roadmap/no-course-context instruction and preserved graded-work/grounding rules. No other import/function/guard/signature differs. Source literal diff is four added string lines; Python implicit concatenation is one AST Constant. The frontend change does not establish live model behavior; Hello remains FG-9.

Amendment2B is planned/deferred to ITO in TUTOR-REQ-015/WI-29, not partly built. No last-exchange endpoint, edit control, migration, evidence/mastery write, image support, provider or config change.

## Files changed

- apps/web/src/features/tutor/components/TutorChat.tsx
- apps/web/src/features/tutor/components/TutorComposer.tsx
- apps/web/src/features/tutor/components/TutorConversationRow.tsx
- apps/web/src/features/tutor/components/TutorFileCard.tsx
- apps/web/src/features/tutor/components/TutorFilePreview.tsx
- apps/web/src/features/tutor/components/TutorRenameDialog.tsx (new)
- apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs
- services/api/app/routers/tutor.py (E1 constant only)
- services/api/tests/test_tutor_small_talk_approval08.py (new)

## Validation

| Check | Result |
| --- | --- |
| Full API |1,016 passed |
| Dedicated Amendment7 enrollment matrix |116 passed |
| Tutor/schema/API-error/presentation unit checks |21 passed |
| E3 |53 passed |
| Synthetic Tutor/mixed retained browser |258 assertions passed at375px/1440px, reduced motion included |
| Web lint/typecheck/build |PASS; existing warnings retained |
| E1 AST and frozen-path diff |PASS |
| Coordinator independent full8-router comparison |PASS: only _SYSTEM literal differs, seven other routers byte-identical and all19 student guard calls retained |

Server: lane Vite PID3878, correct worktree and HTTP200, stopped after tests. Coordinator observed no listener before releasing5173 to U2. Screenshots are synthetic local-only artifacts, not live acceptance; raw user/provider data is absent. The mixed browser fixture still asserts old shared loading spinners in its non-Tutor cases; T2 must author a strict test-only C1 update after U2, then rerun it. No conditional acceptance of wrong/right behavior or skipped assertions is permitted.

## Complete Tutor spinner sweep

Baseline locations are atbeccf59; new location at4da2304. Grep covers Spinner, Loader2 and animate-spin throughout features/tutor, separating imports from rendered sites. No direct Loader2/animate-spin use exists in production Tutor files.

| Baseline rendered site | Disposition / reason |
| --- | --- |
| components/TutorChat.tsx:300 | Remove conversation-load spinner and loading shimmer; skeletons plus one text line |
| components/TutorConversationRow.tsx:96 | Keep only for user-activated Save, relocated to TutorRenameDialog.tsx:69 with disabled/pending lock |
| components/TutorConversationRow.tsx:159 | Remove menu pin shared-pending spinner, not a second status indicator |
| components/TutorConversationRow.tsx:185 | Remove row pin shared-pending spinner; retain pending disable/aria state |
| components/TutorFileCard.tsx:57 | Remove attachment uploading/processing status spinner; truthful text retained |
| components/TutorFilePreview.tsx:124 | Remove preview-load spinner; skeleton/text instead |
| Composer inherited submitted control | Stable disabled Send during model wait, no second indicator; user-initiated upload phase can use control feedback only |
| Shared AssistantBlock pending indicator | Tutor uses one local Shimmer while U2 removes the shared status spinner; no duplicate model-wait indicator |

The four obsolete Spinner imports are removed. Final production Tutor grep has only TutorRenameDialog.tsx:9 import and:69 Save render. Every direct original rendered site is covered above; imports are not additional UI indicators. Shared components remain U2-owned.

## Complete Amendment7 guard reconciliation

All retain one unchanged student admission call in their respective function:

| Router | Functions |
| --- | --- |
| courses | get_course, memory_summary |
| twin | get_twin, next_up, learning_plan |
| diagnostic | get_content, list_modules, get_diagnostic_status, get_diagnostic |
| flashcards | skill_cards, deck |
| gamification | summary |
| practice | next_item, list_sets, get_set, get_set_results |
| lessons | get_lesson |
| tutor | list_conversations, get_conversation |

Tutor detail still resolves owned conversation before course admission, then reads messages/attachments. The checkpoint strict student AST proof remains unchanged/historical; E1 deliberately changes one prompt constant so no claim is made that its unmodified whole-module comparator would accept final08 source. E1 full-module normalization plus116 route tests chain that checkpoint safely.

## FG-L — delegated by Fred, read-only

One API log-group candidate discovered; exact last48hours descending tutor_timing/provider query with limit50 executed using in-memory stdout/stderr capture. Mandatory actual-row privacy stop field: **user_id_prefix**. No raw row/value was printed/saved; raw data is local only, not retained. No other identifier or body is retained here. No write/put/delete/update/tag/configuration operation ran.

All requested stage medians/maxima, fallback-request count and primary status/model counts are **unavailable**, not zero. The15–20s attribution is unestablished because inspection stopped immediately. Recommendation: keep configuration unchanged. No inference about provider credit or model availability follows. Fixing the logged field is a separate scoped diagnostics follow-up, not permission to alter E1's router scope.

```text
AUDIT REPORT
Task / brief ID: APPROVAL-08 T2, WI-28, E1; FG-L delegated by Fred, read-only
Branch and worktree: codex/tutor-polish; lane worktree (local only, not retained)
Base revision: beccf5915c4caea045fc5a6e8be2945aaf8812ad
Files changed: nine-file manifest above
REQ / WI IDs touched: TUTOR-REQ-005/009/010/012/013/015/016;
  AUTH-REQ-007 retained; WI-28/29
Commands run and results: API1016, enrollment116, frontend21, E3 53,
  browser258, web checks and AST/freeze proofs pass as detailed above.
Spec changes made: none by lane; coordinator committed first.
Evidence added: this reviewed record and synthetic screenshot inspection.
Anything not done, and why: live checks reserved for Fred; edit deferred;
  FG-L metrics unavailable after mandatory stop; shared-test follow-up pending.
Risks or questions for the planner: user_id_prefix field finding;
  no live Hello/latency/permission claim. No partial edit implementation.
Secrets printed: none (confirmed).
```
