# Skill hub flow review — 2026-10-18

Branch: `feat/study-lesson-ui`. Review baseline: `4d8f27a`.

## Scope and result

Reviewed the Lesson, Study, and Test surfaces; their queries and mutations; hub search parameters; old course-mode routes; Home's quick-practice entry; the shared session shell; and the student tour. Changes stay inside `apps/web`. No browser access, deployments, live model calls, or database changes were used.

The confirmed frontend defects below have been corrected. One API eligibility discrepancy remains outside the original frontend-only scope. This review does not establish that every live or visual edge case is resolved; the smoke matrix below remains for the user.

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

## Remaining API follow-up

Membership in `services/api/app/routers/flashcards.py` computes `due` and `dueToday` from timestamps for all scheduled membership items. `services/api/app/learn/srs.py` filters mastered/graduated rows out of `due_cards` using `is_mastered(box, streak)`.

Consequently, a graduated Known card with an expired timestamp can appear in membership's Due count even though Review due will not serve it. Membership supplies the client a memory band, not the box/streak eligibility fields. Excluding every Known card in the UI would also exclude eligible Known cards, so that would be an incorrect workaround.

Proposed API follow-up: use the same eligibility predicate for membership's `due`/`dueToday` and session selection, while keeping every card in the browse list. Add API cases for a graduated overdue card, an eligible overdue Known card, and a future scheduled card. This requires extending the original “apps/web only; no API or schema changes” brief and is not included in this branch.

Cards with unavailable answer labels still require bank-content repair. The UI retains the accepted Answer unavailable display and an exit; this frontend review does not repair stored answer keys.

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
14. Separately verify the graduated-card eligibility case after the API follow-up above. Do not treat the UI-only review as closing that issue.
