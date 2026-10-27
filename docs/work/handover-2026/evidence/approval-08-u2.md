# APPROVAL-08 U2 implementation report — reviewed locally

2026-10-27. Candidate795b10f41a634ae5e4b4ed1aee31f6af87cc29f6, rebased onto0f7da692a22be64368702c43efb2d324456cc562 after T2. Coordinator reviewed the final26-file diff and merged locally atad7a9acbeefaae05a3a4d6d77a722db5a9179ccb. No publication or live acceptance is implied.

## Result and scope

Student surfaces use neutral availability copy. The workspace route is reachable by staff, so E4 retains their material-count notice and changes only its role condition. Test uses “New practice set / Fresh questions. Choose 5, 10, or 20 at a time.” Not-ready, caught-up and fetch-error/Retry remain distinct. Instructor material wording remains.

Test/Study/Diagnostic share the static-mascot, one-line, skeleton loading card. Synthetic content/loading widths match:343px at375px and752px at1440px. The shared stream moves horizontal padding inside its800px shell so those content cards align. Model assistance has one shimmer and a disabled, stable initiating control. Diagnostic bulk-submit disables all choices but shows only the activated footer button's spinner; AnswerableCard's optional pendingFeedback defaults to its previous behavior for other callers.

Get new cards explicitly fetches the existing review-mode query through TanStack Query, including when opened from Study all. The active session remains pinned while that request settles. Already-posted items are filtered; an empty result preserves completion and replay, with an actual next-review date from existing review/membership dueAt. Missing/invalid dates show an inline error, never an invented date. Replay and posted-rating/idempotency protection remain. No review payload, evidence/mastery write or scheduler change.

Two reproduced defects are recorded rather than hidden:

- Original reload restored completed cards and cleared the posted guard before refetch; a rated card could reappear and accept a second POST with a different idempotency key. The new completion flow prevents it.
- An intermediate pinned-session candidate failed all three controlled course/skill/mode-switch tests, while original source passed. A keyed inner session now resets genuine scope changes, including loading transitions, while retaining the same-scope snapshot. Final21 component cases pass.

## Named exception proofs

E2, extended by Amendment6, changes exactly two expected/assertion lines in H's frontend-closeout.browser.mjs:

| State / old text | New expectation |
| --- | --- |
| Workspace positive waiting counts showed material wording | Student material wording is always absent |
| Questions unavailable: Waiting for course material | Your baseline check isn't ready yet. |

All remaining fixtures, seeds, paging, Retry/count/navigation assertions and non-material text are identical. Remainder SHA-256:414fb2acc102bc9482d980ab0b5f5dc9e9fe8c94e5fb117a9f9eb109ac7b5134.

| Student state | Distinct message |
| --- | --- |
| Not ready | Your baseline check isn't ready yet. Check back later. |
| Completed | You're all caught up |
| Fetch error | We could not load the diagnostic, with Retry |

E4 changes only the condition at workspace index.tsx:89 to retain the notice for non-student sessions. Its hook, variable, Diagnostic counts, navigation and layout stay. No07 commit touched that route. Both roles are tested. No new tour anchor was needed after Amendment7a.

All98 frozen07 paths remain unchanged except E2. Tutor source, API/worker/DB source, E3 and CourseShell are byte-identical to integrated main. The blocked twelve-step tour is not implemented by this lane.

## Files changed

- apps/web/src/components/ai-elements/prompt-input.tsx
- apps/web/src/components/shared/BriefLoading.tsx
- apps/web/src/components/shared/LoadingPanel.tsx
- apps/web/src/components/shared/LoadingRegion.tsx
- apps/web/src/components/shell/TutorSidebar.tsx
- apps/web/src/components/study/AnswerableCard.tsx
- apps/web/src/components/study/AssistantBlock.tsx
- apps/web/src/components/study/ComposeDock.tsx
- apps/web/src/components/study/StudyStream.tsx
- apps/web/src/components/study/TopicLanding.tsx
- apps/web/src/components/ui/sonner.tsx
- apps/web/src/features/diagnostic/components/DiagnosticPanel.tsx
- apps/web/src/features/diagnostic/tests/frontend-closeout.browser.mjs
- apps/web/src/features/flashcards/components/FlashcardDeck.tsx
- apps/web/src/features/flashcards/hooks/use-flashcards.ts
- apps/web/src/features/flashcards/schema/flashcards.schema.ts
- apps/web/src/features/flashcards/tests/final-ui-pass.browser.mjs
- apps/web/src/features/flashcards/tests/study-deck.test.mjs
- apps/web/src/features/gamification/components/GamificationSummary.tsx
- apps/web/src/features/instructor/components/DecisionCenter.tsx
- apps/web/src/features/instructor/components/SkillReviewPanel.tsx
- apps/web/src/features/lessons/components/LessonChat.tsx
- apps/web/src/features/practice/components/PracticePanel.tsx
- apps/web/src/features/skill-hub/components/StudyBrowser.tsx
- apps/web/src/features/skill-hub/components/TestBrowser.tsx
- apps/web/src/routes/course/index.tsx

## Verification at candidate

| Check | Result |
| --- | --- |
| Study component regressions |21 passed |
| Retained frontend/E3/route unit checks |77 passed |
| New U2 browser suite |146 assertions passed |
| H Diagnostic closeout/E2, final rerun |114 passed |
| Instructor read states |222 passed |
| Evidence history / scope |80 /16 passed |
| Twin presentation / instructor feedback |148 /63 passed |
| Retained legacy tour browser |616 passed |
| Web lint / typecheck / build |PASS;0 lint errors,18 existing warnings |
| Ownership, whitespace and frozen-path proofs |PASS |

The first concurrent history run timed out; its unchanged standalone rerun passed80 and later stable runs also passed. No assertion was edited to hide that failure. The mixed Tutor browser still fails its obsolete shared three-spinner expectation; T2 owns the strict test-only C1 follow-up after U2. The616 legacy tour assertions do not establish the blocked no-write rework or production side-effect freedom.

Lane Vite PIDs6448 and13282 were stopped;5173 was free before coordinator released it to the minimal-disable lane. Synthetic screenshots were visually checked; artifacts are local only, not retained. They are not Fred's live LTI acceptance.

## Complete spinner inventory

37 original rendered product sites outside Tutor →17 remaining:20 removed,15 permitted activated controls,2 reserved CourseShell sites. Removed locations refer to pre-U2 base; retained locations to candidate. Imports are not extra product indicators. Spinner remains the sole direct Loader2/animate-spin implementation.

| Source / location | Decision and reason |
| --- | --- |
| ai-elements/prompt-input.tsx:1254 | Remove model-wait spinner; stable disabled control |
| shared/BriefLoading.tsx:26 | Remove page spinner |
| shared/LoadingPanel.tsx:34 | Remove card spinner |
| shared/LoadingRegion.tsx:15 | Remove skeleton overlay spinner |
| shell/TutorSidebar.tsx:111,234 | Remove chat-list spinner; retain disabled Delete |
| study/AnswerableCard.tsx:142 | Retain activated grading feedback; Diagnostic opts out |
| study/AssistantBlock.tsx:52 | Remove duplicate; retain one shimmer |
| study/ComposeDock.tsx:114,135,158 | Retain activated non-model controls |
| study/TopicLanding.tsx:176 | Remove background status spinner |
| ui/sonner.tsx:24 | Remove toast/status spinner |
| diagnostic/DiagnosticPanel.tsx:163,197 | Remove status spinner; retain disabled Submit |
| flashcards/FlashcardDeck.tsx:74,893,904 | Remove advanced-rating and model-status spinners |
| flashcards/FlashcardDeck.tsx:388,467 | Retain explicit reload/continue control feedback |
| gamification/GamificationSummary.tsx:68 | Replace header-stat spinner with reduced-motion skeleton |
| instructor/AutoMatchedSection.tsx:83 | Retain disabled detach; unchanged file |
| instructor/DecisionCenter.tsx:141,471 | Remove model-wait spinner; retain disabled recording |
| instructor/SkillReviewPanel.tsx:63,242,131,143 | Remove proposal-status spinners; retain disabled decisions |
| lessons/LessonChat.tsx:458,468 | Remove model-assistance spinners |
| practice/PracticePanel.tsx:202,207 | Retain disabled retake/new-set controls |
| skill-hub/StudyBrowser.tsx:223 | Remove background preparation spinner |
| skill-hub/TestBrowser.tsx:465,333 | Remove background generation; restrict control feedback to activated request |
| shell/CourseShell.tsx:442,443 | Reserved duplicate start-tour finding, unchanged by U2; student entry is separately hidden under7a, instructor stays unchanged |

## Finding-only material flag review

Fred's four sets/20 attempts are reported counts, not independently verified hosted observations. Current bank readiness and saved-set/attempt history come from different predicates/records, so those counts cannot establish whether the IaaS/PaaS/SaaS flag is wrong. No hosted inspection, flag repair or configuration change occurred.

```text
AUDIT REPORT
Task / brief ID: APPROVAL-08 U2; E2/Amendment6; E4; WI-27
Branch and worktree: codex/final-ui-pass; lane worktree (local only, not retained)
Base revision: 0f7da692a22be64368702c43efb2d324456cc562
Files changed: 26; exact manifest is the candidate diff against base
REQ / WI IDs touched: DIAG-REQ-008/013/014; STUDY-REQ-003/006/007; WI-27
Commands run and results: component21; unit77; browser results above;
  web lint/typecheck/build and freeze/diff proofs passed.
Spec changes made: none by lane; coordinator committed first.
Evidence added: this reconciled lane report; synthetic captures local only, not retained.
Anything not done, and why: T2-owned mixed expectation follow-up pending;
  full TOUR-2 blocked; hosted material flag and FG-9 not verified.
Risks or questions for the planner: retain history timeout/retest, external
  renderer/browser fixture dependency and human acceptance limitations.
Secrets printed: none (confirmed).
```
