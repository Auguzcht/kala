# Sequencing, Guardrails, and Codex Handoff

How to actually execute this without half-breaking the tree, what to check at
each step, and the copy-paste-able notes for driving Codex CLI through it.

> **Revision note:** this package went through one implementation review before
> Step 0 (an independent pass that read the actual `CourseShell`, `PromptInput`,
> `TourRunner`, and per-feature `CornerBrackets` usage against the original
> draft). Eight corrections came out of it and are now folded into `01`, `02`,
> `03`, `04`, `05`, `07`, and this file: the `CourseShell` height plumbing was
> wrong (the shell has no existing flex/height scaffold — it had to be
> designed, not just flagged), `ComposeDock`'s rounding targeted the wrong DOM
> node, the tutor tour anchor's "textarea" wording risked breaking
> `requestSubmit()`, the follow-up-ask feature needed explicit design
> decisions instead of being folded into "presentation only," "orange once per
> view" was imprecise given the progress-fill/focus-ring uses already in the
> plan, the stream and dock had no shared measure, `AnswerableCard` needed to
> own the quiz container instead of four per-feature copies, and the Lessons
> takeover needed a sharper anti-pattern warning so a superficial restyle
> couldn't pass as the real fix. All corrections are inline at their point of
> relevance, not just listed here — read the specs as written now, not as a
> delta.

---

## Guardrails (check every stage against these before moving on)

Same spirit as the original overhaul's non-negotiables:

- [ ] **One scroll owner per session.** After each mode migrates, resize the
      window short and confirm ONLY the stream scrolls — the bar and dock stay
      fixed, the page itself does not scroll. This is the whole point; verify it
      every time.
- [ ] **No backend/gating regression.** `result.advance` still gates lessons.
      `skill_id` validation/404s. Diagnostic batch-silent + submit-once +
      blur-reveal. SRS scoping. Grading server-side. Zero changes to any router,
      migration, or hook's server contract. (The one intentional new frontend
      capability, follow-up ask on Lessons/Practice/Flashcards, still hits the
      existing `askTutor` endpoint unchanged — see `03`'s callout. "No server
      contract changes" does not mean "no new frontend capability" here; be
      precise about that distinction when reviewing.)
- [ ] **Every `#tour-*` anchor still resolves.** Grep the full list before you
      start and after each mode (command below). An anchor may move to a new
      element; it may not vanish.
- [ ] **`AnswerableCard` is restyled, never forked.** Its grading logic,
      delayed-spinner, disabled-during-pending, one-shot animation stay. Only
      its container styling changes to match the radius rule.
- [ ] **Radius rule held** (lint section below). No component picks a radius for
      "feel."
- [ ] **Each mode is one reviewable step.** Don't stack unreviewed modes.

---

## The radius lint (the thing an implementer will accidentally violate)

The single easiest way to wreck this redesign is to "tidy" the radii into
uniformity — that is literally the SaaS-card-kit tell the design is fighting.
Enforce this table; treat deviations as bugs:

| Element | Class | NOT |
|---|---|---|
| Session bar, quiz/answer card container | (no radius) + `border`/brackets | not `rounded-*` |
| Answer option buttons | `rounded-md` | not `rounded-full`, not `rounded-none` |
| Teaching bubble | `rounded-md` | not `rounded-2xl`, not `rounded-lg` |
| Compose dock input | `rounded-2xl` | not `rounded-md`, not square |
| Primary advance (Continue/Next/Submit) | `rounded-full` | not `rounded-md` |
| Back/forward chevrons | `rounded-full` | not square |

Quick self-audit grep after building (should return only the intended files):

```bash
# rounded-2xl should appear ONLY in ComposeDock
grep -rn "rounded-2xl" apps/web/src/components/study apps/web/src/features
# rounded-full on interactive controls should be SessionBar chevrons +
# PrimaryAdvance only (plus pre-existing avatar/badge uses)
grep -rn "rounded-full" apps/web/src/components/study
```

If `rounded-2xl` shows up on a teaching bubble or a quiz card, that is the tell
creeping back in — revert it.

---

## Tour anchor manifest (grep before and after EVERYTHING)

```bash
# Authoritative list the tour selects by:
grep -rho "tour-[a-z-]*" apps/web/src/components/shell/student-tour.ts | sort -u
# What actually exists in the components right now:
grep -rho "tour-[a-z-]*" apps/web/src | sort -u
# Diff these two sets before you start. After each mode migration, re-run the
# second command and confirm no id from the first list disappeared.
```

Known anchors by surface (from the current tree):
- Lessons: `tour-lesson-generating`, `tour-lesson-explain`,
  `tour-lesson-continue`, `tour-lesson-check`, `tour-lesson-check-feedback`,
  `tour-lessons-picker`, `tour-lessons-first-card`
- Practice: `tour-practice-picker`, `tour-practice-recommended`,
  `tour-practice-card`, `tour-practice-choices`, `tour-practice-feedback`
- Tutor: `tour-tutor-input`, `tour-tutor-thinking`, `tour-tutor-response`
- Shared: `tour-first-choice` (AnswerableCard default; diagnostic passes null)
- Rail: `nav-workspace`, `nav-diagnostic`, `nav-lessons`, `nav-practice`, …

Placement destinations are given in each mode's spec (`03`, `04`, `05`).

---

## Sequencing

Build order chosen so the tree always compiles and each step is independently
reviewable.

### Step 0 — CourseShell height flag
`components/shell/CourseShell.tsx`: make `<main>` a fixed-height, non-scrolling
flex container for the session routes (`/course/lessons`, `/course/practice`,
`/course/flashcards`, `/course/diagnostic`, `/course/tutor`), scrolling as
today for `/course` and `/course/twin`.

```tsx
// sketch — read the active route, swap main's classes
const SESSION_ROUTES = ["/course/lessons","/course/practice","/course/flashcards","/course/diagnostic","/course/tutor"];
const isSession = SESSION_ROUTES.some((r) => location.pathname.startsWith(r));

<main className={cn(
  isSession
    ? "flex min-h-0 flex-col overflow-hidden" // fills the row, no page scroll
    : "mx-auto max-w-screen-2xl px-6 py-8 pb-24 lg:px-10", // unchanged
)}>
  {children}
</main>
```
The parent of `<main>` must give it a real height (the shell is already a
`h-screen`/`h-dvh` flex column with the topbar as a shrink-0 row — confirm and,
if needed, add `min-h-0` to the row that contains `<main>` so it can shrink).
Ship this first; nothing else depends on visuals yet and it is the load-bearing
layout change.

### Step 1 — the three shared components (`02`)
`StudySurface`, `SessionBar` (refactor `StudySessionShell`), `ComposeDock` +
`PrimaryAdvance`. They compile standalone. Add `ChevronRightIcon` if missing.
Do not wire any mode yet.

### Step 2 — Lessons (`03`)
The hardest and highest-signal. Rebuild `LessonChat` on the shared components
with the Check-takeover mechanic; strip the header in `routes/course/lessons.tsx`.
Review here hardest — this is where the takeover pattern is proven. **Watch the
tour click-through of `tour-lesson-continue` now that it's in the dock.**

### Step 3 — Practice, then Flashcards (`04`)
Both are single-card, mechanical after Lessons. Practice first (simpler, no
phase machine), then Flashcards (keep the phase machine + optional skillId).

### Step 4 — Diagnostic (`04`)
Keep batch-silent + submit-once + blur/reveal. Dock is Submit-only (no compose).

### Step 5 — Tutor (`05`)
Nearly there already; make its input the shared `ComposeDock` (compose-only),
switcher into the bar. Preserve `tour-tutor-input` on the `PromptInput` form
(NOT the textarea — `TourRunner` calls `requestSubmit()` on this id, which only
exists on `<form>`; see `05`).

### Step 6 — sweep
- Retire `StudySessionShell` if you created a separate `SessionBar` (don't leave
  both). If you refactored in place, delete nothing.
- Radius-lint grep. Tour-anchor grep diff. One-scroll check on every surface.
- Reduced-motion pass: the takeover pop and any dock transitions respect
  `useReducedMotion`.

---

## Manual verification checklist (run at the end)

- [ ] Lessons: one scrollbar; no "Guided lessons" header in-session; Continue →
      check takes over the step (doesn't append below); correct → pops out,
      next step reveals; ask-a-follow-up injects a turn without advancing.
- [ ] Practice: no inner "Quick practice" card header; Next item in the dock;
      recommended card only on the pre-session picker.
- [ ] Flashcards: think→choose→reveal intact; Next card in the dock; due-review
      default on picker; skillId still optional.
- [ ] Diagnostic: N cards, no per-item reveal, Submit in dock, blur→delta reveal
      intact, no duplicate `tour-first-choice` ids.
- [ ] Tutor: input is the same rounded dock as lessons; switcher in bar;
      attachments work; `tour-tutor-input` resolves and tour can submit it.
- [ ] All surfaces: back chevron returns to the picker; the rounded dock is the
      ONLY `rounded-2xl` element; exactly one orange *primary action* per view
      (progress fill and focus rings are semantic exceptions, not second
      primaries — see `00`).
- [ ] Reduced motion honored; keyboard focus visible on dock + primary + back.
- [ ] Instructor dashboard untouched and still fine.

---

## Driving Codex CLI (suggested prompts)

Feed Codex one step at a time, in order, pointing it at the matching spec file.
Example prompts:

> Read `docs/ai-overhaul-v2/01_ARCHITECTURE.md` and `02_SHARED_COMPONENTS.md`.
> Implement Step 0 and Step 1 from `06_SEQUENCING_AND_HANDOFF.md` only: the
> CourseShell height flag and the three new shared components
> (`StudySurface`, `SessionBar` refactored from `StudySessionShell`,
> `ComposeDock` + `PrimaryAdvance`). Add `ChevronRightIcon` if it doesn't
> exist. Do not migrate any feature yet. Keep every existing `#tour-*` anchor.
> Hold the radius rule in the spec exactly.

Then, after review:

> Now Step 2: rebuild `LessonChat` per `03_LESSONS_TAKEOVER.md`. The Check must
> take over the current step slot (dimmed teaching behind), not append as a new
> stream block. Move Continue/Next/Try-again into the ComposeDock. Strip the
> PageHeader from `routes/course/lessons.tsx` in-session. Preserve all five
> `tour-lesson-*` anchors — verify `tour-lesson-continue` still resolves now
> that it's the dock's primary button. Don't touch grading or `result.advance`.

…and so on per step. Keep each Codex run to one sequencing step so each is
independently reviewable, matching the original overhaul's stage discipline.

After each Codex run, before accepting:
```bash
grep -rho "tour-[a-z-]*" apps/web/src | sort -u   # diff vs the manifest
grep -rn "rounded-2xl" apps/web/src/components/study apps/web/src/features
npm run build   # or the repo's typecheck/build task
```

---

## One-paragraph version (if you read nothing else)

Session surfaces today have two scroll owners because `StudyStream` sets its own
`h-[62vh]` inside a scrolling page — fix that by making a live session a
viewport takeover (`StudySurface`) with exactly three zones: a fixed
`SessionBar` (back / progress / forward), the stream as the single scroll
owner, and a fixed `ComposeDock`. The dock is the unifier: an orange
`rounded-full` primary (Continue / Next / Submit) plus a `rounded-2xl` compose
("ask a follow-up") — the ONLY rounded elements on an otherwise boxy instrument
panel, echoing the launch line. In lessons the comprehension check *takes over
the current step's slot* instead of appending below. Strip the eyebrow/"Work
through it" headers from every in-session view. Keep every tour anchor, every
server contract, and `AnswerableCard`'s logic exactly. Build the shared
components first, migrate Lessons first, then the quiz surfaces, then Tutor,
one reviewable step each.
