# Frontend question-bank audit

Read-only audit against `docs/design/question-bank-design.md` (section 0 amendments take precedence; section 9 is the student contract), `apps/web/src/styles/DESIGN.md`, and the current FastAPI routers. The numbered findings are the pre-fix audit; resolution notes are recorded below.

## Summary

At the time of this audit, the frontend had not completed the bank-status migration. The numbered findings below preserve that pre-fix comparison; see the progress notes at the end for current status.

## Instructor skill proposals

1. `services/api/app/routers/dashboard.py:292-306` returns proposed skills with `id`, `name`, `bloom_level`, `blueprint_weight`, and `proposed_source`. The Zod shape in `apps/web/src/features/instructor/schema/instructor.schema.ts:61-72` matches those fields. Review at `services/api/app/routers/dashboard.py:334-368` accepts approve/reject and returns `{skillId, status}`; the UI mutation shape is consistent.
2. Proposal enqueue is asynchronous: `services/api/app/routers/diagnostic.py:169-177` returns `202 {status: "queued"}` and `apps/web/src/features/instructor/schema/instructor.schema.ts:79-83` matches it. At audit time, `SkillReviewPanel` polled for three minutes and showed generic queued copy. It did not distinguish queued from completed work, and the fixed window could end while worker work was still queued or chained. The current implementation and status contract are recorded in the instructor follow-up below.
3. The proposer records source notes including “possible overlap with this course”, “thin material: N chars”, and “possible duplicate of …” (worker implementation; API review list returns `proposed_source` unchanged). `SkillReviewPanel` only recognizes a source starting with `possible duplicate` or a warning glyph at `apps/web/src/features/instructor/components/SkillReviewPanel.tsx:256-265`. Thus plain overlap and thin-material notes do not get warning treatment. The source cell truncates the string at `:289-308`, so the full reason is only available through the native title tooltip.
4. The empty-state text at `apps/web/src/features/instructor/components/SkillReviewPanel.tsx:209-214` says a launch may have produced a partial result, although launch no longer runs proposals. Refresh is correctly the explicit action; update the explanation to describe worker-queued proposals and avoid implying a launch kicks the proposer.

## Test tab / practice session

Backend reference: `services/api/app/routers/practice.py:90-132,206-303,509-570`; bank status is `services/api/app/routers/bank.py:26-54`.

1. A bank `POST /practice/{course_id}/set` returns `200` with `setId: null`, empty `items`, and `status: "preparing"` or `"no_material"` when not usable/material is absent (`practice.py:242-269`). The Zod shape accepts those states at `apps/web/src/features/practice/schema/practice.schema.ts:16-47`, but `PracticePanel` only handles `generating` and `failed` before falling through to “Nothing to practice yet” (`apps/web/src/features/practice/components/PracticePanel.tsx:170-205`). The no-set bank response therefore renders the generic empty fallback.
2. The dedicated session hook POSTs again unless cached data has `status === "generating"` and a `setId`; it polls only `generating` (`apps/web/src/features/practice/hooks/use-practice.ts:24-53,59-70`). A `preparing` response has no `setId`, so it cannot enter detail polling. In current `TestBrowser`, that response is intercepted and the browser toggles a separate `preparing` flag (`apps/web/src/features/skill-hub/components/TestBrowser.tsx:183-192`), but this does not fix direct session/legacy-route entry.
3. TestBrowser fetches bank status only after local `preparing` becomes true (`apps/web/src/features/skill-hub/components/TestBrowser.tsx:155-158`). `useBankStatus` polls every 10 seconds when the skill is not usable and stops as soon as it is usable (`apps/web/src/features/practice/hooks/use-practice.ts:81-91`), without using the endpoint’s top-level `building` flag. It does not handle the full lifecycle from initial render, building-but-usable, no-material, or error, and `preparing` is never cleared when status changes (`TestBrowser.tsx:307-310`).
4. The bank contract defines exact per-skill states and says usable skills can create sets even while more items build; the TestBrowser only displays preparing/no-material after a failed set POST (`apps/web/src/features/skill-hub/components/TestBrowser.tsx:183-234,287-329`). It has no `building, usable` “More questions on the way” message or instructor-facing bank error path. It renders `apiErrorReason(generate.error)` directly at `:319-329`; server/provider details can therefore reach a student.
5. `TestBrowser` passes `includesRepeats` from a just-created response into the detail page (`:187-188`), and `SetDetail` displays the exhaustion banner when true (`:359-364`). But saved-set list/detail API responses do not include `includesRepeats` (`practice.py:134-166,509-570`), and the frontend schema makes it optional (`practice.schema.ts:29-38`). Reopening/retaking a set that originally contained repeats loses the banner. Also the backend picker marks repeats for a particular served set; confirm desired persistence semantics before relying on it for retakes.
6. The size picker offers only fixed values 5, 10, and 20 at `apps/web/src/features/skill-hub/components/TestBrowser.tsx:213-227`, while design section 7.2 also specifies “all unseen”. Backend currently validates only 5/10/20 (`practice.py:244-246`), so this is a design/backend discrepancy to resolve in the backend handoff if “all unseen” remains required.
7. `practiceSetProgressSchema.bankStatus` omits `status`’s enumerated values (it is any string) and requires numeric ready/target plus usable (`apps/web/src/features/practice/schema/practice.schema.ts:22-27`). The global bank status response has a `building` flag and per-skill status, counts, depth, and usable (`services/api/app/routers/bank.py:26-54`). The separate fetch schema strips/does not model optional instructor `lastError` (`practice.api.ts:79-95`). This is not a parse failure today, but weak validation loses the state contract and instructor diagnostic detail.

## Study tab / flashcards

Backend reference: `services/api/app/routers/flashcards.py:49-155`; it serves due SRS cards then database-backed bank MCQs and tracks new cards. It no longer calls a model in the bank-serving path.

1. `StudyBrowser` says the deck’s top-up generation seeds empty skills (`apps/web/src/features/skill-hub/components/StudyBrowser.tsx:15-20`) and displays “Kala couldn't write cards … Try again” with a Refresh action for a zero-card response (`:61-83`). This is stale and falsely suggests retrying a model call can fix an empty bank. No-material must instead show the specified permanent no-material copy with no retry.
2. `FlashcardDeck` shows “Building your deck — Kala is writing the first cards…” while the deck query loads (`apps/web/src/features/flashcards/components/FlashcardDeck.tsx:121-122`). The endpoint is a database read; this is old generation messaging. On a successful zero-card response, the component reports “hasn't been mapped for flashcards yet” and offers Refresh (`:131-149`) rather than using bank status to distinguish preparing, no material, and an empty SRS queue.
3. The legacy `/course/flashcards` route still exists at `apps/web/src/routes/course/flashcards.tsx:14-22`. It intentionally makes a `limit=0` peek for course-wide SRS stats, but comments claim that this avoids top-up generation. `flashcards.py:94-103` and `:139-155` should be checked against this premise: the route returns before bank selection when limit is zero, but the legacy fallback path is still present when bank serving is disabled. The route itself does not display per-skill bank state.
4. Study schemas correctly cover returned card data (`apps/web/src/features/flashcards/schema/flashcards.schema.ts:13-38`), but there is no bank-status schema/hook in the flashcard feature and no UI handling for the six section 9 states. Study currently treats successful empty deck and query error as the only non-loading cases.

## Diagnostic

Backend reference: `services/api/app/routers/diagnostic.py:483-640`. Bank mode returns ready questions plus `pendingSkillIds` and `failedSkillIds`; no-material skills go in failed IDs and skills below `MIN_USABLE` go in pending IDs. The legacy path still enqueues old per-item generation jobs.

1. The response schema matches the current backend’s main shape: `apps/web/src/features/diagnostic/schema/diagnostic.schema.ts:21-28` includes status, questions, ready count, pending/failed IDs, and skipped count. `questionSchema` requires non-null `bloomLevel` enum (`:4-19`), while backend returns `item.get("bloom_level")` (`diagnostic.py` bank/legacy question assembly), so nullable/missing Bloom data can fail parsing.
2. Diagnostic polling keys only off `data.status === "generating"` and runs every 5 seconds (`apps/web/src/features/diagnostic/hooks/use-diagnostic.ts:10-21`). The design says use `GET /courses/{id}/bank/status` and poll every 10 seconds only while its `building` is true. Diagnostic does not fetch that endpoint and cannot express skill-level building-usable versus building-not-usable states.
3. Bank mode returns `status: "ready"` whenever at least one question is ready, even when other skills remain pending (`services/api/app/routers/diagnostic.py:553-558`). The panel then shows those ready questions, but does not show a preparing indicator for `pendingSkillIds`; its only partial-result notice is for `failedSkillIds` (`apps/web/src/features/diagnostic/components/DiagnosticPanel.tsx:217-222`). If there are pending skills and no ready questions, the API returns `generating` and the panel replaces the whole surface with a loading panel (`DiagnosticPanel.tsx:117-123`). The frontend therefore misses the mixed ready/building state and does not follow the specified bank-status polling contract.
4. Failed skills render a notice saying topics “without course material” were left out (`DiagnosticPanel.tsx:217-222`), which aligns for bank `no_material`; however it only shows if questions render. If every skill is no-material, route status is `failed`, and the panel tells the student a general failed baseline message (`:124-129`) instead of the section 9 no-material wording. Network/load errors also expose `apiErrorReason` elsewhere in app features; diagnostic’s current initial query error copy is generic and safe.
5. `DiagnosticPanel` has no exhausted/repeat state banner. The bank route records diagnostic exposures and picks deterministically; a repeated item can be served after exhaustion without a frontend indication. The six-state table’s exhausted treatment should be checked against diagnostic semantics (section 7.3 explicitly describes the repeat banner for test sets; diagnostic is one question per due skill).

## Lesson checks

Backend reference: `services/api/app/routers/lessons.py:28-46` and `services/api/app/learn/lessons.py` (step checks are filled from the bank on lesson reads; `check` can be null). The endpoint still generates and stores the lesson itself on first open; bank migration applies to its check item, not to lesson prose.

1. The lesson Zod schema has only lesson lifecycle status `generating | ready | failed` (`apps/web/src/features/lessons/schema/lessons.schema.ts:31-38`) and models `check` as nullable (`:19-29`). It has no bank status fields. The lesson component uses the lesson lifecycle for a full-screen loader (`apps/web/src/features/lessons/components/LessonChat.tsx:110-124`) and treats a null check as a step that advances without assessment (`:140-145`). It does not show per-skill bank preparing/no-material/error states or poll bank status.
2. The combined SkillHub Lesson tab and legacy `/course/lessons` route both use `LessonChat` (`apps/web/src/features/skill-hub/components/SkillHub.tsx:12,158-164`; `apps/web/src/routes/course/lessons.tsx:1-36`). Thus the missing bank state handling affects both entry paths. Confirmed lesson generation remains a separate lesson job and is not incorrectly replaced by bank polling.

## Legacy route reachability

1. `/course/practice` remains registered at `apps/web/src/routes/course/practice.tsx:14-25`, and directly mounts `PracticePanel` at `:31-43`. It is still functional with the legacy `GET /practice/{id}/next` path when bank serving is off, but the bank version of `POST /set` returns `preparing` with a null set ID, which the session component currently falls through as “Nothing to practice yet”. The route is not a redirect to the new skill hub.
2. `/course/flashcards` remains registered and functional as a standalone chooser/session (`apps/web/src/routes/course/flashcards.tsx:14-23`); it calls the same deck endpoint but has no bank status UX. Its limit-zero peek is a stats-only view, not a route migration.
3. `/course/lessons` remains registered and functional (`apps/web/src/routes/course/lessons.tsx:14-36`); it loads the same lesson endpoint and therefore retains the independent lesson-generation status and null-check behavior described above.
4. The routes are registered and directly reachable, even if current navigation does not link to all of them. They duplicate the newer `/course/skills/{skillId}` combined hub. The frontend overhaul must decide whether they remain supported entry points and make their bank states correct if they stay reachable.

## Step 2 progress

### Fixed in the approved Study and Test pass

- **Skill hub entry:** bare skill URLs now default to Study, and session start preserves the selected tab. The source path confirmed the suspected `tab === "study" && start` mismatch. Chrome access was denied, so the click repro could not be confirmed live.
- **Response schemas:** required fields and types are validated; unknown fields are stripped and logged with the endpoint in development. Bank status values share one enum schema. See `schema-check.md` for the field-by-field contract table.
- **Shared bank status:** the hook is loaded on SkillHub entry and shared by Study and Test. It polls at 10 seconds only while the backend's top-level `building` flag is true.
- **Test:** bank states drive generation gating and status copy. `preparing` and `no_material` no longer fall through to “Nothing to practice yet”. The repeat banner is carried into the active session for a newly generated repeat set.
- **Study:** stale generation copy and top-up comments are removed. Empty decks now distinguish no material, a bank still preparing, and an empty SRS queue. “Test me on these” still posts the studied item IDs to the bridge endpoint, which records `quiz_set_items` before opening the saved set.
- **Product decisions:** “all unseen” was dropped, section 7.2 now lists only 5, 10, and 20. Saved-set repeat banners were dropped; generated-set metadata is not expected when reopening a set. The flashcard deck `bankStatus.usable` field is no longer modeled or read. Backend will represent approved skills without state rows as `waiting_content`.

### Instructor proposal review

- Warning labels cover possible overlap, thin material, and possible duplicate reasons; the full reason remains visible. Empty-state copy no longer implies a launch starts proposals.
- The fixed three-minute stop was removed. Polling continues until worker status reports done or failed. If the current API omits status, a 15-minute safety fallback stops polling with a message that does not claim completion; Refresh stays enabled. See `backend-handoff.md`.

### Instructor proposal review follow-up

- Warning labels now cover possible overlap, thin material, and possible duplicate sources, with the full reason visible in the row. Empty-state copy no longer says launch runs proposals.
- The panel polls for the worker's proposal status and shows a finished state. The current backend only returns `queued` from the trigger and has no completion status on the proposed-skills read, so a fallback is needed for pre-status responses. See `backend-handoff.md`.

### Deferred to the next pass

Diagnostic states, lesson check states, and the independent legacy routes remain. Backend contract decisions are listed in `backend-handoff.md`.
