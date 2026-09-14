# Practice / Flashcards / Diagnostic — Rebuild Spec

These three are the quiz surfaces. After Lessons proves the `StudySurface` +
`SessionBar` + `ComposeDock` grammar, these are simpler: mostly "put the single
card in the stream, move the advance action to the dock, drop the redundant
inner chrome."

## Do this first, across all three: move the quiz container into `AnswerableCard`

Before touching any individual mode, consolidate ownership of "what a quiz
surface looks like." Verified today: `LessonChat`, `FlashcardDeck` (in two
places), and `DiagnosticPanel` each independently wrap their card in
`<div className="relative border bg-card"><CornerBrackets />…`, and
`PracticePanel` wraps in a shadcn `Card` instead and skips brackets entirely —
four different implementations of the same surface. Move the bracketed,
zero-radius bordered container **into `AnswerableCard` itself** (it already
owns the prompt/choices/result rendering; it should own the frame too), and
delete all four per-feature wrapper divs. Every mode then gets the identical
quiz surface for free, and it can't drift again because there's only one place
to change it. Do this as its own small step before Practice/Flashcards/
Diagnostic migrate individually — it de-risks all three at once.

The user's specific complaint here: **Practice and Lessons show the exact same
topic-selection page first, so they read as the same feature even though they
are not.** The fix is not to make the pickers different for difference's sake —
it is to make the *sessions* distinct (which the dock + mode now do) and to let
the pre-session picker be clearly a lightweight "pick a topic" step, not a
full-page feature of its own that competes with the session.

---

## Practice — `features/practice/components/PracticePanel.tsx`

### Remove
- The wrapping `<Card><CardHeader><CardTitle>Quick practice</CardTitle>` — this
  is a redundant boxy title *inside* a surface that already has a `SessionBar`.
  It is the "panel header inside the content" duplication. Gone.
- The in-flow "Next item" button under the card → moves to the dock.

### Keep
- All grading logic, `useNextPracticeItem`, `useSubmitPractice`, the gamification
  XP-delta derivation, streak/band-transition meta. Untouched.
- `AnswerableCard` with all its props (`tour-practice-choices`,
  `tour-practice-feedback`, the meta slot). Untouched.

### Shape

```tsx
export function PracticePanel({ courseId, skillId, onExit }: {
  courseId: string; skillId: string; onExit: () => void;
}) {
  // …all existing hooks/state unchanged…

  return (
    <StudySurface
      bar={
        <SessionBar
          title="Quick practice"
          progress={{ current: sessionAnswers, total: 0, label: "answered" }}
          onBack={onExit}
          backLabel="Choose another topic"
        />
      }
      dock={
        <ComposeDock
          // Advance only exists AFTER a graded result. Before that, no
          // primary — per ComposeDock's degenerate-case behavior (see `02`),
          // that alone forces compose-only mode, no toggle chrome, which is
          // exactly right pre-answer: nothing to advance to yet.
          primary={
            lastResult ? { label: "Next item", onClick: () => refetch() } : null
          }
          onAsk={(text) => askAboutItem(text) /* optional: a grounded "explain
            this" via a dedicated useTutorAsk instance (not shared with any
            other mutation), appended as a UserBlock + AssistantBlock pair;
            practice can also omit onAsk entirely if you want practice to be
            heads-down. Recommend KEEPING it — it's the whole "unified with
            the AI" point. */}
          placeholder="Ask Kala about this question…"
        />
      }
    >
      <StudyStream>
        <div id="tour-practice-card">
          <AnswerableCard
            prompt={item.prompt}
            choices={item.choices}
            selectedId={selectedChoice}
            onSelect={handleAnswer}
            choicesAnchorId="tour-practice-choices"
            resultAnchorId="tour-practice-feedback"
            result={lastResult ? { correct, explanation, mastery } : null}
            isPending={submit.isPending}
            meta={/* band transition / streak / +XP — unchanged */}
          />
        </div>
      </StudyStream>
    </StudySurface>
  );
}
```

### Route `routes/course/practice.tsx`
- In-session → `<PracticePanel … onExit={() => setSkillId(null)} />`, no
  `PageHeader`.
- Pre-session → the picker with the **Recommended** card stays (that is genuinely
  Practice-specific and good — it is the "your lowest mastery" nudge). Title
  shrinks to "Choose a topic" like Lessons. The Recommended dark card is the one
  thing that visually distinguishes Practice's picker from Lessons', which is
  correct — Practice *has* a recommendation, Lessons does not.

### Tour anchors: `tour-practice-picker`, `tour-practice-recommended`,
`tour-practice-card`, `tour-practice-choices`, `tour-practice-feedback` — all
preserved (picker/recommended on the pre-session view, card/choices/feedback in
the session).

---

## Flashcards — `features/flashcards/components/FlashcardDeck.tsx`

Flashcards already uses `StudySessionShell` + `CornerBrackets` + `AnswerableCard`
and has the think→choose→reveal phase machine. Migration is mechanical:

### Remove
- The inner `border bg-card` panel + its `border-b px-5 py-3` header row (the
  in-panel title). `SessionBar` owns the title now.

### Keep
- The `Phase` state machine (`think`/`choose`/`answered`/`revealed`), the
  `TransitionPanel` phase motion, `StateBadge`, the SRS meta, `skillId` staying
  **optional** (cross-skill due-review is a real mode — do not force a skillId,
  see the existing file comment).
- Reveal-is-terminal behavior.

### Dock
- After a card is answered/revealed → dock primary = **Next card**.
- Progress in the bar = `{ current, total, label: "card" }` (deck position).
- Forward chevron in `SessionBar` can also drive "next card" if you want the
  Gizmo dual-affordance (chevron top-right AND dock button). Pick one as
  primary; wiring both to the same handler is fine and matches Gizmo (it has the
  top chevron *and* a bottom continue).

### Route `routes/course/flashcards.tsx`
Same pattern: session = takeover no header; pre-session = picker titled "Choose
a topic" with the due-review default option. Flashcards' picker distinguishes
itself by offering "Review what's due" (cross-skill) as the default — again a
genuine, non-cosmetic difference from Lessons/Practice.

---

## Diagnostic — `features/diagnostic/components/DiagnosticPanel.tsx`

The special one. It is **not** a per-item graded loop — it is a batch-silent
baseline: N cards on screen at once, no per-question correctness, single submit,
then a blur-out → mastery-delta reveal.

### Migrate the container, preserve the mechanics
- Put the batch of `AnswerableCard`s into `StudyStream` inside `StudySurface`
  (it already uses `StudyStream`; now it is inside the takeover surface with a
  bar and dock).
- **Dock primary = Submit** (single, at the end, disabled until all answered).
  Not "Next item" — diagnostic submits the whole sitting at once.
- **No `onAsk` / no follow-up compose** for diagnostic. Asking Kala mid-baseline
  would undercut the baseline (same reasoning as "no per-question reveal"). The
  dock here is primary-action-only (`ComposeDock` with `onAsk` omitted → it
  renders just the Submit primary, centered). This is a legitimate dock mode.
- Keep the blur/reveal `Dialog` + `MasteryDelta` "your twin just updated"
  moment exactly. Keep batch-silent (`firstChoiceId={null}` per card so N cards
  don't collide on the tour anchor — this is the existing duplicate-id fix, do
  not regress it).

### Progress
`{ current: answeredCount, total: questionCount }` in the bar, so the student
sees "4/8" as they fill it in. Submit enables at `answered === total`.

### Anchors
Diagnostic renders many cards; it passes `firstChoiceId={null}` to avoid
duplicate `tour-first-choice` ids. Preserve that. Its own tour anchors (if any
in `student-tour.ts`) stay put.

---

## Cross-cutting: the "same picker" perception fix

After this, why do Practice and Lessons no longer read as the same feature,
even though both have a topic picker?

1. **The session is now unmistakably different.** A lesson is a multi-turn
   stream with teaching bubbles and a Continue dock; practice is one card with a
   Next-item dock. Before, both opened into similar-looking boxed panels. Now
   the dock + stream content diverge visibly.
2. **The picker is demoted.** It is a lightweight "Choose a topic" step titled
   plainly, not a full feature page with a big eyebrow/description. It reads as
   a gate to the session, not the destination.
3. **Each picker keeps its one honest differentiator** and nothing more:
   Practice has the Recommended card, Flashcards has Review-what's-due, Lessons
   has neither (it is just the topic grid). Those differences are real, not
   decorative.

Do **not** try to differentiate them by giving each picker a different layout or
color — that would be decoration, and the frontend skill warns against exactly
that. The sameness of the picker is fine *because the picker is no longer the
feature.* The session is.
