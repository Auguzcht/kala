> Archived: 2026-10-24 (Asia/Manila), under APPROVAL-01. Historical source: `apps/web/docs/2026-10-18-hub-flow-audit.md` at base `e9de105`.
> Replacement: [docs/work/handover-2026/evidence/migration-map.md](<../../work/handover-2026/evidence/migration-map.md>). This original is evidence, not current policy; old commands and next-step queues are not authorization to execute them. Source line references below and in audits refer to the original, before this header.

# Skill hub flow review — 2026-10-18

Branch: `feat/study-lesson-ui`. Review baseline: `4d8f27a`.

## Scope and result

Reviewed the Lesson, Study, and Test surfaces; their queries and mutations; hub search parameters; old course-mode routes; Home's quick-practice entry; the shared session shell; and the student tour. Changes stay inside `apps/web`. No browser access, deployments, live model calls, or database changes were used.

The confirmed frontend defects below have been corrected. The API eligibility mismatch and the 12 unavailable card backs are resolved by the companion API branches shipping with this UI, as confirmed by the planner. This review does not establish that every live or visual edge case is resolved; the smoke matrix below remains for the user.

## Corrected findings

| Area | Previous failure | Correction |
| --- | --- | --- |
| Home quick practice | A completed generated set could remain in the skill-level query cache and reopen as results. | Generated sets are keyed by session identity. Home supplies a fresh session ID. Refreshes of an existing set use GET rather than creating another set. |
| Active Study session | Window focus or reconnect could fetch a new session ID and reset the queue, ratings, and position. | Active deck queries do not refetch on focus/reconnect. Their cache is discarded after the last observer leaves; a later session loads a fresh deck. |
| Study card reset | Reloading a one-card deck could preserve its flipped side or tutor text when the index stayed at zero. | Per-card reset also follows response session identity. |
| Topic/session switches | React could reuse state from another topic, sitting, or missed-review attempt. | Hub surfaces have explicit keys for course, skill, session, and applicable attempt identity. |
| Partial Test sets | Any existing answer caused the preview action to generate a replacement set. | Untouched sets offer Start test, partial sets Continue test, and completed sets View results. New set stays an explicit separate action. |
| Attempt provenance | Review missed could fetch the latest attempt instead of the attempt whose missed item IDs were selected. Refreshing a retake could also return to an older attempt. | Attempt identity is carried through Test URLs, missed-card review, return navigation, and retake session updates. Retakes and each missed-card study sitting get their own review session IDs, preserving the server’s per-session accounting. |
| Cache invalidation | Test answers did not refresh Study membership or saved-set attempt metadata. | Submissions refresh membership, the saved-test list, and the course review-count peek. Saved-set metadata is marked stale for its next read without replacing a visible question. |
| Future due times | A membership screen left open could keep showing zero due after a scheduled time arrived. | Membership polls once per minute while cards are scheduled but not yet due; active card sessions stay stable. |
| Loading/error recovery | Session loading, missing-material, unavailable-set, and failure states could lose their in-app exit. | Shared SessionState preserves a Return to menu back action. Saved-progress failures have an explicit retry. Hub loading errors and invalid skills also have recovery actions. |
| Wrong-topic saved links | A saved set ID could be opened under a different skill URL. | Preview and session paths reject a mismatched skill and provide a route back. |
| Late tutor responses | A response requested on one card or lesson step could populate the next card/step after navigation. | Request epochs prevent older responses from updating the current content. Lesson retry/reset also clears prior answered-kind and grading visibility flags. |
| Lesson edge cases | A final explanation-only step could finish without the shared celebration; submission failures had no visible feedback. | Completion celebrates through the existing helper, and failed grading gives retry feedback. Bloom labels were removed from the lesson session header to match the accepted student-facing design. |
| URL booleans | Coercing the string `false` produced true, unintentionally starting a session. | Search flags explicitly handle true/false and 1/0. Invalid legacy optional fields fall back safely. |
| Legacy routes | Lesson and per-topic Flashcards entries still ran separate local session flows. | Those choices open the canonical skill hub. The intentional course-wide due-review entry remains available. Legacy Test links already open the hub's Test menu. |
| Removed shortcut remnants | Unused single-item/Study-to-Test hooks, request helpers, and copy still described the removed shortcut. | Removed the unused frontend entry points and contracts, and corrected the empty-Test copy. No server endpoint was changed. |
| Guided tour | Tour steps still expected sessions at the old routes and skipped the hub's preview/start stages. | The runner can follow the skill route chosen by a preceding click. Test generation and start have explicit tour anchors and wait states. Existing question/feedback anchors remain. Missing targets stop the tour with a message instead of endlessly restarting the wait state; topic selection also works without a recommendation. |
| Repeated-card state | A card first marked Still learning could retain its original New badge on a repeat. | The active repeat uses the shared Slipping presentation after a local miss. |

Earlier branch fixes were rechecked: untouched claimed cards are excluded from review-due indicators, due-now counts agree with filters/actions, repeated misses remain queued until Got it, grading feedback waits for Next, completion actions have the accepted priority, and Study completion uses the existing reduced-motion-aware celebration.

## Resolved companion API fixes

**Graduated-card due eligibility — resolved.** Per the planner, `fix/membership-due-eligibility` introduces one shared `is_due` predicate in `srs.py` for both membership counts and review selection. It ships together with this UI branch. The previous discrepancy, where a graduated Known card could count as due but not be served, is no longer an outstanding API follow-up. Case 14 below is a joint-release regression check, not a remaining defect. This frontend branch did not independently deploy or live-verify that API branch.

**The 12 unavailable card backs — resolved.** Per the planner, the API now falls back to the correct choice label when resolving the card back, shipped with the lesson check branch. Those cards no longer require the bank-content repair previously stated here. The UI's “Answer unavailable” fallback remains for genuinely missing answers.

## Code-only verification

Ad hoc regression checks executed the current production functions with stubbed query/network callbacks via the installed TypeScript compiler. These checks exercised:

- strict URL flags and malformed legacy parameters;
- distinct generated-set session keys and GET refreshes of existing sets;
- preparing-state polling, active-deck refetch policy, future-due refresh, and cache invalidation;
- untouched, partially answered, completed, and unavailable Test action labels;
- attempt-preserving review, return, and retake navigation;
- repeated single-card misses, mixed queues, no extra review writes for local repeats, failed-save rollback, and returning from missed-Test review;
- delayed-response isolation, completion/confetti guards, reduced motion, tour route matching, and recovery shells around session fallback returns.

These checks are not browser or end-to-end coverage. Full web lint, typecheck, and build passed. Lint has 18 existing warnings and no errors; the build retains its existing chunk-size advisory.

## User smoke matrix before branch closure

1. Open an untouched topic before and after opening/leaving a deck without answering. Both should show Start studying and no Due markers on New cards.
2. Open a topic with both New and genuinely due cards. Only previously reviewed due cards belong in Review due and the Due filter.
3. Keep the Study menu open across a due time. Its counts should refresh within about a minute. Switching browser focus during a running deck must preserve position and ratings.
4. Miss the same single card repeatedly, then mark Got it. The deck must stay open until Got it. Mixed decks must not replay cards already recalled.
5. Request a hint, advance before it returns, and check the next card/step. The old answer must not appear there.
6. Finish Study, check one celebration, Reload deck, and finish again. Check Return to menu, secondary Reload, optional next group, and reduced motion.
7. Open untouched, partial, and completed saved tests. Check Start test, Continue test, and View results respectively. Continue must restore the first unanswered question.
8. Submit correct and incorrect answers. Feedback must remain until Next. Leave and reopen the Test menu; the attempt and Study counts should be current.
9. Retake a set, refresh mid-retake, and use Review missed. It should stay on that attempt, even if another sitting becomes the latest attempt elsewhere.
10. Exercise failed/slow loads, unavailable sets, missing material, wrong-topic set links, and invalid skill URLs. Retry and Return to menu/All skills must stay usable.
11. Visit the old Lessons, Flashcards, and Practice pages. Topic choices should reach the canonical hub. Repeated Home Start practice actions must not reopen an old completed sitting.
12. Run the student tour through Lesson teaching/checks and Test menu/generation/preview/start/feedback. Check the new wait states with a slow set preparation.
13. Open hub URLs with `start=false`, `start=0`, invalid tabs, or malformed optional fields. They must not accidentally start a session or crash the route.
14. **Resolved on the API side:** the shared `is_due` eligibility fix ships with this branch. Retain graduated-card eligibility as a joint-release regression check; it is not an outstanding defect.


## Smoke follow-up: cases 7, 9, 11 and 12

Baseline: `80d64f3` on `feat/study-lesson-ui`. Scope remains `apps/web` only. No browser was opened, no deployment was performed, and verification made zero live model calls. Diagnostic and standalone Tutor tour content were left as they were.

### Case 7 — partial Test preview

The pill divided the correct count by the answered count. It now uses the saved set's question count: one correct answer in a five-question set reads **1/5 correct**, and zero answers reads **Not attempted**. Continue test still restores the first unanswered question; that working behavior was retained.

Source: `src/features/skill-hub/components/TestBrowser.tsx:112`.

### Case 9 — refresh during missed-question review

The URL preserved the test attempt and exact missed item IDs, but the queue, cursor, ratings and posted-item set existed only in React memory. Refresh recreated the review session and started at card one.

Missed-question review now stores IDs and local progress in tab-scoped `sessionStorage`, keyed by user, course, skill, set, attempt and the exact missed item IDs. It restores the same review session ID, current card, repeated-card queue, local ratings and already-posted IDs. Confirmed progress is saved after the request succeeds; repeat ratings remain local and do not create additional review writes. Completion clears the saved progress. Malformed/unavailable storage falls back to an in-memory session.

If refresh happens during a save, the previous, unconfirmed card resumes with its pending idempotency key. Re-answering can safely retry that request instead of assuming the optimistic next-card state was saved. This intentionally differs from refreshing after a confirmed save, which resumes the next card.

Sources: `src/features/flashcards/lib/review-progress.ts:1`; `src/features/flashcards/components/FlashcardDeck.tsx:118`, `:208`, `:499`, `:529`.

### Case 11 — confirmed in code

- Old Lessons topic choices open `/course/skill/$skillId?tab=lesson`: `src/routes/course/lessons.tsx:28`.
- Old Flashcards topic choices open the same canonical hub with `tab=study`: `src/routes/course/flashcards.tsx:44`. Its intentional course-wide due-review entry remains separate.
- Old Practice links carrying a skill/set replace themselves with the hub's Test preview, without `start=true`; fresh topic choices open the Test menu: `src/routes/course/practice.tsx:35`, `:43`.
- Home Start practice creates a fresh `sessionId` on every click: `src/routes/course/index.tsx:147`. That ID participates in the generated-set cache key: `src/features/practice/hooks/use-practice.ts:24`. Repeated Home starts therefore do not reuse an old sitting's cached completed set. Once a set exists, refresh/polling reads it with GET instead of generating another set.

These are code-confirmed navigation contracts, not new visual smoke results.

### Case 12 — one-topic hub walkthrough

The previous walkthrough independently selected topics through the old Lesson and Practice pickers. It could pick a different, material-free Test topic and wait on a disabled generation button.

The tour now reads bank availability and saved tests before starting, selects one topic with at least five prepared questions, and pins that skill through Lesson, Study and Test. It prefers a ready lesson already in the query cache, then the current topic, with saved tests as another preference. It excludes topics marked no-material. On legacy courses without bank serving, it uses an already prepared lesson or a topic with material and an existing five-question set instead. Cancelling the availability dialog also cancels the pending tour launch. If no suitable topic exists, it reports that immediately instead of entering an unavailable Test flow.

The hub walkthrough keeps one topic but leaves all saving actions to the student. It opens the Study menu before entering a deck, since opening a deck claims cards and records exposure. Students choose to enter the deck, create/start a Test set, answer checks/questions, rate cards or send chat. Completed-only Test topics stay on the menu, explaining Retake and New set without activating either.

Each dock can open and pre-fill an editable sample without submitting it or waiting for a reply. Existing draft text is preserved. Lesson Continue and front-side Show answer remain UI-only actions; Show answer has its own anchor so it can never accidentally activate Got it after a student flips the card first.

The runner navigates on search changes within the pinned skill, keeps asynchronous waits separate, and observes the outcome of the student's own action. Every student-action wait offers **Skip this step**, which bypasses dependent feedback/chat steps. Waits remain bounded at 120 seconds, and tour cleanup during student navigation no longer dismisses the walkthrough. Diagnostic and instructor controls only highlight or open UI; the standalone Tutor now also pre-fills without sending.

Sources: `src/components/shell/CourseShell.tsx`; `src/components/shell/student-tour.ts`; `src/components/shell/TourRunner.tsx`; `src/features/skill-hub/components/StudyBrowser.tsx`; `src/features/flashcards/components/FlashcardDeck.tsx`.

### Verification and handoff

- Lint: **0 errors, 18 existing warnings**.
- Typecheck: passed.
- Production build: passed, with the existing chunk-size advisory.
- Code-only regression checks: passed for partial/complete/untouched score pills; confirmed cursor and repeated queue persistence; pending-write idempotency state; storage isolation and malformed data; saved-test reuse; no-material rejection; one skill across all three tour modes; editable pre-fill without submission; skippable student-action waits; earlier repeat-loop, navigation, cache and retake checks.
- Checks used stubbed DOM/query/network callbacks against production functions. They did not open a browser or contact model endpoints. Temporary check scripts are outside the repository.

**User smoke remaining:** repeat case 7; refresh on card two of missed review and again during a repeated miss in case 9; run case 12 from an already opened ready topic, checking all three dock demonstrations without automatic submission. Also run the tour when there is no saved test and when only completed sets exist; verify student-controlled New set/Start actions and explanatory completed-set menus. Confirm each hub breadcrumb stays on the same skill.

**Closure status:** the reported frontend regressions are addressed, subject to user visual smoke. Both companion API findings are resolved per the planner and ship together with this UI. They are no longer branch-closure blockers.


## Tour writes audit — student actions only

Baseline: `80d0770`. This update removes automatic learning writes and chat requests from the tour. Read-only discovery, navigation, opening panels, local card flips and editable drafts remain permitted. Lesson navigation may load or prepare shared course lesson content through the existing GET; it never submits student evidence. The tour makes no direct save/model requests.

| Step before | Automatic action before | Behavior after |
| --- | --- | --- |
| Lesson — Check your understanding | Clicked the first choice, submitting a graded check and updating evidence, mastery and scheduling. | Highlights choices with an instruction to pick an answer; observes feedback after the student's click. Skip goes to Study without grading. |
| Test — Answer a question | Clicked the first choice, saving/grading a Test answer. | “Pick an answer to see feedback.” Waits for student input; Skip bypasses feedback/chat. |
| Test — New set | Clicked New set, creating a saved set. | Highlights New set and waits for the student's click, with Skip. |
| Test — Test sitting | Clicked Retake this set when the saved set was complete, creating an attempt. | Completed-only topics show the Test menu and explain Retake/New set. Neither is activated, and no new set is created as a fallback. |
| Study — entry | Automatically entered `start=true&mode=all`; the deck GET claims cards and records study exposure. | Opens the read-only Study menu. The student chooses Start studying/Review due/Study all; Skip bypasses the deck. |
| Lesson dock — sample follow-up | Filled and submitted a sample question automatically. | Opens the dock and pre-fills editable text without sending, preserving existing text. Next continues without a reply wait. |
| Study dock — sample follow-up | Filled and submitted a sample question automatically. | Same editable pre-fill; only the student's Send invokes Kala. |
| Test dock — sample follow-up | Filled and submitted a sample question automatically. | Same editable pre-fill; only the student's Send invokes Kala. |
| Standalone Tutor — sample question | Filled/submitted automatically, creating a conversation and sending a model request. | Editable pre-fill only; explains that Send asks Kala. The tour can continue without sending. |

Study's Still learning/Got it controls were **not clicked automatically before** and remain explanation-only. Diagnostic submission was also highlight-only and remains student-controlled. Opening an unfinished Test was previously automatic but read-only; the tour now waits for the student's Start/Continue click too, with Skip. Instructor tour clicks remain panel/tab/navigation actions.

All student-action waits expose Skip during availability waits as well as while awaiting input. Each has a 120-second limit; timeout skips dependent steps. Replies are never required after a sample pre-fill. A front-only Show answer anchor prevents a local flip step from turning into an accidental rating if the student has already flipped the card.

Verification: lint 0 errors / 18 existing warnings, typecheck and production build pass. Code-only checks cover no automatic submit/save targets, preserved drafts, Skip/timeout behavior, student-driven feedback and URL changes, and completed-only/no-set/unfinished-set tour branches. No browser, live model call, deployment or database write was used for verification. User visual smoke remains separate.
