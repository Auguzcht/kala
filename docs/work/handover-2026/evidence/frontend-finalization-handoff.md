# Frontend finalization handoff: student and instructor

Date: 2026-10-25. Audited application revision: `47b9700`, branch `codex/ui-overhaul`, worktree `.`.

## Readiness and scope

The requested presentation changes are implemented and have local regression evidence. Kala is **not ready for unconditional live UI/UX sign-off**: instructor identity accuracy, Diagnostic availability and the reported shared AI failures still affect whether the experience tells the truth and completes its core flows. Finish these before another cosmetic pass.

This document consolidates WI-22, its directly requested shared/instructor/Twin follow-ups, and the final source review. It distinguishes completed changes, confirmed data investigations, source-confirmed open defects and acceptance still needed. It does not claim every historical Kala feature was rebuilt or every route was exercised against production. No new application fix, hosted repair, model call or teacher decision was performed for this handoff.

Authority: [AGENTS.md](../../../../AGENTS.md), [task router](../../../README.md), [APPROVAL-05](../approval-05.md), [WI-22](../work-items/WI-22-diagnostic-tutor-ui.md), [implementation and verification evidence](ui-overhaul.md). Requirements: DIAG-REQ-001–008, TUTOR-REQ-001 compatibility and TUTOR-REQ-002–011 integration, INSTR-REQ-001/002, TWIN-REQ-001/002/003. Related dependencies: WI-01, WI-08, WI-20, WI-21 and WI-23.

The final accessibility/recovery review also consulted the [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md). Kala's sentence-case copy, design tokens and Fred's explicit motion decisions remain authoritative where general guidance differs.

## Completed work

“Implemented” below means local source with the recorded checks, not a deployment to the hosted instructor site. The detailed sequence and intermediate test corrections remain in [ui-overhaul.md](ui-overhaul.md).

### Student: Diagnostic

| Area | Final behavior |
| --- | --- |
| Purpose and hierarchy | Shared PageHeader introduces what the baseline is for; no competing Study-style SessionBar. Typography matches Skills/Twin. |
| Margins | Header uses the same centered max-screen-2xl container, 24px horizontal padding below lg, 40px at lg and 32px vertical padding as Skills/Twin. Full-width separator remains. This supersedes the earlier breadcrumb-gutter alignment. |
| Question and submission layout | Question column and answered-count/Submit footer share the 800px maximum and matching inner edges. Questions scroll independently; the last answer remains reachable on mobile. |
| Selection feedback | Selected answers remain orange under a stationary pointer, leave/re-entry and keyboard focus. Neutral hover applies only to unselected choices. Selection exposes aria-pressed. |
| Submission | Shared Spinner, pending lock, preserved selections on failure and retryable submission; original answer payload/grading semantics retained. |
| Completion | Persistent Test/Study-style results panel, animated returned mastery progression, once-only confetti when motion is allowed; no automatic completion modal or repeated exit buttons/footer. One primary Back to workspace and one secondary View your twin. No invented score or answer key. |
| Refetch and revisits | Successful results win over question-query refetch/loading/empty/error changes for the mounted sitting. A fresh visit checks current availability. Status/Twin/next-up invalidation remains. |
| Other states | Loading/preparing, partial readiness, missing material, failed preparation and caught-up views retained. The availability/copy problem and inert load-error Retry remain open below. |

### Student: Tutor and history

| Area | Final behavior |
| --- | --- |
| Desktop/mobile shell | Always-open desktop history, default width 320px with 280–440px pointer/keyboard resizing and matching content offset; mobile history uses a Sheet. |
| History structure | Quiet collapsible Pinned above Recents, counts, dedicated sort icon, local newest/oldest/title sorting. Management controls depend on API capability. |
| Row actions | More actions appear on hover/focus and remain visible while open. Inline Rename, Pin/Unpin, direct pin and confirmed Delete are wired for capable responses. Unsupported responses do not attempt unsupported updates. |
| Popup placement and motion | Rounded padded sort/chat menus open toward the right on desktop and remain within mobile bounds. Both entry and exit are immediate. Sort has a quiet white trigger and an inset rounded focus treatment without the clipped square outline. |
| Long titles | A measured overflowing title moves gently to its end and returns when hovered; short titles and reduced-motion titles stay still. |
| Empty chat | Composer centered in the session viewport with greeting/mascot above it. Deterministic time/course-aware greeting; long starter suggestions removed. No name/model-cost disclosure added. |
| Conversation chrome | Removed duplicate conversation-title header and separators for a continuous reading area. Existing follow-up actions retained. |
| Dock | Shared prompt styling, circular leading attachment/Send controls, consistent line height and rounded corners. Floating dock covers the scrolling stream directly, without the previous blank strip above it; scroll-to-bottom clearance follows it. Study's text dock shares the geometry. |
| Icon motion | Published lucide-animated per-icon variants controlled by the whole button's hover/focus. The interim generic tilt/nudge/pulse wrapper was removed. Glyphs without a published variant remain static. Registry URLs/hashes are recorded in the evidence. |
| Waiting and recovery | Thinking shimmer and Still working feedback; typed safe provider/timeout errors; successful-answer/save-retry behavior retained. These UI states do not establish provider recovery. |
| Mascot motion | Scoped to the empty Tutor, stops on typing/sending, static with reduced motion. Lead-designer acceptance of the approved exception remains. |

### Student: file staging and previews

| Area | Final behavior and limits |
| --- | --- |
| Staging ownership | Native File objects live in React memory. They are not stored in localStorage, sessionStorage or IndexedDB. Refresh/remount loses unsent staged files. |
| Network boundary | Selecting/dropping a file does not create a conversation or upload. Send lazily creates the conversation if needed, uploads staged files, then asks only after the batch is ready. |
| Types and validation | TXT, MD and PDF through the existing API, up to 5 MiB per file. Image upload/vision is not supported by this backend contract. |
| Partial failure | Question and failed staged files remain available. Retry reuses successful uploads rather than uploading them again. Changing chats cancels the old composer's continuation. |
| Cards | Filename, type, size and staged/uploading/attached/failure state; subtle format accents from tokens, equal top/left insets, hover shade, keyboard/click preview and separate removal. |
| Shape and drop feedback | Finite rounded corners preserved while the dock expands for cards; drop overlay uses the published Upload animation and reduced-motion handling. |
| Local text preview | Optional dialog with bounded raw TXT/MD text (128 KiB), subtle overlay blur and short reduced-motion-aware entry/exit. No Markdown/HTML execution or adjustable editor pane. |
| Restored files/PDF | Metadata dialog opens for all cards. Actual contents are not available through the current retrieval contract; no false preview is fabricated. Images, restored text retrieval and PDF rendering are separate scope. |

### Shared, Study and Twin

| Area | Final behavior |
| --- | --- |
| Flip accessibility | Hidden flashcard faces use inert/focus handling; hidden-face focus and the related accessibility warning were corrected while preserving Study rating/replay behavior. |
| Loading indicators | Shared Spinner/LoadingRegion used for real pending operations, including student workspace/pickers, Diagnostic, Tutor, Study/Test, lesson checks, Twin and gamification; instructor plan, roster, charts, records, recommendations and proposal review/refresh. One indicator per skeleton region, static under reduced motion. Placeholder/menu ellipses and static errors do not imply activity. |
| Toast contrast | Sonner follows the resolved application theme and uses explicit readable description text. Success/error/info/warning contrast was tested. This fixes pale/white descriptions on light notifications, including badge notices. |
| Readiness rings | Student 176px and instructor 144px readiness donuts use a prominent 48px monospaced center; compact 56px skill rings retain 12px. Null/0/100 and accessible value/band labels covered. |
| Focus area | Decorative heading icon removed; skill and practice action retained. The action's lost skill context is a remaining issue below. |
| Evidence ledger | Shared ten-row pages, instructor-sized 40px controls, range explicitly labelled recent events, windowed page numbers, mobile previous/current/next, keyboard links, disabled endpoints, page clamp and learner reset. Page replacement is immediate; new-arrival reveal remains reduced-motion-aware. |
| Shell classification | Fixed raw prefix matching that treated plural /course/skills as singular /course/skill. Skills/Twin/Diagnostic match at wide widths; actual skill sessions retain full-width takeover. |

### Instructor

| Area | Final behavior |
| --- | --- |
| Skill Approve/Reject | Request starts immediately. Selected action shows Spinner and controls lock for the real request plus a minimum 350ms feedback interval. Queue refresh is included in the lock. Failure leaves a retryable proposal and explicit message. |
| Recommendation decisions | Removed optimistic cache transition that unmounted the Recording spinner immediately. Card stays mounted until validated server confirmation, then moves to history. Choice/notes lock during recording; failure preserves them for retry. No success is fabricated. |
| Learner presentation | Shared readable readiness rings and ledger pagination apply to learner record/Twin callers. Learner changes reset local ledger presentation. |
| Accuracy investigation | Traced the Alfred/Hanna discrepancy through actual enrollment, aliases, evidence/mastery and cohort.roster reads. No identity/data repair was performed. |

## Bugs encountered and disposition

Labels H01 onward are local handoff references, not newly allocated REQ/WI IDs. Existing WI/REQ ownership is preserved.

| Ref | Symptom/root cause | Disposition |
| --- | --- | --- |
| F01 | Sort used menu dots; trigger looked boxed/clipped; menus opened left | Dedicated sort, inset focus, rightward bounded menus implemented. |
| F02 | Popup exit still animated after entry override | Direct Tutor-menu animation/transition override covers both states. |
| F03 | Chat More trigger disappeared after click | Open-menu state now retains row actions. |
| F04 | Missing Rename/Pin/Pinned section | UI implemented; live availability still depends on list/PATCH capability, H04. |
| F05 | New-chat composer vertically offset; dock had an empty strip above it | Centered empty composer and floating shared dock geometry implemented. |
| F06 | Generic icon motion did not follow the requested lucide variants | Generic wrapper removed; published per-icon sources used. |
| F07 | Attachment expansion distorted corner shape; upload started before explicit send | Finite corner styling and memory staging until Send implemented. |
| F08 | Restored file could not hover/click | Noninteractive div replaced by preview button; metadata fallback explicit. |
| F09 | Attachment top/left inset uneven; formats indistinct | Card inset and token-based format accents corrected. |
| F10 | Sonner descriptions nearly white on white | Resolved theme and explicit muted-foreground text corrected. |
| F11 | Selected Diagnostic answer looked unselected while pointer remained | Unconditional neutral hover removed from selected choice. |
| F12 | Diagnostic completion modal + duplicate Back buttons/footer | Replaced with one persistent result panel and two distinct destinations. |
| F13 | Refetch could replace just-submitted mastery reveal | Success view has precedence; question invalidation avoids immediate refetch. |
| F14 | Question/footer/header spacing inconsistent; wide Skills margin still wrong | Final content gutters aligned; segment-aware shell matching corrected. |
| F15 | Instructor actions appeared instantaneous; recommendation Spinner vanished | Pending presentation retained, 350ms minimum; optimistic card removal removed. |
| F16 | Readiness value tiny inside large donut; long ledger required scrolling | Responsive center size and ten-row recent-window pagination implemented. |
| F17 | Flip card retained focus in hidden face | Inert and deliberate focus handling implemented. |
| H01 | Instructor records show another identity's history | Confirmed, open; detailed trace below. |
| H02 | Workspace says five baselines due when zero questions are selectable | Confirmed, open; detailed trace below. |
| H03 | Shared AI help returns provider 502 / reported 503 | Existing P0 dependency; diagnostics work elsewhere is not a recovery claim. |
| H05–H12 | Recovery, navigation, keyboard and bounded-data findings from final review | Open; source locations and acceptance below. |

## High-priority trace H01: Alfred Nodado and Hanna Sato

Priority: **P1 data correctness / sign-off blocker**. Owner: backend identity/LTI plus a named maintainer for reviewed data repair; frontend validates the corrected result. This is not fixable with a label change, cache invalidation or client-side name matching.

### Observed evidence

Tenant/course-scoped read-only investigation on 2026-10-25 reproduced the hosted instructor screenshot with the actual cohort.roster function. It returned 25 enrolled learners, Hanna as not-started with zero attempts, and Alfred as needs-support with 40 older attempts.

| Learner | Identity selected by roster enrollment | Active identity used in student testing |
| --- | --- | --- |
| Hanna Sato | 0 course evidence, 0 mastery rows, 0 attempts | 384 evidence events: 42 Diagnostic, 89 Tutor, 118 practice, 135 flashcard; 12 mastery rows / 384 attempts; **no course enrollment** |
| Alfred Nodado | 40 older practice events; 2 mastery rows / 40 attempts; last event 2026-10-11 UTC | 13 recent events: 6 Diagnostic, 5 practice, 2 flashcard; 7 mastery rows / 13 attempts; last event 2026-10-24 21:55 UTC; **no course enrollment** |

These are investigation-time counts, not a live counter. Within each pair the normalized emails matched. The enrolled record used Blackboard's internal REST identifier; the active record used a different LTI identifier. Both already had separate alias mappings. Raw emails, UUIDs, LMS identifiers, answers and credentials are deliberately omitted.

### Execution path

1. Student LTI launch resolves the active alias and writes evidence/mastery under that user. The history exists; it has not vanished.
2. [resolve_user](../../../../services/api/app/db/supabase.py) at **139–154** returns an existing alias match before reaching same-email discovery at **156**. Email fallback helps a new unmatched identifier; it does not merge a pair of already-established aliases.
3. Instructor roster synchronization calls the same resolver for the REST identifier: [lti/routes.py](../../../../services/api/app/lti/routes.py) at **126–145**. The REST alias resolves to the other user and that user is enrolled.
4. Synchronization reconciles enrollments using those REST-resolved IDs at **156**. An unmatched active LTI user's enrollment can be removed. Simply launching the student again is therefore not a durable repair.
5. [cohort.student_ids](../../../../services/api/app/twin/cohort.py) at **60** includes only enrolled course/tenant students, with both enrollment and user role checks. The active non-enrolled IDs do not enter this set.
6. [cohort.roster](../../../../services/api/app/twin/cohort.py) at **195** loads identities, mastery and evidence for that set. Mastery joins at **140**, evidence at **152**. The browser receives the enrolled identities' metrics and renders them accurately, but they are the wrong histories for the tested people.

This establishes the current mechanism; it does not establish the exact historical commit or moment that first created the duplicate records.

### User impact

- Instructor roster, readiness/accuracy, last activity and support classification disagree with student testing.
- Hanna can be described as having no engagement even after hundreds of events.
- Alfred's recent Diagnostic/practice is absent from the displayed enrolled record while his older history remains on it.
- Cohort summaries and recommendations built from these identities can be misleading. The displayed zero-attempt outreach recommendation must not be treated as trustworthy evidence of disengagement.

### Required repair and acceptance

1. A maintainer reviews tenant/course-scoped candidate pairs and chooses a canonical identity from verified LMS identity evidence. Matching names alone is insufficient; matching email alone must not become an unrestricted automatic merge rule.
2. Inventory current referencing tables and collisions before choosing a migration/repair procedure: aliases, enrollments, append-only evidence, mastery/SRS, attempts/sets, exposures, conversations/attachments, recommendations and derived snapshots/state as applicable.
3. Preserve both histories, especially Alfred's two nonempty histories. Reconcile aliases and enrollment together; recompute derived state as required rather than naively overwriting mastery rows.
4. Existing [merge_duplicate_user.py](../../../../scripts/merge_duplicate_user.py) is historical repair tooling, **not an approved ready-to-run repair for the current schema**. Review its table/collision coverage first. Agents do not apply hosted repairs.
5. Verify student-first then instructor launch, instructor-first then student launch, and repeat roster sync. Both identifiers must continue resolving to the same canonical person, with correct enrollment and no new duplicates.
6. Reconcile student Twin with instructor roster, learner record, last activity, measured skills and evidence counts at the same scope/window. Confirm both histories remain and no additional XP/evidence is created merely by opening the views.
7. Review stale recommendations after repair; recompute/regenerate only through the approved instructor process. Do not automatically assign anything to a learner.
8. Retain tenant/course isolation, role exclusions and negative access tests. Do not loosen enrollment filtering to mask the split.

## High-priority trace H02: five baseline skills, zero actionable questions

Priority: **P1 core-flow correctness**. Owner: Diagnostic/bank API and product contract; frontend consumes the explicit availability state.

The fresh workspace still showed five after the completed sitting. Read-only investigation confirmed saved Diagnostic evidence and existing status invalidation; this was not lost answers or merely a stale badge.

| Check | Investigation result |
| --- | --- |
| Approved skills | 14 |
| Distinct skills with Diagnostic evidence after the sitting | 9 |
| Remaining never-diagnosed skills | 5 |
| No-material among remaining | 4: two service/deployment-model skills, EC2 troubleshooting, cloud architecture design |
| Fifth skill | Cloud computing essentials; bank ready with 12 approved live MCQs, all previously tested by this learner |
| Read-only pick_diagnostic_item result for fifth skill | None |
| Currently selectable remaining Diagnostic questions | 0 |

Source chain:

1. [diagnostic.py:461](../../../../services/api/app/routers/diagnostic.py) defines due as approved skills without this user's type=diagnostic evidence.
2. The status endpoint at **504–522** returns that count, without readiness/material/exposure availability.
3. [workspace:67](../../../../apps/web/src/routes/course/index.tsx) renders it as “new skills need a baseline” and offers Take diagnostic.
4. Diagnostic selection at **541** limits to ten candidates **before** checking availability. At the earlier eleven-due state, six returned questions and four no-material candidates occupied that first slice; the eleventh candidate was outside it.
5. No-material and exhausted candidates go into failedSkillIds at **555–572**. [bank/serving.py:79](../../../../services/api/app/bank/serving.py) only returns an approved item without last_tested_at; a fully tested pool has no fallback.
6. The frontend's generic failed view at [DiagnosticPanel.tsx:108](../../../../apps/web/src/features/diagnostic/components/DiagnosticPanel.tsx) describes question creation failure. That is misleading for the exhausted-ready-bank case.

Required resolution: distinguish never-diagnosed totals from actionable/preparing/unavailable/exhausted availability; filter available candidates before the sitting limit; deliberately define the baseline policy for already-tested pools; align dashboard badge/action and terminal copy. Never mark skipped skills diagnosed merely to clear the notice.

Acceptance: mixed no-material/ready/preparing/exhausted fixtures, more than ten due skills, failed-generation retry, all-answered refetch, empty course and completed sitting; workspace action must lead to something actionable or explain the real unavailable reason. Preserve saved evidence and test exposure rules.

## High-priority dependency H03: shared Tutor provider failure

Priority: **P0 in APPROVAL-05**, still requiring live recovery evidence. Owner: provider/API lane and maintainer, with frontend acceptance afterward.

Reported broken surfaces: Study hint, Explain more, Study dock, Review-missed dock and Test dock. They share /tutor/ask; persistent Tutor and Lesson help also use that boundary. Review missed uses FlashcardDeck's same serializer, not a separate AI endpoint. Retrieval/embedding precedes chat, so a request can fail before any chat fallback.

The separate local `codex/tutor-provider-502` lane at `7f484bb` records primary OpenRouter chat HTTP 429 in the investigated window; fallback failure status remained unclassified in the historical logs. Successful observed requests took roughly 7.8–14.7s, but no row identified the Explain-more action, so those are not measured Explain-more-specific latency results. An unexplained browser 503 needs route/time/code correlation; it must not all be labelled a provider 502.

That lane implements privacy-safe stage/provider/model/status/request correlation and reports **515 offline API tests passing**. It changes diagnostics, not model selection/fallback policy or account configuration. This handoff read that lane's evidence; it did not merge it, rerun its tests, deploy it or establish recovery. Health 200 and frontend synthetic answers are insufficient acceptance.

Follow-up: integrate approved diagnostics through the coordinator, identify the fallback failure with sanitized metadata, have the maintainer correct the cause, then record successful real clicks for every affected help shape, timeout/unavailable recovery and saved-answer behavior. No raw provider bodies, prompts or credentials in screenshots/log reports. Do not solve this by adding extra frontend retry loops, artificial waiting or unapproved streaming work.

## API integration dependency H04: live Rename/Pin capability

Priority: **P1 release integration**, WI-21 / TUTOR-REQ-002/003. UI accepts an optional/nullable pinnedAt. [supportsConversationManagement](../../../../apps/web/src/features/tutor/lib/presentation.ts) checks field presence, including null. The previously observed live list omitted it, correctly hiding unsupported management actions.

Separate local API branch `codex/tutor-conversation-api` at `0ccbb22` is not proof of a deployed API or applied migration. Coordinator must integrate the API/OpenAPI/generated-type and UI contracts; Fred alone applies reviewed migration 0037 and releases hosted services. Then verify rename persistence, pin/unpin, pinned order, legacy response compatibility, deletion, stale list refresh, ownership/tenant rejection and desktop/mobile focus. Never remove the capability gate just to make controls visible.

## Remaining source-review findings

These were found during this finalization review and **are not fixed in 47b9700**. Source-confirmed behavior is separated from unexecuted browser acceptance. Resolve through the feature owner/spec process; the report does not authorize hosted mutations.

| Ref / priority | Source location | Finding and required acceptance |
| --- | --- | --- |
| H05 / P2 | DiagnosticPanel.tsx:79 | Load-error Retry is a Button without onClick. Wire the query refetch/reset path; force a failing GET, activate Retry by pointer and keyboard, recover without page reload and preserve appropriate state. Submission retry is a different, already-wired flow. |
| H06 / P2 | RosterTable.tsx:342/354/361; SkillReviewPanel.tsx:398/410/417; TwinBody.tsx:147/154/163; ui/pagination.tsx:54 | These older pagers render anchors without href or tabIndex; controls are not normally Tab-focusable. Endpoints use pointer-events/opacity without explicit disabled semantics. Match the new ledger's keyboard behavior and endpoint semantics, preserving 40px sizing. Test multiple pages, filters/shrinking queues, keyboard and mobile. |
| H07 / P2 | routes/course/skills.tsx:20/31; TopicLanding.tsx:64 | Skills consumes data/isLoading but not isError, then passes [] on failure. TopicLanding displays No skills mapped yet, conflating failed retrieval with an empty course. Lessons/Practice/Flashcards legacy pickers have the same pattern. Add distinct error/retry handling and test rejected fetch vs genuine empty data. |
| H08 / P2 | TwinBody.tsx:342 | Focus area's Practice this navigates to /course/practice without the shown skillId. The student reaches a general chooser rather than that skill. Route to the canonical Test browse pane for focus.skillId; verify the destination name/skill, browse-vs-start choice and Back behavior. No automatic sitting should be introduced without deliberate intent. |
| H09 / P2 | routes/__root.tsx:33/54 | Root error and not-found CTAs always send /course, including instructors. Select /class for staff session recovery and /launch when unauthenticated as appropriate; test each role and missing course. This is a navigation issue, not evidence of an authorization bypass. |
| H10 / P3 | routes/index.tsx:12/16 | Public / still exposes Scaffold ready plus developer CLAUDE/template instructions. Replace with an intentional launch/help entry or role-aware destination; Kala remains LMS-launched, not a new password signup. |
| H11 / P3 | routes/session-expired.tsx:19/22; routes/launch.tsx:372 | Expiry copy suggests a standalone sign-in although the route has no such flow. Re-launch navigates to /launch, which cannot mint a fresh LMS token by itself. Make the instruction/CTA destination honest and test real expiration from an embedded/new-tab Blackboard launch. |
| H12 / P2 contract review | twin/cohort.py:153/225/528/551; LearnerStanding.tsx:83 | Recent-window counts can read as lifetime statistics. Roster evidence is capped class-wide at 2,000; learner-record statistics read at most 200 events and return only 25 ledger rows. Last-active/accuracy can be truncated by those windows. Establish explicit count/window semantics and aggregation/paging requirements; do not attribute H01 to truncation, since its identity split was separately reproduced. |

Source paths for this table are under apps/web/src unless prefixed twin/cohort.py (services/api/app). Full paths and ownership are discoverable from the adjacent source links above and the route inventory below. The pagination and error issues were identified from the current JSX/query paths; this report did not execute a new exhaustive browser accessibility suite.

### Correction to earlier evidence-window wording

The previous WI-22 evidence/spec said the instructor record supplies at most 200 ledger events. **The source actually reads 200 internally but serializes only events[:25]** in cohort.py:551. Student Twin returns at most 20. Instructor StudentDrillDown uses the Twin response, while LearnerRecord uses the 25-row record response. The ledger can handle 200 supplied synthetic events, but that test does not prove a 200-event live response. The focused Twin spec's observed API description is corrected with this handoff; historical evidence is retained with this explicit correction. Full-history server pagination remains unimplemented.

## Route and stale-path inventory

| Route | Current purpose / finalization action |
| --- | --- |
| /launch | LMS token/session capture, role routing and loading. Test first/returning launch, missing token, invalid/expired token and missing course. A plain frontend link cannot perform a fresh LMS launch. |
| /course | Student workspace, due-baseline notice, next-up, instructor assignments and tour entry. H02 blocks truthful availability; verify notification/assignment destinations after identity repair. |
| /course/diagnostic | One sitting, terminal preparation/empty states, persistent results. H05 load retry still open. |
| /course/skills | Canonical skill chooser. Wide-screen prefix bug fixed; H07 fetch failure still open. |
| /course/skill/$skillId | Canonical Lesson/Study/Test hub. tab selects mode; Study/Test browse before start; setId/sessionId/attemptId and missed-item parameters preserve context. Tab switching clears session start; Lesson exit returns to Study browse. Preserve this rather than reintroducing three independent main destinations. |
| /course/lessons | Retained per-mode picker; chooses canonical skill hub with tab=lesson. Not a missing route or safe deletion candidate merely because it is absent from the rail. Error/empty copy needs review. |
| /course/practice | Legacy Test picker/bridge. skillId/setId redirect to canonical tab=test using replace. Without a skill it still renders the older Practice chooser and one-item/graded-reps copy. Audit that copy against actual saved-set Test behavior. Twin's H08 currently lands here without context. |
| /course/flashcards | Legacy per-topic Study chooser plus a course-wide due-review deck. It still has a distinct local session path; retain or explicitly consolidate after validating course-wide review, not by blanket deletion. |
| /course/tutor?conversation=… | Canonical persisted chat context. New-chat/drop does not write until Send. Stale/deleted/foreign IDs, Back/Forward, history refresh and expired-session handling still need live acceptance. |
| /course/twin | Student mastery/evidence. Shared ring/ledger polished. H08 practice destination and H12 count semantics remain. |
| /class | Instructor KPIs, roster, triage sheet, support list, trends/heatmap and skill mapping/review. Existing data depends on correct identity enrollment, H01. |
| /class/student/$uid | Full learner record, decision center, mastery/activity tabs. Verify direct link and roster-sheet/full-record transitions for same learner, access denial and stale IDs. |
| /session-expired, /unauthorized | Retained recovery states; copy/launch behavior and return destination need the role-aware pass. |
| Unknown path / root error | Existing SystemState; H09 role-aware destination needed. |
| / | Remaining scaffold page, H10. |

Other stale material to reconcile: routes/course/tutor.tsx:22 still says the conversation title lives in SessionBar, which this UI intentionally removed. WI-22's initial introduction/starter/upload instructions and earlier evidence paragraphs describe superseded iterations. Use the latest Diagnostic amendment and this consolidated final behavior, then have the coordinator update their exclusively owned Tutor/DESIGN text. Do not treat stale comments or old screenshots as a requirement to restore rejected UI.

Student/instructor tour configuration still exists, with contextual skill-tour steps and no-write behavior expected. This review inspected routes/selectors but did not replay every data-dependent tour branch. A completed Diagnostic has no answer-card target; empty rosters/recommendations likewise change available tour targets. Rehearse skip/fallback, Esc/back and no-write behavior in those states before sign-off. Do not assert that all old tour targets are broken merely because layouts changed.

## Flows still needing final acceptance

These are coverage requirements, not claims that every item is a newly discovered bug. Use a reviewed test tenant and the correct canonical accounts after H01. Record frontend SHA, API version, applied migration set, device/viewport, motion preference, role and sanitized pass/fail evidence for each run.

| Surface | Required walkthrough |
| --- | --- |
| Launch/session | First/returning LMS launches for both roles; expiry during a request; fresh LMS relaunch; wrong-role, missing course, unknown route and Back/Forward. No token in captures. |
| Workspace | Baseline due vs genuinely available vs preparing/no material/exhausted; next-up destination; instructor-assigned work and empty state; loading/error/refresh. |
| Diagnostic | No approved skills; no material; worker preparing; mixed ready/pending; more than ten due; all tested pool; network load error/Retry; changing selections; failed/double submit; success/refetch/revisit; long prompt/last option reachable. |
| Lesson | Missing/stale skill, generation pending/failure/reopen; checks and retry; hint/Explain more/follow-up success/failure; final step and exit to hub. |
| Study | Review-due vs all/fresh mode; empty/caught-up vs failed load; flip focus; ratings and replay; missed-only review; completed/mastered deck; no accidental rerating on navigation; hint/Explain more/dock and bottom clearance. |
| Test | Existing set, newly generated set, retake, saved result, interrupted/reloaded URL and Back; submit failure/duplicate lock; results/confetti; Review missed and Study missed retain exact items; follow-up provider recovery. |
| Tutor | Empty/new session, first Send, persisted conversation, rename/pin/unpin/delete and failure, API capability off/on, long titles, resize/mobile Sheet, URL history, provider timeout, saved-answer retry, deleted/foreign ID. |
| Files | Select/drop TXT/MD/PDF, uppercase/unsupported/oversize/zero-byte, multiple/duplicate names; raw local preview vs restored metadata; remove; upload partial failure/retry; conversation switch during upload; refresh loses staged files; text and no-text Send; no upload before Send. |
| Twin | Empty/partial/null/0/100, estimates vs evidence windows, large skill lists, focus CTA, evidence pagination, learner switch, mobile wrapping, reduced motion. |
| Instructor roster | Correct Alfred/Hanna canonical data, other enrolled learners, real empty vs fetch failure, search/filter/sort/pagination, de-identification, triage vs full record, same learner across tabs, no wrong-person UI remnants. |
| Instructor decisions | Fast/slow/failing Approve/Reject; modify/decline with notes; recording lock, exactly one request, failure retained for retry, confirmed history; stale queue/permission rejection; no learner work before confirmation. |
| Instructor analytics | Trends/heatmap/Bloom/weakest-skill consistency, zero evidence vs null values, long names, 25+ learners, bounded-count labels, refresh and privacy toggle. |
| Tours | Student and instructor, no target/missing material/completed session, skip/back/Esc, desktop/mobile; browsing a tour never submits answers, approvals or assignments. |
| Global accessibility | Keyboard-only navigation and visible focus, screen-reader busy/error feedback, restored dialog focus, pagers, 200% zoom, long content and touch-sized controls. |
| Layout/theme | 375px, tablet, 1440px and 1920px; mobile virtual keyboard/safe area, dock/last-message visibility, dark/system theme changes, toast contrast, reduced motion and slow requests. |

No broad additional redesign is required to run these checks. The final polish should prioritize functioning recovery, contextual navigation, legible/null-safe data and consistent controls. Image upload, rendered PDF/restored-file content previews, adjustable preview panes, full-history evidence pagination and streaming are explicit future scope, not defects to conceal with mock UI.

## Integration and ownership handoff

| Order | Owner / action | Completion evidence |
| --- | --- | --- |
| 1 | Coordinator records exact branches, API deployment and migration state; reviews/integrates local UI, provider diagnostics, auth and conversation-management dependencies under existing approvals | Named revision set and normal integration checks; no assumption that local HEAD equals hosted /class |
| 2 | Identity/LTI owner + maintainer prepare and execute approved H01 repair | Both identities converge durably after repeated LMS launches/sync; both histories retained; student/instructor records agree |
| 3 | Diagnostic/bank owner specifies H02 availability and selection policy; frontend uses resulting contract | Correct actionable badge/action/copy, mixed/capped/exhausted regression fixtures |
| 4 | Provider owner/maintainer establish H03 recovery; coordinator integrates H04 API capability | Sanitized real help success/recovery evidence; live ownership-safe rename/pin checks |
| 5 | Frontend owner fixes H05–H11; backend/product clarify H12 window semantics | Focused error, keyboard, navigation and count tests; no unrelated grading/auth changes |
| 6 | Frontend + Fred run the acceptance matrix on the agreed release | Recorded role/device/state results and screenshots without private learning content or credentials |
| 7 | Coordinator reconciles Tutor/DESIGN amendments and focused Twin/Instructor specs with WI-08; lead designer reviews the two scoped exceptions | Specs describe the final accepted UI, remaining work honestly planned/deferred; no silent ownership overlap |

Keep one dev server on 5173; test from the worktree that changes source. Agents prepare changes/checks but do not merge, push, deploy, apply hosted migrations or perform hosted identity repairs under this handoff. The report is prepared for the frontend/coordinator; no message was sent to another chat or external recipient.

## Verification ledger and reproducibility

| Evidence | Revision / result / limitation |
| --- | --- |
| Retained Tutor/Diagnostic/shared browser suite | `47b9700` source: **219 assertions passed**, 1440/375 plus 1920 geometry checks. Real components with synthetic API/auth interception; non-localhost traffic blocked. |
| Twin/ledger browser suite | `47b9700` source: **148 assertions passed**, including both shared student/instructor callers, reduced motion and synthetic large supplied lists. Does not prove live history depth. |
| Instructor review browser suite | `fc75b6c`: **63 assertions passed**, fast/slow/failure/retry, confirmed transitions, keyboard and reduced motion. This is recorded prior evidence; not rerun for this documentation-only audit. |
| Frontend unit checks | Latest recorded completion pass: **21 tests passed** for Tutor recovery/schema/errors/presentation; earlier iterations had different totals. Do not sum assertions across revisions. |
| Study renderer checks | **4 tests passed** after continuation/waiting changes. Existing external renderer/experimental VM notices remain. |
| Web quality gates | Latest presentation change: lint passed with 0 errors / 18 existing Fast Refresh warnings; typecheck passed with existing route-generator warning; build passed with existing chunk-size warning. |
| Backend/provider | Separate lane reports 515 offline API tests; not this UI branch's live acceptance or a new run here. |
| Data traces | Existing 2026-10-25 scoped SELECTs, read-only bank selection and actual cohort.roster reproduced H01/H02. No new hosted access for this report. |
| Current handoff audit | Read current routes, query/error paths, pagination primitives/callers, identity/LTI/cohort/Diagnostic selection source, current specs/evidence and separate provider lane evidence. New findings are source review; no product mutation. |

Browser commands (server must already be running on 5173):

```sh
KALA_BROWSER_TEST_DEPS=/Users/fred/.cache/codex-runtimes/codex-primary-runtime/dependencies/node \ # local only, not retained
KALA_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \ # local only, not retained
node apps/web/src/features/tutor/tests/ui-overhaul.browser.mjs

KALA_BROWSER_TEST_DEPS=/Users/fred/.cache/codex-runtimes/codex-primary-runtime/dependencies/node \ # local only, not retained
KALA_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \ # local only, not retained
node apps/web/src/features/twin/tests/presentation.browser.mjs

KALA_BROWSER_TEST_DEPS=/Users/fred/.cache/codex-runtimes/codex-primary-runtime/dependencies/node \ # local only, not retained
KALA_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \ # local only, not retained
node apps/web/src/features/instructor/tests/review-feedback.browser.mjs
```

Current implementation milestones: `543a488` Diagnostic/flip focus; `423579e` Tutor presentation; `2aa449c` dock/history correction; `75ff72a` Tutor finishing; `f87bbf0` local staging/raw previews; `bd5cff0` attachments/toasts; `6e368ae` Diagnostic introduction/hover; `fdef8d4` completion/loading; `fe6a70b` baseline investigation; `fc75b6c` instructor feedback/identity trace; `47b9700` final margins/readiness/ledger. This list is provenance, not permission to cherry-pick without reviewing dependencies.

## Audit report

Task / brief ID: WI-22 final frontend UI/UX audit and student/instructor handoff; related WI-01/08/20/21/23 dependencies.
Branch and worktree: codex/ui-overhaul; /Users/fred/.codex/worktrees/2e93/kala. (local only, not retained)
Base revision: 47b9700.
Files changed: this handoff; ui-overhaul.md handoff/correction entry; focused Twin spec observed-response correction.
REQ / WI IDs touched: DIAG-REQ-001–008, TUTOR-REQ-001–011, INSTR-REQ-001/002, TWIN-REQ-001/002/003 referenced; WI-22; no new requirement IDs allocated.
Commands run and results (tests, lint, typecheck, build): source/route/evidence review; final relative-link and diff-whitespace checks recorded in ui-overhaul.md. No application test/build rerun for documentation-only work; existing revision-specific results above.
Spec changes made: correct observed instructor ledger response cap from 200 to 25, distinguishing the internal 200-event read; no intended UI/API behavior change.
Evidence added: consolidated completed-work/bug register, high-priority identity and Diagnostic traces, provider/API dependencies, remaining source findings, route inventory, acceptance matrix and ownership handoff.
Anything not done, and why: no runtime fixes requested in this audit, no new live acceptance, identity repair, API integration, hosted write, merge, push, deploy or migration. No message sent externally or to another task.
Risks or questions for the planner: H01/H02/H03 remain release-signoff blockers; frontend recovery/navigation/keyboard fixes and observed count-window semantics remain open; live capability and specification integration require their existing owners.
Secrets printed: none (confirmed).
