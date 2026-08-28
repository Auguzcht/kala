# Frontend fixes: use what's already built

This isn't a request for new visual direction. Kala already has a design
system and a written brief (`apps/web/src/styles/DESIGN.md`). The problem is
the newer work (flashcards, lessons, gamification, twin lists) didn't use
what's already sitting in the repo. Every item below points at a specific
file and a specific existing resource — nothing here requires inventing a
new component.

## The audit (run yourself before touching anything, to confirm the baseline)

```
grep -rl "from \"@/components/motion" src/features src/routes   # → 0 matches
grep -rl "components/ui/pagination\|Pagination" src/features src/routes  # → 0 matches
grep -rl "Accordion\|components/ui/accordion" src/features src/routes   # → 0 matches
grep -rl "Skeleton" src/features/flashcards src/features/lessons src/features/gamification  # → 0 matches
```

Four component families exist in the repo and are used **nowhere** in
`features/` or `routes/`: `components/motion/*` (animated-group, in-view,
text-effect, transition-panel), `components/ui/pagination.tsx`,
`components/ui/accordion.tsx`, and `Skeleton` outside one legacy file
(`TwinView.tsx`). That's the "not using shadcn" and "what happened to the
motion" feeling, made concrete.

Worse, two of DESIGN.md's seven named **signature elements** don't do what
their own spec says:

- `components/kala/mastery-radar.tsx` — spec (DESIGN.md §Signature elements
  #1): "Subtle pulse animation when an evidence event updates a node."
  Actual: zero `motion`/`animate` in the file. Static.
- `components/kala/evidence-ledger.tsx` — spec (#4): "new events slide in,
  color-coded by type." Actual: zero `motion`/`AnimatePresence` in the file.
  Static.

Compare `components/kala/mastery-ring.tsx`, which does exactly what its spec
says (#3: "fills and animates on update, never a flat bar") — it imports
`motion`/`useReducedMotion` from `motion/react` and animates
`strokeDashoffset` on change, respecting reduced motion. **This is the
reference implementation.** Match its pattern everywhere else in this list,
don't invent a new one.

DESIGN.md's actual motion principle, quoted directly so it's not
reinterpreted: *"Motion encodes state change, not vanity... If an animation
does not report a real change, cut it."* Every fix below is motion tied to a
real state transition (a card flips, a step advances, an evidence event
lands), never decoration.

---

## P0 — real bugs, fix first

**1. Practice page: answer choices overflow the viewport.**
Screenshot: long MCQ choice text runs off the right edge, uncontained. This
is a missing wrap, not a design call — find the choice button/row markup in
the practice/diagnostic shared components and ensure `whitespace-normal`
plus a bounded width (`max-w-full`, `break-words`) is actually applied. Check
whether a parent is forcing `flex-nowrap` or `overflow-x` without a wrap
class on the child.

**2. Twin radar chart is illegible past ~8 skills.**
`components/kala/mastery-radar.tsx` renders one spoke per skill with full
skill-name labels; at 16 skills (screenshot: CPE101) labels overlap and clip
mid-word. This is a data-cardinality problem, not a styling one. Fix:
aggregate the radar to the six Bloom levels (Remember → Create, matching the
existing `BloomsLadder` legend already in the design system) instead of one
spoke per skill — average mastery within each level. Keep the full per-skill
detail in the `Skills` list below it, where it already reads fine. This also
finally gives the radar a legitimate reason to pulse per-node (see P1 below):
6 stable nodes, not 16 that reflow every time a skill is added.

---

## P1 — wire in what already exists

**3. Loading states: replace bare text with the hornbill + Skeleton.**
DESIGN.md's signature element #7: *"The hornbill as guide. Tutor avatar,
onboarding guide, empty states, **loading moments**."* Right now, loading
is a plain string: `"Building your deck..."` (flashcards),
`"Building your baseline"` (course home empty state, this one's actually
close to spec already). Every first-load / generation wait across
flashcards, lessons, and diagnostic should use the hornbill mark (already
used elsewhere as `/assets/kala-mark.png`, see `WorkspaceHome` in
`routes/course/index.tsx`) plus `Skeleton` blocks shaped like the content
that's coming (a skeleton MCQ card, a skeleton lesson step), not a spinner or
a line of text. The lesson page already has real generation-progress
semantics (`status === "generating"`, polled every 2s in `use-lessons.ts`) —
use that as the model for what flashcards' deck-seeding wait should feel
like too, even though it has no formal status field yet.

**4. `MasteryRadar`: implement the pulse the spec already calls for.**
When an evidence event moves a skill's mastery (any `useReviewFlashcard`,
`useSubmitDiagnostic`, or lesson-check success that returns an updated
`mastery`/`estimate`), the corresponding radar node should pulse once, using
the exact pattern in `mastery-ring.tsx`: `motion` + `useReducedMotion`,
animate on the value transition, `duration: 0` when reduced motion is on.
This also naturally resolves once #2 lands (six Bloom-level nodes are a
sensible thing to pulse; sixteen skill nodes reflowing every time was not).

**5. `EvidenceLedger`: implement the slide-in the spec already calls for.**
New rows should enter via `AnimatePresence` + `motion.div` (see
`transition-panel.tsx` for the exact `AnimatePresence` setup already in the
repo), color-coded by evidence type (`diagnostic`/`practice`/`flashcard`/
`tutor` — the type already exists on `evidence_events`, just isn't used for
color here). This is append-only data hitting a live list, it's the
textbook case `AnimatePresence` exists for.

**6. `FlashcardDeck.tsx`: use `TransitionPanel` for its own phase machine.**
This component already has a `type Phase = "think" | "choose" | "answered" |
"revealed"` state machine (good) that currently hard-cuts between phases
(no transition at all). `components/motion/transition-panel.tsx` is
*exactly* built for this: `activeIndex` + an array of children, animated
enter/exit. Map `Phase` to an index and drop the four phase renders into a
`TransitionPanel`. Real state change (think → choose → graded), not vanity.

**7. `LessonStepper.tsx`: same `TransitionPanel` pattern for step advances.**
Advancing from step N to step N+1 (gated on `advance: true`) currently swaps
content instantly. Use `TransitionPanel` keyed on the current step index —
same component, same justification as #6.

**8. Wire in `components/ui/pagination.tsx`.**
Two screens are flat unpaginated lists of 16+ items with zero pagination
component in the entire codebase:
   - Lessons list (`routes/course/lessons` or wherever the skill picker
     lives) — pair with **grouping by `module_ref`** first (it's already on
     every skill, unused for display), then paginate within a module if
     still long. `components/ui/accordion.tsx` (also currently unused) is a
     good fit for collapsible per-module groups.
   - Twin's `Skills` list (`TwinBody.tsx`) — same treatment: group by
     Bloom level (using the existing `BloomsLadder` order) or module, then
     paginate.
   Don't paginate the flashcard deck itself — it's a one-at-a-time queue by
   design, pagination doesn't apply there.

**9. Page-level entrance motion — sparingly, per the brief's own restraint rule.**
`components/motion/in-view.tsx` and `animated-group.tsx` exist and are
unused anywhere. Appropriate, restrained uses: a single `InView` fade-up on
the Lessons list and Twin skills list when they first mount with real data
(not on every re-render, not on the course home quick-links grid — that one
already works and doesn't need help). This is the one place "vanity" motion
is close to acceptable, so keep it subtle (opacity + small y-offset, default
variants in `in-view.tsx` are already tuned for this) and don't reach for
`animated-group`'s flashier presets (`bounce`, `flip`, `rotate`, `swing`) —
those read as decoration, not state change, and DESIGN.md's own rule cuts
them.

---

## What NOT to do

- Don't redesign the color system, typography, or layout grid. The brief
  (DESIGN.md) is specific and already followed correctly in most of the
  older screens (twin, instructor dashboard). This is about consistency,
  not a new aesthetic.
- Don't add motion to something that isn't a real state change. Re-read the
  quoted principle before adding any new `motion.div` not listed above.
- Don't skip `prefers-reduced-motion` on any new animation — every instance
  above has a `useReducedMotion` check in its reference implementation
  (`mastery-ring.tsx`); copy that pattern exactly, don't reimplement it.

## Suggested order

P0 items (1–2) first, they're user-visible breakage. Then 3 (loading, high
visibility, low risk). Then 6–7 (TransitionPanel, contained to two
components you already own from the last pass). Then 4–5 (the two
signature elements that don't match their own spec). Then 8–9 (pagination/
grouping, entrance motion) last, since they touch the most files for the
least urgent payoff.
