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

So the step slot has four states, and the Check is a **takeover of the slot**,
not a new block appended under the teaching bubble.

## State model

```
stepIndex → which step is current
slotState ∈ { "teaching", "checking", "graded", "checkThread" }

teaching : TeachingBlock visible in the slot. Dock primary = "Continue".
           Compose = "Ask a follow-up" (injects Q&A turns, never advances).
checking : Check card OCCUPIES the session lane; the teaching stream and dock
           unmount together (see "the pop" below). This is the "chat window
           hidden" moment — no input remains visible beneath the card.
graded   : Check shows correct/incorrect via AnswerableCard's own result UI.
           The dock returns with Continue/Next or Try again as its primary
           action; Hint is gone, replaced by Explain.
checkThread: Explain (or a pre-grade Hint) reveals a scoped Kala exchange
           directly below the check. This single lane scrolls when needed and
           its dock accepts only questions about that check. The back chevron
           returns to graded/checking, not to topic selection.
```

The committed history (steps already passed) renders above as static
`TeachingBlock`s with a small "Step complete ✓" marker — same as today. Only the
**current** slot has the three-state behavior. This is the architectural rule
from `01`: history is a list; the current step is a single stateful slot.

## The pop (hiding/revealing the chat window)

The "pops up hiding the chat / pops out revealing" is a mount transition on the
Check occupying the slot. Concretely:

- When `slotState` goes `teaching → checking`: the stream and dock unmount as
  one visual layer, then the Check card mounts into the same central session
  lane with a short scale/opacity-in (`motion` is already a dep; respect
  `useReducedMotion`). This is a true takeover, not a modal over a still-live
  conversation: the underlying chat and its input are not visible or
  scrollable while the check is active.
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
those move to the **dock**, passed as `ComposeDock`'s `primary` prop (a config
object, not a rendered button — see `02`'s Checkpoint 2 correction):

- `teaching` state → `primary={{ label: "Continue", onClick: openCheck, id:
  "tour-lesson-continue", icon: <GraduationCapIcon size={16} /> }}`. `onAsk`
  is also present here, so the dock shows the toggle — student can ask a
  follow-up without leaving teaching mode, or hit Continue directly.
- `checking` → do not render `ComposeDock`. The check is a dedicated,
  dock-free takeover while the student is choosing an answer.
- `graded` → bring back `ComposeDock` with `Next step` / `Finish lesson` or
  `Try again` as `primary`. The chat toggle remains available for a scoped
  follow-up.
- `checkThread` → keep the check in place and append the scoped Kala exchange
  below it in the same scroll lane. The dock reuses its normal input, but its
  request context is restricted to the current check.

Hint stays inside an ungraded check and opens the scoped thread rather than
appending inline copy. Once graded, it is replaced by Explain. The back chevron
unwinds `checkThread → check → teaching → topic picker` one layer at a time.

## Tour anchors — must all survive

Grep before and after. The lesson tour uses these ids:
`tour-lesson-generating`, `tour-lesson-explain`, `tour-lesson-continue`,
`tour-lesson-check`, `tour-lesson-check-feedback`.

Placement in v2:
- `tour-lesson-generating` → the loading panel (unchanged).
- `tour-lesson-explain` → the current `TeachingBlock`'s content (pass `id`
  prop, as today).
- `tour-lesson-continue` → passed as `primary.id` in the `teaching`-state dock
  config above; `ComposeDock` puts it on the action button it renders
  internally.
- `tour-lesson-check` → the Check card container in the slot.
- `tour-lesson-check-feedback` → `AnswerableCard`'s `resultAnchorId` (unchanged
  prop pass-through).

`TourRunner.tsx`'s tutor-input textarea fix (the `HTMLTextAreaElement` native
setter) is unrelated and stays. But note: the lesson tour clicks
`#tour-lesson-continue` — verify that selector still resolves to a clickable
button after `ComposeDock` renders it (it will, `ComposeDock`'s action-mode
button is a plain `<button id={primary.id}>`).

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
          progress={{
            current: done ? total : stepIndex + 1,
            total,
            label: "step",
            bloomLevel: current?.bloomLevel ?? undefined,
          }}
          onBack={onExit}
          backLabel="Choose another topic"
        />
      }
      dock={isCheckTakeover ? undefined : (
        <ComposeDock
          primary={dockPrimary}
          onAsk={(text) => askFollowUp(text) /* uses a SEPARATE useTutorAsk
            instance from the Hint button's — see the "Follow-up ask" section
            below. Injects a turn, never advances. */}
          askPending={followUp.isPending}
          placeholder="Ask Kala about this step…"
        />
      )}
    >
      {isCheckTakeover ? (
        /* Dock-free takeover card in the same 800px session lane. */
        <LessonCheckTakeover />
      ) : <StudyStream>
        {/* committed history: passed steps as static TeachingBlocks + ✓ */}
        {/* current teaching bubble + local follow-up turns */}
        {/* done: completion turn */}
      </StudyStream>}
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

## `TeachingBlock`'s Bloom chip — move it, don't delete it (Checkpoint 2)

Checkpoint 2 raised a fair question looking at the built screen: does the grey
"Remember" chip on the teaching bubble just repeat what the topic picker
already showed? **Checked against the actual generation logic, and no — it's
different data, not a duplicate.** The topic picker's chip
(`TopicLanding`/`s.bloomLevel`) is the *skill's* single target Bloom level, set
once by `skill_proposer.py`. The per-step chip comes from a different source:
`services/api/app/learn/lessons.py`'s outline prompt explicitly instructs the
model to "break the skill into an ordered sequence of 3-6 teach-steps that
build from recall toward application (read → understand → apply)," generating
a *distinct* `bloom_level` per step. It's a ladder position within this one
lesson, not the skill's overall level repeated.

So the fix isn't deletion, it's presentation. A bare grey pill inside the
content bubble gives no signal that this is a *progression* rather than a
repeated tag — it reads exactly like duplicated chrome even though it isn't
one. **Move it out of the teaching bubble and into `SessionBar`, next to the
step counter**, using the same mono data-tick treatment already established
there (`1/5 step`) rather than a separate pill floating in prose:

```
◂ back   Compare traditional IT infra…   1/5 step · remember   ▓▓░░░░░░  ▸
```

This does three things at once: gets it out of the content bubble (the actual
decluttering the checkpoint asked for), puts it next to the thing it's
genuinely related to (progress through the lesson), and reuses an existing
visual language instead of inventing a new grey-pill pattern. `TeachingBlock`
drops its `bloomLevel` badge entirely; `SessionBar`'s `progress` prop gains an
optional `bloomLevel` field it renders inline with the counter.

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
- No `bloomLevel` badge inside the teaching bubble; the step's Bloom level
  (when present) shows in `SessionBar` next to the step counter instead.
- The dock's action button and compose input are the same `rounded-full` slot
  — toggling between them via the small circular button produces no visible
  seam, resize, or radius mismatch.
