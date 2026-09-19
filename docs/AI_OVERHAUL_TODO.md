# AI frontend overhaul — staged TODO

Tracking doc for the Lessons/Tutor/Practice/Flashcards/Diagnostic
unification onto one stream primitive. Companion to the plan discussed in
chat; this is the checklist so the work doesn't drift mid-stage. Update
checkboxes as each stage lands, don't start a stage before the previous
one is checked off and reviewed.

## Ground truth (verified against the repo before this doc was written)

- `apps/web/src/components/ai-elements/` already has `conversation.tsx`,
  `message.tsx`, `prompt-input.tsx`, `reasoning.tsx`, `shimmer.tsx`.
  Nothing imports any of them yet.
- Every dependency they need is already in `package.json`: `ai@7`,
  `streamdown@2`, `@streamdown/{cjk,code,math,mermaid}`,
  `use-stick-to-bottom`, `nanoid`, `@radix-ui/react-use-controllable-state`.
  **This overhaul adds zero new dependencies.**
- `prompt-input.tsx` already has a full attachment system:
  `AttachmentsContext` (`files/add/remove/clear/openFileDialog`),
  `PromptInputProvider`, drag-drop, paste, screenshot capture. File
  uploads are mostly a backend problem (Stage 4), not a frontend one.
- `message.tsx`'s `MessageResponse` wraps `Streamdown` with code/math/
  mermaid/CJK plugins — real markdown + streaming, which the current
  hand-rolled bubbles in `LessonChat.tsx` don't have.
- `QuizBlock` is **not new work**, it's the existing `AnswerableCard`
  (`components/study/AnswerableCard.tsx`), recognized as the one shared
  quiz-card component. Do not rewrite it. It carries real hardening from
  batches 2–3c (delayed spinner, disabled-during-pending, tour anchors).
- `StudySessionShell` stays as the floating nav (back/progress/right-slot).
  Don't replace it, wrap the new stream inside it.

## Non-negotiable guardrails (check every stage against these before merging)

- [ ] No backend regression. Server-side grading, per-student diagnostic
      eligibility (`evidence_events`-based), `skill_id` validation/404s,
      SRS scoping from batches 2–3c stay exactly as shipped.
- [ ] Every `#tour-*` DOM anchor still exists after the change (the
      student tour selects by id — grep for `tour-` before and after each
      stage and diff the list).
- [ ] `AnswerableCard` is wrapped, not forked. If a surface needs
      something `AnswerableCard` can't do, extend its props, don't build
      a parallel component.
- [ ] Each stage gets its own DeepSeek review pass before the next stage
      starts. Don't stack unreviewed stages.

---

## Stage 1 — Foundation + Lessons

Goal: build the shared stream, prove it on the surface with the most
invasive change (modal → inline), touch nothing else.

- [ ] `components/study/StudyStream.tsx` — wraps `Conversation` /
      `ConversationContent` / `ConversationScrollButton` from
      `ai-elements`. Renders inside `StudySessionShell`, not instead of it.
- [ ] `components/study/TeachingBlock.tsx` — extracted from
      `LessonChat.tsx`'s existing `TeachingMessage` (summary, detail
      bullets, misconception callout, key takeaway), rebuilt on `Message` /
      `MessageContent` / `MessageResponse` instead of the hand-rolled
      bubble divs. Keep the actual copy/structure, this is a component
      swap, not a rewrite of what it says.
- [ ] `LessonChat.tsx`: remove the `Dialog`-based comprehension check.
      Comprehension check renders as the next `QuizBlock` (`AnswerableCard`)
      **in the stream**, not a popup.
- [ ] Gating unchanged: `result.advance` is still what allows continuing,
      still server-decided, still nothing the client can bypass.
- [ ] Replace the hand-rolled `scrollRef.current.scrollTop = scrollHeight`
      effect with `Conversation`'s built-in stick-to-bottom behavior.
- [ ] Confirm every `#tour-lesson-*` anchor still resolves (currently:
      `tour-lesson-generating`, `tour-lesson-explain`, `tour-lesson-continue`,
      `tour-lesson-check`, `tour-lesson-check-feedback` — grep
      `student-tour.ts` for the authoritative list before starting).
- [ ] Manual test: full lesson start-to-finish, wrong answer → retry path,
      hint request, reduced-motion.
- [ ] DeepSeek review. Do not start Stage 2 before this is signed off.

## Stage 2 — Tutor + persistence

Goal: tutor gets real conversation history and joins the same stream.
This is the one stage with a schema change.

- [ ] Migration `packages/db/migrations/0010_tutor_sessions.sql`:
      `tutor_conversations` + `tutor_messages`, RLS scoped to the owning
      student, default-deny matching the pattern in `0002_rls.sql`.
      **Actually run this against Supabase**, committing the file isn't
      enough, this is exactly the step flagged earlier as easy to miss.
- [ ] Backend: conversation CRUD (list/create/append) in a new or extended
      tutor router. `/tutor/ask` becomes conversation-aware
      (`conversation_id` in, appends both turns).
- [ ] Frontend: `components/study/UserBlock.tsx` (student's own message,
      `Message` with `from="user"`).
- [ ] Frontend: `components/study/FollowUpChips.tsx` wrapping `Suggestion`
      (from shadcn.io/ai — not yet vendored, check before assuming it's
      installed the way the other five are), wired to the **already-
      existing** `default`/`eli5`/`detail` styles in
      `services/api/app/routers/tutor.py`'s `_STYLE_HINTS`. Nothing
      currently calls these from the UI, this is real, not cosmetic, new
      wiring.
- [ ] `PromptInput` (from `ai-elements`) replaces `TutorChat.tsx`'s current
      input. Attachment UI can render here but stays disabled/hidden until
      Stage 4's backend exists, don't half-wire uploads early.
- [ ] A conversation list/switcher somewhere in the tutor surface (new UI,
      doesn't exist today in any form).
- [ ] Decide and record: is `ConversationDownload` (export thread to
      markdown, already built into `conversation.tsx`) wanted here? If
      yes, wire it. If no, note that decision here so it isn't re-litigated.
- [ ] Manual test: start a conversation, close and reopen the tutor,
      confirm history persists. Ask a follow-up via each chip style.
- [ ] DeepSeek review.

## Stage 3 — Unify the quiz surfaces

Goal: Practice, Flashcards, Diagnostic adopt `StudyStream`. Highest
regression risk relative to already-shipped, reviewed work — goes last.

- [ ] `PracticePanel.tsx` on `StudyStream`, single `QuizBlock` at a time.
      Topic-picker decision from the prior round (Lessons-style two-step
      landing) applies here regardless of this stage, don't let the two
      efforts collide, confirm sequencing before starting.
- [ ] `FlashcardDeck.tsx` on `StudyStream`, `QuizBlock` carries SRS
      metadata (box, due state) as additional props, not a fork.
- [ ] `DiagnosticPanel.tsx` on `StudyStream`, batch-silent `QuizBlock`
      sequence, reveal stays a reveal (no per-question correctness, that
      product decision from the diagnostic rethink stands).
- [ ] Re-run the full batch 2–3c manual test checklists (they're in the
      earlier CHANGES.md files) against the migrated versions, not just
      new tests. This stage's whole risk is silently breaking prior work.
- [ ] DeepSeek review.

## Stage 4 — File uploads

Goal: student-facing uploads. Frontend is largely already built (Stage 2
wired the UI, just disabled). Real work is backend + one product decision.

- [ ] **Decide first, before building**: are student uploads private study
      aids, or do they enter the shared RAG corpus? Can an upload move the
      twin the same way ingested LMS content can? Kala's stated source of
      truth is the LMS, this needs an explicit rule, not a default.
- [ ] Storage bucket + RLS policy for uploaded files, scoped to the
      uploading student (or institution, depending on the decision above).
- [ ] Upload endpoint, extraction into the existing chunk/embed pipeline
      (same shape as `routers/diagnostic.py`'s ingest path, reuse it, don't
      duplicate the chunking/embedding logic).
- [ ] Enable the attachment UI in `PromptInput` that Stage 2 left wired
      but disabled.
- [ ] Manual test: upload, ask a question referencing it, confirm scoping
      matches the decision above (a student shouldn't surface another
      student's upload, and if uploads stay private, they shouldn't leak
      into another student's RAG retrieval either).
- [ ] DeepSeek review.

---

## Question-quality pass (post-Stage 3)

Three fixes landed after Stage 3, driven by a 50-question sample across 10
skills. Recorded here so the reasoning is not lost and the remaining lever is
named rather than re-diagnosed next session.

### Meta-referential stems — fixed

~23 of 50 sampled stems opened with "According to the excerpt" and resolved to
citation questions ("what does the Overview explain differences between?") — the
student had to LOCATE a sentence, not know a concept. Scenario-framed stems on
`apply` skills rarely did this, which located the cause in the framing, not the
model.

Three changes in `services/api/app/learn/items.py`:

- `_MCQ_SYSTEM` now names the banned framings explicitly (excerpt, passage,
  text, reading, overview, document, module, chapter, "according to", "the
  reading states", "as mentioned", "the author", "the material", "this
  section") and instructs the model to write the question as if the student
  must already know the fact. Grounding rule and strict-JSON contract unchanged.
- The model payload key was literally `"excerpt"` — the exact token that leaked
  into stems. Renamed to `"source_material"`.
- `_validated_mcq` rejects a banned phrase in the stem or any choice, so a
  meta-referential item gets one reroll via `generate_question`'s existing
  single validation retry instead of shipping. No extra loop added.

### Batch repetition — reduced where depth allows, floor is CONTENT

Repetition tracks corpus DEPTH, not size. Two levers applied:

- `_context_for` widened retrieval from `k=3` to `k=5` (`_RETRIEVAL_K`).
- `_rotated_context` gives each batch roll a different LEADING chunk. Batch
  rolls run independently (`map_concurrent_partial` over `range(size)`) and
  cannot see each other's stems, so with identical input they converged on the
  same top-ranked fact. `generate_question` now takes `context_offset`, and
  `routers/practice.py` passes the roll index. All chunks stay present in every
  slice; only the order changes, so no roll is ever grounded in less material.
- Token budget sized for the worst case per the `max_tokens` rule: context
  capped at `_MAX_CONTEXT_CHARS` (12000) and `max_tokens` raised 1536 -> 2048.
- No post-generation near-duplicate filter. Steps 1-2 cover the depth-limited
  case; a filter adds cost and a regeneration path for marginal gain.

**The remaining lever is content, not code.** A skill with 1-2 chunks still
produces near-synonym questions, and no prompt or rotation can fix that — there
are not two facts to ask about. The real fix is ingesting the AWS teaching PDFs,
which as of 2026-09-19 are confirmed reachable (see task #22 below) rather than
requiring manual staff upload. On a skill with 4+ chunks a 5-item batch now
draws on distinct facts rather than rewording one.

**Verification status: needs a live sample at real scale.** The unit tests pin
the mechanics (banned-phrase rejection, rotation order, offset threading, token
bounds) and the suite is green, but the claim "near-zero meta-referential stems
on real generation" requires deploying and sampling >=30 questions across skills
of varying depth. One good call proves nothing for an intermittent failure.

---

## Next session, in this order (do not reorder)

Set 2026-09-19. Items 1-4 are pending; item 5 is the Blackboard lead below.
The ordering is load-bearing: nothing else can be trusted until the rate-limit
fix is proven live.

### 1. Confirm 0016 is applied and the new code is actually running

**DONE 2026-09-19, confirmed live.**
- The three columns exist and hold real values on the AWS101 course:
  `lms_course_external_id = "AWS101.A321.1T.27.28"` (cache populated),
  `last_roster_sync_at = 2026-09-19T10:31:49Z` (cooldown stamped).
- The AWS101 launch that wrote those landed ~4 seconds before the session token
  was minted, so this is post-deploy behavior, not a leftover row.
- Lambda `kala-api` last modified 2026-09-17T07:36 UTC, which is AFTER both
  `f0ad10e` (stem fix, 06:56 UTC) and `5b8c086` (rate-limit fix, 07:34 UTC).
  The running build contains both.
- `last_skill_seed_at` is still NULL. That is expected: skill seeding only runs
  when it has something to propose, and the stamped path requires a non-skipped
  result. Not a defect.

### 2. The ~79-request drop: NOT a mystery consumer

**Explained 2026-09-19.** It was our own probe traffic. The tree walk alone
(root contents + five module listings + six folder listings + the
`_537_1` children fetch + repeated attachment/download attempts) is 30-40 calls,
and the two probe blocks plus concurrent manual testing account for the rest. No
background consumer exists: the API log shows no Blackboard REST calls in the
window, and the worker only ran `readinessSnapshot`. Steady-state drift is ~1
request per quota probe (1 OAuth + 1 read). Do not re-investigate this.

### 3. Item 1 — live-scale verification: RUN 2026-09-19

**Stem fix: VERIFIED.** 30 questions across 5 skills, generated against the
deployed build. **0 meta-referential stems (0%)**, down from ~23/50 (46%) in the
original sample. Every stem is scenario-framed and reads as knowledge-testing:

```
A startup expects highly unpredictable traffic: some months it needs a handful
of servers, other months it needs hundreds for just a few days. Which approach…

A company is deploying a web application on AWS and wants to ensure that it
remains available even if an entire data center fails…
```

**Repetition: the brief's success criterion did NOT hold, and the cause is
corpus quality, not the rotation code.** Measured per skill:

| skill | chunks | questions | distinct facts observed |
|---|---|---|---|
| `ec529ba8` | 6 | 10 | **1** — 9 of 10 reword "which certification does the course prepare you for" |
| `d2961973` | 3 | 5 | **1** — all 5 are "Auto Scaling group + traffic spikes" |
| `99811a42` | 4 | 5 | **1** — all 5 reword the course-badge completion scenario |
| `eed94898` | 6 | 5 | 3 |
| `d9b33edd` | 2 | 5 | **1** — all 5 reword the data-center-failure scenario |

Inspecting `ec529ba8`'s six chunks explains it: they are **not six facts**. Two
are junk (18 chars: `"Course Orientation"`; 71 chars), two are 4000- and
3518-char mega-chunks each containing many facts, and one is 275 chars of
metadata. Every one of them mentions the same headline topic. Rotation has
nothing to rotate *between* — the chunk COUNT is a misleading proxy for
chunk DIVERSITY.

**Conclusion to carry forward:** `_rotated_context` and `context_offset` are
wired correctly and firing (`items.py:354`, `practice.py:150`), but rotation
cannot manufacture variety a corpus does not contain. This is the same "depth is
the remaining lever" conclusion as before, now measured rather than assumed —
and it is stronger than the brief expected, since even 4-6 chunk skills repeat
when those chunks cover one topic. The fix is better content (the AWS PDFs,
task #22), not more prompting or a bigger `k`.

### 4. Item 2 — question-bank reset, drafted as SQL for the user to run

**DRAFTED 2026-09-19, NOT RUN.** `packages/db/reset_question_bank_aws101.sql`.
No linked Supabase CLI or DB password in this environment; the user applies it.
- There is **no per-user generated content**. `generated_items` and `quiz_sets`
  have no `user_id` column by design — diagnostic items are one row per skill
  shared course-wide, quiz sets are shared decks. The low-substance rows in the
  bank are course-wide, not one test account's.
- Delete course-wide `generated_items` for `kind in ('diagnostic','practice')`
  and the course's practice `quiz_sets`. Deleting a `quiz_sets` row cascades
  its `generated_items.set_id` rows and every student's `quiz_set_attempts` for
  that set — do NOT delete those separately. Both cascades verified against
  `0012`/`0013`.
- **CORRECTION to the earlier note that "nothing links the item bank by FK".**
  Two tables DO reference `generated_items(id)`:
  `srs_state.item_id` (ON DELETE **CASCADE** — a student's spaced-repetition
  schedule) and `guided_lesson_steps.check_item_id` (ON DELETE **SET NULL** —
  a lesson's comprehension check). Deleting a referenced row would destroy SRS
  progress or blank a lesson. Checked against the live DB: of 293 rows matching
  the delete filter, **zero** are referenced by SRS (31 rows) or lesson checks
  (30), because both reference only `kind='tutor'` and `kind='flashcard'`.
  The `kind` filter is what keeps this safe — widening it to include flashcards
  or tutor items WOULD cascade real data away. The SQL carries a mandatory
  collision check that must read 0 before the deletes.
- Do **not** touch `evidence_events` or `mastery_state`. They hold the actual
  learning history, and `evidence_events` is append-only besides.
- Current bank: 313 items (`practice` 283, `tutor` 16, `diagnostic` 10,
  `flashcard` 4). The reset removes 293 of them.
- Confirm with the user before running, and ask explicitly whether
  `kind='flashcard'` should be included — it was not called out as bad, and as
  the FK note above shows it is the one kind where widening the filter is
  actively destructive.
- This stops being a casual reset once real students exist. Say so rather than
  assuming.

### 5. Task #22 — build the Lead B extraction (see the section above)

Only after the connector is proven stable in production.

---

## Blackboard course content / the AWS PDFs (task #22)

**Status: investigated live, 2026-09-19. PDFs ARE reachable. Not built yet.**

The standing conclusion in the code — "the professor's PDFs are unreachable via
the REST API, staff `POST /content/upload` is the only path" — is **wrong**,
and so is the REST-attachments lead that was proposed to replace it. Both are
recorded below so neither gets retried. Verified against the live instance
(`AWS101 | Cloud Practitioner`) once the rate-limit quota cleared.

### Lead A — REST attachment endpoints: DEAD END, do not retry

Anthology's cookbook documents `/contents/{id}/attachments` →
`/attachments/{attachmentId}/download` for `resource/x-bb-document` items. On
this instance it fails at the first call:

```
GET /courses/_8_1/contents/_622_1/attachments
400 {"status":400,"message":"The Content Item does not support file attachments"}
```

Ultra documents do not use the attachments API at all — they embed files in the
body instead (Lead B). The cookbook path applies to Original-view content, which
this course is not. The old code comment claiming `/attachments` "returns JSON"
was reading a 400 body, not a result list.

### Lead B — embedded `data-bbfile` href: CONFIRMED WORKING

An Ultra document item's `body` carries literal anchor tags with the file
metadata inline. Real example from `_622_1` (`[Read] Student Guide - Introduction`):

```html
<a href="https://<host>/bbcswebdav/pid-622-dt-content-rid-5560_1/xid-5560_1?Kq3cZ..."
   data-bbtype="attachment"
   data-bbfile="{&quot;fileName&quot;:&quot;Student Guide AcademyCloudFoundations.pdf&quot;,
                 &quot;fileSize&quot;:819568,
                 &quot;mimeType&quot;:&quot;application/pdf&quot;,
                 &quot;resourceUrl&quot;:&quot;...&quot;}">Student Guide - Course Introduction</a>
```

`data-bbfile` is HTML-escaped JSON: `fileName`, `fileSize`, `mimeType`,
`resourceUrl`. The sibling `href` is the real file.

**Verified end to end, no OAuth required:**

- `curl -L "$href"` → `302` → `200`, `application/pdf`, **819568 bytes** — exactly
  the `fileSize` in `data-bbfile`. `%PDF-1.7`, 37 pages.
- Kala's existing `app.ai.documents.extract_text(data, "application/pdf")` pulls
  **12,062 chars** of clean text: real AWS Academy Cloud Foundations student
  guide content (`© 2022, Amazon Web Services, Inc.`).
- The signed `bbcswebdav` href is self-authenticating. No bearer token, no
  `JSESSIONID`, no referer, no admin rights.

**Two gotchas that cost probe time:**

1. Use `href`, **not** `resourceUrl`. They are different signed URLs
   (`rid-5560` vs `rid-46141487`); `resourceUrl` is the inline-render variant and
   returns **404**. The `href` returns the file.
2. The signature is short-lived (the `VxJw3wfC56` param is a unix timestamp). It
   must be fetched from a freshly-read body, not cached and reused.

### The three steps to build this later

Do not start until the connector is confirmed stable in production. This
changes `blackboard.py`, the file whose rate-limit behaviour was just fixed.

1. **Extract before stripping.** `_HTMLTextExtractor` currently discards the
   anchors on the way to plain text. Pull `href` + `data-bbfile` out of `body`
   first, keep the anchor's text as the title, and only then strip markup for
   the prose chunk.
2. **Filter by MIME.** Allow-list against `documents.ALLOWED_MIME_TYPES`, which
   already contains `application/pdf`. The same `data-bbfile` blob also carries
   `image/png` screenshots — those must be skipped, or the corpus fills with
   images that extract to nothing.
3. **Feed the existing pipeline.** Fetch the href, pass bytes through
   `extract_text`, then reuse the chunk + embed path `/content/upload` already
   uses. No new dependency, no new auth, no new table. `pypdf` is already a
   declared dependency.

**Budget note:** each PDF is one extra HTTP request, and this instance's quota
is 10,000 per window. A course-wide walk that downloads every attachment in one
ingest run would be exactly the kind of burst that caused the 2026-09-17 outage.
Whatever this ships as must respect the same cooldown/rate-limit discipline
(0016) — and it belongs in the WORKER, next to tagging, not in a request path.

### Fallback if Lead B ever regresses

Blackboard's built-in **Export/Archive Course** (Packages and Utilities → Export
or Archive) produces a ZIP with an explicit "include copies of the content"
option, normally available to the course's own instructor without institution
admin rights. Manual and browser-triggered, so it does not solve automatic
detection, but it turns one-PDF-at-a-time into "export once, unzip, bulk-call the
existing `/content/upload` over the contents." Good enough to build on if needed.

---

## The 30s wall is now the top structural risk (measured 2026-09-19)

Three separate paths hit the same Lambda ceiling, and they are the same
underlying problem: unbounded work behind a request-response door.

| path | measured | wall |
|---|---|---|
| `connector.get_content` tree walk (178 items) | **31.8s** | 30s |
| tree walk + 3 PDF attachments | **38.4s** | 30s |
| practice set generation (5 items, free-tier model) | hits 30000.00 ms | 30s |
| the old serial tagging loop | fixed by moving to the worker | — |

**The tree walk is the root of it.** It makes ~40+ sequential Blackboard REST
calls at ~0.7s each. That ALONE exceeds the wall for this course, which is the
smallest one in the pilot \u2014 so capping PDF attachments cannot fix ingest,
because ingest was already too slow before any PDF was fetched. Confirmed in
the logs: eight `Duration: 30000.00 ms ... Status: timeout` invocations, and no
`Ingest pulled ...` line, meaning ingest requests never reached their own
logging.

This also explains the `documentsRemaining` value being less useful than
intended: the cap works (3 fetched, 5 left, 6.6s — matching the predicted
~2s/file), but a caller never gets to see the response because the request
dies first.

**The fix has the same shape as tagging's.** Tagging moved to the worker for
exactly this reason. The content walk should too: it is unbounded in the number
of LMS items, it is network-bound with no per-call ceiling, and nothing about
it needs to happen inside a user's request. That is a real piece of work, not a
constant to tune, and it is deliberately NOT started here.

Until then, treat `/ingest` as unreliable for any course of this size, and do
not build on the assumption that it completes.

---

## Two more defects found during the 2026-09-19 live verification

Both are recorded here rather than chased, per the standing instruction to
flag and stop. The malformed-UUID one was FIXED in `3d40c4f`.

### A malformed `course_id` in a token returned 500, not 4xx — FIXED in `3d40c4f`

Any route with `course_id` in the path, given a course id that is not a valid
UUID, returned a **bare 500** with a `text/plain` body reading
`Internal Server Error`. Verified on four routes at once:

```
GET /courses/<bad-id>              -> 500
GET /courses/<bad-id>/diagnostic   -> 500
GET /practice/<bad-id>/next        -> 500
GET /courses/<bad-id>/modules      -> 500
```

Cause: every such route passes the path param straight into a PostgREST filter
string. Postgres rejects it with `22P02 invalid input syntax for type uuid`, and
the resulting `httpx.HTTPStatusError` propagates out of the handler unhandled,
so Lambda turns it into a generic 500. A client-side bug (a mistyped or
hand-edited token) therefore presents as a server outage.

Fix (not yet written): validate path-param ids as UUIDs at the boundary and
return 404, matching the two-layer gate's existing "404 not 403, so an
unauthorized staffer cannot probe which ids exist" convention. Worth a shared
dependency rather than repeating the check per route.

### Practice set generation can exceed the Lambda 30s ceiling

During the sample, several `POST /practice/{id}/set` calls returned
`{"setId": null, "items": []}`. Eight Lambda invocations in that window show
`Duration: 30000.00 ms ... Status: timeout` — the platform ceiling, hit exactly.
The partial-tolerant batch fans out N concurrent model calls, and N=5 against a
slow free-tier model can exceed the budget.

The response shape is also misleading: `setId: null` is the shape of the "no
approved skill" branch, so a TIMEOUT is indistinguishable from "this course has
no skills" to the client. Note this is the same 30s wall that forced tagging
into the worker — the batch generation path now shares that constraint.

Repro note: intermittent, not size-dependent — the same skill at the same size
alternated between 5 items and a timeout-derived empty set across consecutive
calls.

---

## Parking lot (raised, not decided, don't build until resolved)

- `ConversationDownload` for tutor sessions — see Stage 2.
- Upload privacy/corpus-membership — see Stage 4.
- Whether `Reasoning` (chain-of-thought display, already vendored) has any
  use in Kala. Nothing in the current plan calls for it — Kala's tiered
  model router doesn't currently surface reasoning traces to students, and
  showing model "thinking" to a learner is a different pedagogical choice
  than showing it to a developer. Don't wire it speculatively.
- **A skill whose study queue is fully graduated goes permanently empty.**
  Raised during the Checkpoint 3 hub review, deliberately not solved there.
  Study cards are a bounded, schedule-driven queue seeded on first open; once
  every card in it is mastered and graduates out of normal review, the Study
  tab has nothing to show for that skill and no way to add more (by design —
  see the StudyBrowser copy). The narrow version of the question is "how do
  new cards enter a mastered queue without disturbing the schedule of cards
  still in rotation?" That is a real design question, not a bug: answering it
  means deciding whether a graduated skill should re-seed on open, on a
  mastery dip, or never. Separate from, and much smaller than, "let students
  generate flashcards on demand" (rejected: it makes `due_at` meaningless).
