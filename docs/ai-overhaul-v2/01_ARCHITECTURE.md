# Architecture — Study Surface v2

The target component tree, the scroll-ownership model, and the shared session
grammar every mode plugs into. This is the contract the per-component specs
(`02`–`05`) implement.

## The single problem to solve

Every visible complaint the user raised traces to one root cause:

> The session content lives *inside* the normal page scroll, and `StudyStream`
> then opens a *second* scroll inside that. Two scroll owners, stacked. From
> that one fact you get: premature content cut-off, two scrollbars, header
> eating space it can't reclaim, and a quiz that can only append downward
> because it is just another item in a scrolling list.

Fix the scroll model and most of the visible ugliness resolves structurally,
before any restyling.

## New concept: `StudySurface` (the session takeover)

A new shell component that a mode renders when a session is *active*. It claims
the course content viewport and establishes exactly one scroll owner.

```
CourseShell
 └─ <main>                     ← REMOVE overflow behavior here for session routes
     └─ StudySurface           ← NEW. position:relative, fills main, flex-col, min-h-0
         ├─ SessionBar         ← top zone, shrink-0 (floating navbar)
         ├─ StudyStream        ← middle zone, flex-1 min-h-0 — THE scroll owner
         │   └─ (mode blocks: TeachingBlock / AnswerableCard / UserBlock / …)
         └─ ComposeDock        ← bottom zone, shrink-0 (anchored rounded input)
```

Key CSS facts that make it work (call these out to the implementer — they are
the load-bearing lines):

- `StudySurface` is `flex flex-col min-h-0` and is given a real height by its
  parent (see "Height plumbing" below). Not `max-h`. A real height.
- `SessionBar` and `ComposeDock` are `shrink-0`.
- `StudyStream` becomes `flex-1 min-h-0 overflow-y-auto`, and gains a shared
  `mx-auto w-full max-w-3xl` content column wrapped around its blocks.
  Verified in the current file: `StudyStream` today renders
  `ConversationContent` full-width with only `px-5 py-6` padding, no measure
  cap at all. Without adding the `max-w-3xl` column, the stream and
  `ComposeDock` (which does use `max-w-3xl`) will not visually line up once the
  page-scroll cap is removed and the surface gets real width to work with. The `min-h-0` is the
  single most important line: without it a flex child refuses to shrink below
  content size and the *page* scrolls instead of the stream. This is precisely
  the current bug.
- `StudyStream` **loses its own `h-[62vh]`**. It no longer sets its own height;
  it fills the flex slot. The `ai-elements` `Conversation` inside it keeps
  doing stick-to-bottom, now against a correctly-sized parent.

### Height plumbing

**Corrected below after implementation review — the original draft of this
section assumed `CourseShell` was already a fixed-height flex column. It is
not.** Verified in the actual file: the root is `<div className="min-h-dvh
bg-background">`, normal document flow. The side rail is `fixed`, but the
content column is a plain `<div className="pl-14">` containing `TopBar` (not
fixed, not sticky) and then `<main className="mx-auto max-w-screen-2xl px-6
py-8 pb-24 lg:px-10">` — an ordinary block that grows with its content and lets
the whole page scroll. There is no existing flex/height scaffold to hook into;
it has to be built.

**The real fix (do this, not the old sketch):**

1. The content column div (`<div className="pl-14">`) becomes
   `h-dvh flex flex-col overflow-hidden`. This is the new height root for
   everything to its right of the rail.
2. `TopBar` (and the optional tour banner below it) stay in normal flow as
   `shrink-0` children of that column — they do not need their own class
   changes, a flex column's non-flex-1 children already behave as shrink-0
   content by default, but add `shrink-0` explicitly for clarity.
3. `<main>` becomes conditional based on the active route:
   - **Session routes** (`/course/lessons`, `/course/practice`,
     `/course/flashcards`, `/course/diagnostic`, `/course/tutor`):
     `flex-1 min-h-0 flex flex-col overflow-hidden`, **no padding, no
     max-width wrapper**. `StudySurface` fills this directly.
   - **Everything else** (`/course`, `/course/twin`): keep the current
     `mx-auto max-w-screen-2xl px-6 py-8 pb-24 lg:px-10`, but it must also sit
     inside `flex-1 min-h-0 overflow-y-auto` now that its parent is a flex
     column, or the dashboard stops scrolling entirely.

```tsx
// components/shell/CourseShell.tsx — sketch of the corrected structure
const SESSION_ROUTES = [
  "/course/lessons", "/course/practice", "/course/flashcards",
  "/course/diagnostic", "/course/tutor",
];
const isSession = SESSION_ROUTES.some((r) => pathname.startsWith(r));

<div className="min-h-dvh bg-background">
  <nav className="fixed inset-y-0 left-0 z-20 …">{/* unchanged */}</nav>

  {/* was: <div className="pl-14"> — now the height root */}
  <div className="flex h-dvh flex-col overflow-hidden pl-14">
    <div className="shrink-0"><TopBar … /></div>
    {bannerVisible ? <div className="shrink-0">{/* banner, unchanged */}</div> : null}

    <main
      className={cn(
        isSession
          ? "flex min-h-0 flex-1 flex-col overflow-hidden"
          : "mx-auto max-h-full w-full max-w-screen-2xl flex-1 overflow-y-auto px-6 py-8 pb-24 lg:px-10"
      )}
    >
      {children}
    </main>
  </div>
</div>
```

`StudySurface`'s `h-full` is only meaningful once this restructuring lands —
without it, `StudySurface` has no real height to fill and the double-scroll bug
persists exactly as before. **Treat this CourseShell change as a hard
prerequisite for Step 1 (`StudySurface`), not a parallel task.**

Use `dvh` (not `vh`) throughout so mobile browser chrome doesn't clip the dock.

## The shared session grammar

Every mode is the same three zones. What differs is only the **dock mode** and
which **block types** appear in the stream.

| Mode | Stream blocks | Progress | Dock offers |
|---|---|---|---|
| Lesson | Teaching → (inline Check takeover) → Teaching → … | `n/total step` | **Continue** ▸ + **Ask a follow-up** |
| Practice | one AnswerableCard at a time | `n answered` | **Next item** (after grading) + Ask |
| Flashcard | one card at a time (think→choose→reveal) | `n/total card` | **Next card** + Ask |
| Diagnostic | batch of AnswerableCards (silent) | `n/total` | **Submit** (single, at end) — no per-item Ask |
| Tutor | User/Assistant turns | none | free **Ask** + follow-up chips |

The dock is the unifier. In Gizmo the bottom of a lesson is either "Continue" or
"Ask a follow-up," and that *same dock shape* is the tutor's input. Kala adopts
exactly this: one `ComposeDock` component, a `mode` prop, everything routes
through it.

## `ComposeDock` — the heart of the convergence

This is the new component that makes the surfaces feel like one product. It is
the anchored, rounded conversational input at the bottom of every session.

```
┌──────────────────────────────────────────────────────────────┐
│  ▸ Continue        │  Ask Kala a follow-up…            ⌨  ◗  │  rounded-2xl
└──────────────────────────────────────────────────────────────┘
   primary action        free-text compose (PromptInput)     send
```

It has two halves that coexist:

1. **Primary action** (left, `rounded-full`): the mode's forward move —
   "Continue," "Next item," "Next card," "Submit." Orange. This is the default
   thing the student does.
2. **Compose** (right, the `PromptInput` from `ai-elements`): "Ask Kala a
   follow-up." Typing here and sending does NOT advance the session; it injects
   a grounded Q&A turn into the stream and then the primary action re-focuses
   ("point back to Continue when ready," verbatim from the user's ask).

Behaviorally (this is the Gizmo interaction the user described):

- Idle in a lesson step → primary shows **Continue**, compose shows the
  follow-up placeholder.
- Student types a question, sends → an assistant answer turn appears in the
  stream (grounded, does not touch the gate), primary stays **Continue**. They
  can ask again, or continue.
- Student hits **Continue** → the step's Check takes over (see the takeover
  mechanic in `02`), the dock's primary swaps to disabled/hidden until the
  check is answered, compose stays available for "explain this differently"
  style hints if the mode allows.
- Check answered correctly → takeover unmounts, next Teaching turn streams in,
  primary returns to **Continue**.

One component, one visual language, every mode. Tutor is just the degenerate
case where there is no primary action, only compose — which is exactly what it
already is, now wearing the shared dock.

## The quiz "takeover" (not "append")

The user's sharpest complaint: clicking "I understand" appends a new bubble
below and pushes the previous up; Gizmo instead *pops the quiz over the current
message*, hides the chat, and on correct answer *unmounts and reveals* the next
turn.

Architecturally this means the Check is **not another item in the stream
array.** It is an overlay state on the *current step slot*. See `02` for the
exact mechanic, but the architectural rule is:

> The stream renders committed history (teaching turns the student has passed).
> The *current* step is a single slot that can be in one of three visual
> states: `teaching` (bubble + dock Continue), `checking` (the Check card
> occupying the slot, prior bubble visually behind/dimmed), `passed`
> (collapses into history, next slot begins). The Check is a state of the
> slot, never an appended sibling.

This kills the "two bubbles stacking" feel and gives the pop-over/unmount
behavior for free, because mounting/unmounting the Check *is* the transition.

## What stays exactly as-is (contracts you must not break)

- `AnswerableCard`'s grading props, the delayed-spinner, disabled-during-pending
  double-submit fix, the one-shot check/x animation. Restyle the container,
  keep the logic.
- **Where the restyle lands matters.** Verified today: `CornerBrackets` and the
  zero-radius bordered container are applied *per feature file*, not inside
  `AnswerableCard` itself — `LessonChat`, `FlashcardDeck` (twice), and
  `DiagnosticPanel` each independently wrap their own `<div className="relative
  border bg-card"><CornerBrackets />…` around the card, and `PracticePanel`
  doesn't apply brackets at all (it wraps in a shadcn `Card` instead). Four
  independent copies of "what the quiz surface looks like" is exactly the drift
  this redesign is trying to kill. **Move the bracketed, zero-radius container
  into `AnswerableCard` itself** (spec `04` repeats this) so every consumer
  gets the identical surface automatically, and delete the four per-feature
  wrapper divs that currently reimplement it.
- Every `#tour-*` anchor id. The tour selects by id. `06` has the full grep
  list to diff before/after. Moving an anchor to a new element is fine; losing
  one breaks the tour silently.
- Server gating: `result.advance` still decides progression in lessons.
  `skill_id` validation/404s. Diagnostic's batch-silent, submit-once,
  blur-reveal. SRS scoping. All server-side, all untouched.
- `StudySessionShell` — see note below.

## Migration note on `StudySessionShell`

`StudySessionShell` currently renders the progress bar + back + right-slot as a
*top border-bottom row inside the normal flow*. `StudySurface` + `SessionBar`
supersede it. Two options:

- **Preferred:** rename/refactor `StudySessionShell` into `SessionBar` (it
  already owns exactly the back/progress/right-slot chrome — it just needs to
  become the fixed top zone of `StudySurface` instead of an in-flow row, and
  the forward chevron gets added). Keep the file, evolve it, preserve its
  comment history about GamificationSummary living in the topbar.
- Do **not** leave both `StudySessionShell` and a new `SessionBar` in the tree
  doing the same job — that recreates the "two components, same purpose"
  redundancy this whole redesign is removing.

## File-level change map

| File | Change |
|---|---|
| `components/study/StudySurface.tsx` | **NEW** — the 3-zone takeover shell |
| `components/study/SessionBar.tsx` | **NEW** (or refactor of `StudySessionShell`) — floating top nav w/ back, progress, forward |
| `components/study/ComposeDock.tsx` | **NEW** — unified rounded dock: primary action + compose |
| `components/study/StudyStream.tsx` | drop `h-[62vh]`, become `flex-1 min-h-0 overflow-y-auto` slot; wrap blocks in `mx-auto w-full max-w-3xl` to match `ComposeDock`'s measure |
| `components/study/StudySessionShell.tsx` | refactor into `SessionBar` (see note) or retire |
| `features/lessons/components/LessonChat.tsx` | rebuild on StudySurface; Check becomes slot-takeover not appended block |
| `features/practice/components/PracticePanel.tsx` | rebuild on StudySurface; drop inner `Card`; dock "Next item" |
| `features/flashcards/components/FlashcardDeck.tsx` | rebuild on StudySurface; dock "Next card" |
| `features/diagnostic/components/DiagnosticPanel.tsx` | rebuild on StudySurface; dock "Submit"; keep blur/reveal |
| `features/tutor/components/TutorChat.tsx` | rebuild on StudySurface; its input BECOMES ComposeDock (compose-only) |
| `routes/course/lessons.tsx` | remove PageHeader from session; picker stays as pre-session view |
| `routes/course/practice.tsx` | same; recommended card stays on picker |
| `routes/course/flashcards.tsx` | same |
| `routes/course/tutor.tsx` | remove PageHeader eyebrow; tutor is session-only |
| `components/shell/CourseShell.tsx` | `<main>` height flag for session routes (approach A) |
| `components/study/TeachingBlock.tsx` | restyle to radius rule; no logic change |
| `components/study/AnswerableCard.tsx` | **owns** the bracketed zero-radius quiz container now (moved in from each feature file); logic untouched |
| `components/study/TopicLanding.tsx` | stays (pre-session picker); minor: it is the "deck materials" view, see `05` |

## Sequencing (so the tree never half-breaks)

Detailed in `06`, but the shape: build the three new shared components first
(they compile standalone), migrate **Lessons** first (it is the surface with
the takeover mechanic and the loudest bug — proving it there de-risks the rest),
then Practice/Flashcards (simpler, single-card), then Diagnostic (keep its
special mechanics), then Tutor (it is nearly there already). Each mode is one
reviewable step, same discipline as Stages 1–4.
