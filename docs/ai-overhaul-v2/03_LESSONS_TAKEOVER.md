# Lessons Rebuild — the Check Takeover

Lessons is migrated **first**: it has the loudest bug (two scrollbars, header
bloat, the append-instead-of-popover check) and it is the only mode with the
takeover mechanic. Proving the pattern here de-risks every other mode.

Target file: `features/lessons/components/LessonChat.tsx` (rebuild) and
`routes/course/lessons.tsx` (strip session header).

## The behavior we are matching (from the user, verbatim intent)

> Continue proceeds with the next step OR the reinforcement quiz that pops up
> **hiding the chat window**, then when answered correctly, **pops out and once
> more reveals the chat window** now with a new AI response for the next step.
> OR ask a follow-up question (keeps a relevant grounded answer to the question
> only, then points back to Continue when ready).

So the step slot has three states, and the Check is a **takeover of the slot**,
not a new block appended under the teaching bubble.

## State model

```
stepIndex → which step is current
slotState ∈ { "teaching", "checking", "graded" }

teaching : TeachingBlock visible in the slot. Dock primary = "Continue".
           Compose = "Ask a follow-up" (injects Q&A turns, never advances).
checking : Check card OCCUPIES the slot (the teaching bubble is unmounted or
           dimmed behind it — see "the pop" below). Dock primary hidden/disabled.
           This is the "chat window hidden" moment.
graded   : Check shows correct/incorrect via AnswerableCard's own result UI.
           If correct (result.advance) → on Continue/Next, the slot unmounts the
           Check, commits the teaching turn to history, stepIndex++, next step
           streams in as a fresh teaching slot ("reveals the chat window with a
           new AI response"). If incorrect → "Try again" resets to checking.
```

The committed history (steps already passed) renders above as static
`TeachingBlock`s with a small "Step complete ✓" marker — same as today. Only the
**current** slot has the three-state behavior. This is the architectural rule
from `01`: history is a list; the current step is a single stateful slot.

## The pop (hiding/revealing the chat window)

The "pops up hiding the chat / pops out revealing" is a mount transition on the
Check occupying the slot. Concretely:

- When `slotState` goes `teaching → checking`: the Check card mounts into the
  slot position with a short scale/opacity-in (`motion` is already a dep;
  respect `useReducedMotion`). The teaching bubble it grew from either unmounts
  or sits dimmed (`opacity-40 pointer-events-none`) directly behind — dimmed is
  gentler and keeps context, matching Gizmo where the lesson text is still
  faintly there. **Recommend dimmed-behind.**
- When correct and advancing: the Check unmounts (scale/opacity-out), the slot
  becomes the next teaching turn. Because it is a real unmount, you get the
  "pops out" for free — no manual "push everything up."

Do NOT implement the pop by appending the Check as the next flex item in the
stream and scrolling. That is the current behavior and the thing being removed.
The Check renders in an overlay layer *within the current slot's box*, not as a
sibling in the stream list.

**Be specific about the anti-pattern, because it's easy to half-fix this.**
Today's code is `{!checkOpen ? <chip/> : null}` followed by
`{checkOpen && check ? <check-card/> : null}` as two siblings inside the same
`<div className="space-y-3">` under `TeachingBlock`. It would be easy to
"migrate" this by keeping that exact structure and just restyling the check
card, if the appearance were the only thing being reviewed for. Structurally
that is still one growing div with a conditional block underneath it — the
component tree shape that produces "new bubble pushes previous content up." The
actual fix requires the current step to render as a single positioned slot
(e.g. a `relative` container) where `teaching` and `checking` are two
absolutely/stacked states that transition via mount/unmount or opacity, not two
conditionally-rendered siblings stacking in normal document flow. If an
implementation still reads as "two `{condition ? x : null}` blocks one after
another in the same flow div," it has not actually implemented the takeover,
regardless of how the check card is restyled.

Wireframe of the current slot across states:

```
 teaching                     checking (the pop)              graded → advance
 ┌────────────────────────┐   ┌────────────────────────┐     (Check unmounts,
 │ 🐦 teaching bubble      │   │ ░ teaching bubble (dim) │      next teaching
 │    summary / bullets    │   │ ┌────────────────────┐ │      streams into a
 │    misconception        │   │ │ CHECK YOURSELF     │ │      fresh slot)
 │    key takeaway         │   │ │ prompt + choices   │ │
 └────────────────────────┘   │ │ [corner brackets]  │ │
   dock: ▸ Continue           │ └────────────────────┘ │
                              └────────────────────────┘
                                dock: Continue hidden;
                                compose may stay for hints
```

## Where the actions live now

Today `LessonChat` renders the "I understand — continue" chip *inside the
stream* and the "Next step / Try again" buttons *inside the check block*. In v2
those move to the **dock**:

- `teaching` state → dock primary = **Continue** (`PrimaryAdvance`,
  `id="tour-lesson-continue"` moves here). Clicking it calls `openCheck()`.
- `checking` (ungraded) → dock primary hidden. The student answers in the card.
- `graded` + `advance` → dock primary = **Next step** (or **Finish lesson** on
  the last step). Clicking commits + advances.
- `graded` + not advance → dock primary = **Try again** (or keep it in-card if
  you prefer; but dock is more consistent). Resets to `checking`.

The Hint button stays inside the check card (it is contextual to the question),
via `AnswerableCard`'s `actions` slot — unchanged.

## Tour anchors — must all survive

Grep before and after. The lesson tour uses these ids:
`tour-lesson-generating`, `tour-lesson-explain`, `tour-lesson-continue`,
`tour-lesson-check`, `tour-lesson-check-feedback`.

Placement in v2:
- `tour-lesson-generating` → the loading panel (unchanged).
- `tour-lesson-explain` → the current `TeachingBlock`'s content (pass `id`
  prop, as today).
- `tour-lesson-continue` → the dock's **Continue** `PrimaryAdvance` (`id` prop
  added to `PrimaryAdvance` exactly for this).
- `tour-lesson-check` → the Check card container in the slot.
- `tour-lesson-check-feedback` → `AnswerableCard`'s `resultAnchorId` (unchanged
  prop pass-through).

`TourRunner.tsx`'s tutor-input textarea fix (the `HTMLTextAreaElement` native
setter) is unrelated and stays. But note: the lesson tour clicks
`#tour-lesson-continue` — verify that selector still resolves to a clickable
button after it moves into the dock (it will, `PrimaryAdvance` is a `<button>`).

## Route file: strip the session header

`routes/course/lessons.tsx` today always renders `PageHeader` (eyebrow "Guided
lessons", title "Work through it, step by step", the description) even mid-
session. In v2:

```tsx
function LessonsPage() {
  const courseId = useSession()?.courseId ?? "";
  const { data: twin, isLoading } = useTwin(courseId);
  const [skillId, setSkillId] = useState<string | null>(null);

  // In session → full takeover, NO PageHeader, NO surrounding page chrome.
  if (skillId) {
    return <LessonChat courseId={courseId} skillId={skillId} onExit={() => setSkillId(null)} />;
  }

  // Pre-session → the picker IS a normal page (title allowed here).
  return (
    <>
      <PageHeader eyebrow="Lessons" title="Choose a topic" />
      <TopicLanding
        isLoading={isLoading}
        skills={twin?.skills ?? []}
        onChoose={setSkillId}
        caption="guided walkthrough with checks"
        gridId="tour-lessons-picker"
        firstCardId="tour-lessons-first-card"
      />
    </>
  );
}
```

Key changes:
- The header is gone once `skillId` is set. The session owns the viewport.
- `LessonChat` gains an `onExit` prop; the "Back" chevron in `SessionBar` calls
  it (replaces the old outline "Choose another topic" button, which was the
  redundant chrome the user flagged as looking nothing like Gizmo).
- The pre-session title shrinks to a plain "Choose a topic" — the long
  "Work through it, step by step / Kala walks you through…" description is cut.
  It was eyebrow-tell filler (frontend skill) and the user asked for it gone.

## `LessonChat` skeleton (v2)

Not full code — the shape. The implementer fills logic from the existing file
(all the hooks, `useLesson`, `useSubmitStepCheck`, `useTutorAsk` for
hints/follow-ups, the reset-on-lessonId effect, the check submit/choose/retry
handlers all carry over intact).

```tsx
export function LessonChat({ courseId, skillId, onExit }: {
  courseId: string; skillId: string; onExit: () => void;
}) {
  // …all existing state + hooks unchanged…
  // NEW: slotState machine derived from checkOpen + result, or an explicit
  //      "teaching" | "checking" | "graded" state.

  // Loading / error / empty → return inside <StudySurface> with just a bar,
  //   OR keep the simple full-panel states (they're fine as-is, no dock).

  return (
    <StudySurface
      bar={
        <SessionBar
          title={data.title}
          progress={{ current: done ? total : stepIndex + 1, total, label: "step" }}
          onBack={onExit}
          backLabel="Choose another topic"
        />
      }
      dock={
        <ComposeDock
          primaryAction={dockPrimary /* Continue / Next step / Finish / Try again, per slotState */}
          onAsk={(text) => askFollowUp(text) /* uses useTutorAsk, injects a turn, never advances */}
          askPending={hint.isPending}
          placeholder="Ask Kala about this step…"
        />
      }
    >
      <StudyStream>
        {/* committed history: passed steps as static TeachingBlocks + ✓ */}
        {/* current slot: teaching bubble; when checking, Check card takes over
            the slot (dimmed teaching behind), via AnswerableCard */}
        {/* done: completion turn */}
      </StudyStream>
    </StudySurface>
  );
}
```

### Follow-up ask — this is a real behavior addition, not a restyle

Flag this honestly: adding "ask a follow-up" to Lessons (and Practice/
Flashcards) is new product behavior, not presentation. It reuses the existing
`askTutor` API (no backend change), but it is a capability that doesn't exist
on these surfaces today, so it needs its own small design decisions rather than
being waved through as part of the visual rebuild. Decide these before
building, don't leave them to the implementer's judgment mid-PR:

1. **Separate mutation instance from Hint.** `LessonChat` already calls
   `useTutorAsk(courseId)` once, for the Hint button, and stores it in a
   variable named `hint`. Do **not** reuse that same mutation object for the
   follow-up ask — `useMutation`'s `isPending`/`data` is one shared state, so a
   student clicking Hint and then Ask (or vice versa) would have the two
   actions stomp each other's pending/result state. Call the hook a second
   time for a distinct instance: `const followUp = useTutorAsk(courseId);`.
   This is exactly the pattern Flashcards already uses correctly for its own
   `hint` vs. `explain` (two separate `useTutorAsk` calls) — follow the same
   precedent here, don't regress it.
2. **The student's question renders as a `UserBlock`, followed by the answer
   as an `AssistantBlock`.** Both in the *current slot's* local turn list. This
   matches how Tutor already renders exchanges and keeps the follow-up
   legible as a real back-and-forth, not just an answer appearing from
   nowhere.
3. **These turns are stateless / non-persistent**, same as the existing Hint
   text today (`hintText` local state, not written to any table). They reset
   with the rest of the step's local state on `openCheck()` / step change.
   Nothing about `tutor_conversations`/`tutor_messages` (Stage 2's persistence)
   is touched — a lesson follow-up is NOT a tutor conversation and must not be
   silently written into one.
4. **Practice and Flashcards keep their existing inline Hint/Explain
   treatments as-is** (Flashcards' `askHint`/`askExplain` buttons inside the
   `AnswerableCard` `actions` slot). The dock's `onAsk` is an *additional*,
   more open-ended "ask about this" channel, not a replacement for those
   contextual actions. If that reads as redundant once built (two ways to ask
   Kala something on the same screen), that's a real UX call to make during
   Practice/Flashcards migration (`04`) — flagged there, not decided here.

Implementation: reuse `useTutorAsk(courseId)` as `followUp` (see #1). A
follow-up answer renders as a `UserBlock` + `AssistantBlock` pair appended to
the *current slot's* local turn list (not the committed history, not advancing
the step), then the dock primary re-focuses on Continue. This is the "keeps a
relevant grounded answer only, then points back to Continue" behavior.

## Acceptance check for this mode

- One scrollbar, ever. Resize the window short — only the stream scrolls, the
  bar and dock stay put.
- No "Guided lessons / Work through it" header while in a lesson.
- Clicking Continue: the check *takes over the current step's space* (teaching
  dims behind or unmounts), it does not append a new bubble that shoves content
  up.
- Correct answer: check unmounts, next teaching turn appears where it was — the
  "pop out and reveal" motion.
- Ask a follow-up: answer appears, Continue still there, session did not
  advance.
- All five `tour-lesson-*` anchors resolve (grep + click-through).
