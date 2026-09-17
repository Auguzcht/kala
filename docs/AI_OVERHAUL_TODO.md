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
are not two facts to ask about. The real fix is staff uploading the AWS teaching
PDFs (see the Blackboard bulk-export item). On a skill with 4+ chunks a 5-item
batch now draws on distinct facts rather than rewording one.

**Verification status: needs a live sample at real scale.** The unit tests pin
the mechanics (banned-phrase rejection, rotation order, offset threading, token
bounds) and the suite is green, but the claim "near-zero meta-referential stems
on real generation" requires deploying and sampling >=30 questions across skills
of varying depth. One good call proves nothing for an intermittent failure.

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
