# Component libraries: what to take, what to leave

You asked me to go through tailark, tailgrids, motion-primitives, reactbits,
shadcnstudio, shadcnblocks, shadcn.io, shadcn/ui, and lucide-animated.

Before the list, the rule that decides most of it — from your own
`apps/web/src/styles/DESIGN.md`:

> Do not import Aceternity / Tailark / Magic UI flourishes into the
> daily-use app surfaces. Marketing components stay in
> `src/components/marketing/`.

That line is correct and it already answers half the question. Kala's thesis
is "a measurement instrument and learning ledger". Spotlight cards, aurora
backgrounds, and animated gradient text are the visual language of a
landing page, and dropping them into `/class/*` would make the product look
*less* credible to an academic audience, not more. The instructor dashboard
does not need more sparkle; it needed more information, which is what the
polish pass actually added.

So: yes to primitives that carry information or improve interaction, no to
decoration on app surfaces.

---

## Take these

### shadcn/ui — the namespace change is the real find

shadcn now ships three implementations of each component (`base`, `aria`,
`radix`). You are on Radix, which the `radix-ui` dependency in
`apps/web/package.json` confirms, so stay in that namespace for consistency.

Components you do not have that would earn their place:

| Component | Where it goes |
|---|---|
| **Item** | Roster rows, plan rows, recommendation cards. Replaces hand-rolled flex row markup in three places. |
| **Empty** | You have `EmptyState` already; `Empty` is the same idea with better composition slots. Only worth it if you are touching them anyway. |
| **Field** | The decision form in `DecisionCenter`. Label + control + description + error as one unit, instead of manual `Label` + `Input` pairs. |
| **Data Table** | The roster. I hand-rolled sort, filter, search, and pagination because adding TanStack Table under deadline is a bad trade. If the roster grows more columns, migrate. |
| **Sidebar** | The persistent left rail from your professor's mockup. Real improvement, wrong week. |
| **Kbd** | If you add a command palette. You already have `cmdk` installed and unused. |

```
pnpm dlx shadcn@latest add radix/item radix/field
```

**Slider** (the page you linked): the honest answer is you have no use for
it right now. The one place it could go is a blueprint-weight control on the
skill review panel, letting an instructor dial how much a skill counts
toward readiness. That is a genuinely good feature and it is not this week's
feature.

### motion-primitives — you are already using it correctly

`in-view`, `transition-panel`, `animated-group`, and `text-effect` are
already vendored into `src/components/motion/`. Two more that would encode
real state change rather than decorate:

- **`sliding-number`** — for the KPI tiles. When cohort readiness moves from
  62% to 63% after a decision, the digit rolls. That is motion reporting a
  real change, which is exactly what DESIGN.md asks for.
- **`disclosure`** — smoother than raw Collapsible for the recommendation
  cards, though `Collapsible` is fine and already in place.

Skip `border-trail`, `glow-effect`, `spotlight`, `tilt`, `magnetic`. Those
are marketing.

### lucide-animated — already wired

Your `components.json` already registers the `@lucide-animated` registry and
you have fourteen of them vendored. The new components use `SparklesIcon`,
`CheckIcon`, `XIcon`, `ZapIcon`, and `ChevronLeftIcon` from what you have.
Nothing more needed.

One note: these animate on hover by default. On the instructor surface that
is fine for buttons and wrong for status indicators — a flag icon that
wiggles when you mouse past it reads as playful, and "needs support" should
not read as playful.

---

## Leave these for the marketing site

**tailark** and **tailgrids** are marketing block libraries: heroes,
pricing tables, feature grids, testimonial sections. Genuinely useful when
you build the Kala landing page or the conference microsite. They have no
business inside `/course/*` or `/class/*`.

**reactbits** is animation showcase work — SplitText, Aurora, Particles,
ClickSpark, DecryptedText. Same verdict, more strongly. `CountUp` is the one
thing there you might want, and motion-primitives' `sliding-number` does the
same job in a library you already use.

**shadcnblocks** is a paid block library aimed at marketing pages. Not worth
a licence for this.

**shadcnstudio** is mostly theme generation. Your palette is locked from the
brand board and encoded in `globals.css`. Do not regenerate it.

**shadcn.io** is an aggregator. Worth a browse for one specific thing: it
indexes registries that ship Gantt, Kanban, and calendar components. If a
future phase needs a course timeline view, look there first. Nothing for
this submission.

---

## Quality-of-life primitives: status

You said the UI lacked the small things that make it feel alive. Where they
stand after the pass:

| Primitive | Before | Now |
|---|---|---|
| **Sonner toasts** | `Toaster` mounted in `RootLayout.tsx`, **zero `toast()` calls in the entire codebase** | Fires on every decision, on generation success and failure, with distinct copy for approve / modify / decline. Sonner stacks by default. |
| **Collapsible** | Component existed, used nowhere meaningful | Recommendation cards, decision history, the skill-mapping section on the overview |
| **Pagination** | Only inside `TwinBody`'s skill list | Roster, 10 per page |
| **Sheet** | Component existed, unused | The roster drill-down |
| **Tabs** | Barely used | Learner record (Decide / Mastery / Activity), class overview (Trends / Heatmap) |
| **Switch + Label** | Unused | The de-identify toggle, in two places |
| **Table** | Unused | The roster |
| **Tooltip** | Rare | KPI tiles explain what each number means and where it comes from |
| **ToggleGroup** | Unused | Roster status filter |
| **Select** | Rare | Changing the activity type when modifying a recommendation |
| **Spinner** | Unused | Inline in buttons during generation and decision |

The gap was never that the primitives were missing. Almost all of them were
already installed. They were installed and not called.

---

## One thing worth adding that is not on your list

**Optimistic updates on the decision mutation.** Right now approving a
recommendation waits for the round trip before the card updates. Under
TanStack Query, `onMutate` with a cache update would make the decision feel
instant, which matters a lot in a screen recording where a two-second pause
reads as a bug. It is about fifteen lines in
`useDecideRecommendation`, and it is the single highest-impact polish left.
