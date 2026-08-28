# Two things: animated icons (with exact commands) and why Tutor/Lessons/Flashcards look untouched

## Why you only see changes on Twin

This is the honest answer, not a deflection: the Twin bento grid got built
because I built it directly with tool access in the last pass. The bigger
ask from the turn before that — one shared "AI session shell" and one
reusable "answerable card" component for Tutor/Lessons/Flashcards/Practice —
got correctly *identified* as the real fix, but I only wrote it up as a
recommendation ("worth its own design/engineering conversation") and never
turned it into a buildable spec or built it. That's on me, not something
deepseek skipped. Section 2 below fixes that: it's now a real spec with file
paths and a migration order, not a suggestion.

---

## 1. Animated icons — real commands, verified against lucide-animated's actual docs

Confirmed the install mechanism directly rather than guess: each icon is a
separate shadcn registry item, installed via

```
pnpm dlx shadcn add @lucide-animated/<icon-name>
```

(source: lucide-animated.com's own installation docs). It requires Motion as
a dependency — already satisfied, `mastery-ring.tsx` already imports from
`motion/react`, so no new dependency conflict. Each install copies a real
component file into the project (respects `components.json`'s aliases), so
after installing you import the animated version by name instead of the
static `lucide-react` one at that specific call site — **do not global
find-replace every lucide-react import**, only the ones listed below, each
tied to a real state change per DESIGN.md's own rule ("motion encodes state
change, not vanity").

**First, the actual finding that matters:** `FlashcardDeck.tsx` and
`TutorChat.tsx` currently import **zero** icons from `lucide-react`. There's
nothing to animate there yet because there's nothing there at all — that's
a different problem than "icon isn't animated," and it's the real reason
those two screens read as unfinished. Section 2 covers adding real icons to
both as part of the shared-card/shell work; don't bolt icons onto the
current one-off layouts first.

### Confirmed swap points (icons that exist today)

```
pnpm dlx shadcn add @lucide-animated/flame
pnpm dlx shadcn add @lucide-animated/target
pnpm dlx shadcn add @lucide-animated/circle-check
pnpm dlx shadcn add @lucide-animated/circle-x
pnpm dlx shadcn add @lucide-animated/arrow-right
pnpm dlx shadcn add @lucide-animated/chevron-left
pnpm dlx shadcn add @lucide-animated/layout-grid
pnpm dlx shadcn add @lucide-animated/clipboard-list
pnpm dlx shadcn add @lucide-animated/book-open
pnpm dlx shadcn add @lucide-animated/layers
pnpm dlx shadcn add @lucide-animated/messages-square
pnpm dlx shadcn add @lucide-animated/radar
```
(Confirm each exact slug against lucide-animated.com's catalog before running
— icon names occasionally differ slightly from the plain-Lucide name, e.g.
`CheckCircle2` → `circle-check`.)

| File | Icon | Trigger (the state change) |
|---|---|---|
| `features/practice/components/PracticePanel.tsx` | `CheckCircle2` / `XCircle` | Animate ONCE when the graded result lands (correct vs. incorrect) — this is the single best-justified use in the whole app, a real answer just got graded. |
| `features/practice/components/PracticePanel.tsx`, `features/twin/components/TwinBody.tsx`, `features/gamification/components/GamificationSummary.tsx` | `Flame` | Animate when `streakDays` increases from the previous render (compare against a ref, same pattern already used for the practice XP-gain toast) — not on every render, only on the actual increment. |
| `features/twin/components/TwinBody.tsx` | `Target` (Focus area) | A subtle one-shot animation on mount when the focus skill changes (i.e. keyed on `focus.skillId`), not looping. |
| `features/twin/components/TwinBody.tsx`, `routes/course/index.tsx` | `ArrowRight` | Hover-triggered nudge on the CTA buttons ("Practice this →", "Start practice →") — a real interaction cue, not autoplay. |
| `components/shell/CourseShell.tsx` | All seven nav icons (`LayoutGrid`, `ClipboardList`, `BookOpen`, `Target`, `Layers`, `MessagesSquare`, `Radar`) | Animate on hover and on becoming the active route — this is genuinely well-suited to lucide-animated's hover-triggered variants, and it's the one place in the app a user's cursor visits constantly. |
| `routes/course/lessons.tsx` | `ChevronLeft` ("Choose another skill") | Hover-triggered nudge, same idea as ArrowRight above. |

**Do not** animate icons with a continuous loop anywhere (no perpetual
spinning/pulsing decoration) — every trigger above is either hover or a
one-shot tied to a real event, matching the restraint DESIGN.md already
established for the rest of the app's motion.

---

## 2. The shared AI session shell + reusable answerable card — now a real spec

This is the actual fix for "Tutor/Lessons/Flashcards look untouched." Build
two new shared pieces, then migrate the four surfaces onto them one at a
time.

### 2a. `components/study/StudySessionShell.tsx` (new)

The floating persistent chrome — modeled on the Gizmo reference: a top bar
that stays in place while content underneath swaps, holding streak/XP
(reuse `GamificationSummary`'s data via `useGamification`), a back/skip
affordance, and a slim progress indicator whose meaning is passed in by the
caller (session answer count for Practice, step N/total for Lessons, card
N/total for Flashcards). Props roughly:

```ts
type StudySessionShellProps = {
  courseId: string;
  progress?: { current: number; total: number; label?: string };
  onBack?: () => void;
  children: React.ReactNode;
};
```

It owns only the chrome. It does not know what's inside — Tutor, Lessons,
Flashcards, and Practice all render their own content as `children`.

### 2b. `components/study/AnswerableCard.tsx` (new)

The reusable question/content card — this is the piece Gizmo reuses between
its quiz and its chat follow-ups, and the piece Kala currently has four
separate bespoke implementations of (`PracticePanel`'s choice buttons,
`FlashcardDeck`'s inline MCQ, `LessonStepper`'s check block, and
`DiagnosticPanel`'s question block all do the same thing slightly
differently). One component:

```ts
type AnswerableCardProps = {
  prompt: string;
  choices: { id: string; label: string }[];
  selectedId: string | null;
  onSelect: (choiceId: string) => void;
  result?: { correct: boolean; explanation: string } | null;
  isPending?: boolean;
  actions?: React.ReactNode; // Hint / Reveal / Explain slot, varies by surface
};
```

Handles: choice rendering with the hover/selected states already correct in
`PracticePanel` (reuse that exact styling, it's right), the disabled-during-
`isPending` fix already shipped there, and the graded-result display
(explanation, band transition) already correct in `PracticePanel`/
`FlashcardDeck`. Pull the best version of each piece from wherever it's
currently most correct rather than rewriting from scratch — `PracticePanel`
already has the double-submit fix and hover states, `FlashcardDeck` already
has the terminal `revealed` phase logic. Merge forward, don't discard.

### 2c. Migration order (do NOT do all four at once)

1. **Practice first.** It's already the most correct implementation (hover
   states, pending-disable fix, dynamic mastery/XP delta rendering already
   built). Extract its choice-card markup into `AnswerableCard` with minimal
   behavior change, wrap the page in `StudySessionShell`. This proves the
   two new components work before anything else depends on them.
2. **Flashcards second.** Swap its inline MCQ rendering for `AnswerableCard`
   (passing Hint/Reveal/Explain as the `actions` slot), wrap in
   `StudySessionShell` with `progress` set to the deck position (`1/10`
   etc., already computed). This is also where Flashcards gets real icons
   for the first time (Hint/Reveal/Explain each want one).
3. **Lessons third.** The step content (summary/bullets/misconception/
   key-takeaway) is NOT an `AnswerableCard` — that part stays bespoke to
   Lessons. Only the comprehension-check block at the bottom of each step
   becomes an `AnswerableCard`. Wrap the whole stepper in
   `StudySessionShell` with `progress` set to `step N / total`.
4. **Tutor last, and different.** Tutor's chat is NOT an `AnswerableCard`
   use case (free-form Q&A, no choices) — it only adopts
   `StudySessionShell` for the chrome (no meaningful `progress` value, pass
   nothing) and needs real icons added for the first time: a send icon on
   the Ask button, and consider a `MessagesSquare`-family icon in the empty
   state alongside the hornbill. This is also where the earlier "give Tutor
   real suggestion chips built from the student's weakest skills" idea
   belongs, once the shell exists to hold them.

### What NOT to do

- Don't touch Diagnostic in this pass — it's a fixed one-time baseline
  instrument, structurally different enough (whole-page-of-questions, not
  one-at-a-time) that forcing it into `AnswerableCard`/`StudySessionShell`
  isn't a clean fit. Leave it as-is.
- Don't do all four migrations in one PR. Practice first, confirm nothing
  regressed (typecheck + lint + build + a manual click-through), then move
  to the next.

## Priority

Section 2 (the shell + card refactor) is the real fix and should happen
first — it's the reason three of four surfaces still look unfinished.
Section 1 (animated icons) is real but secondary, and naturally slots in
*during* the Flashcards and Tutor migrations (step 2 and 4 above) rather
than as a separate pass, since that's exactly when those two surfaces get
icons for the first time.
