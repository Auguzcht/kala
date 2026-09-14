# Kala Study Surface Redesign — Design Plan (v2)

This is the design brief and plan for the student-facing AI study surfaces.
It is the "why" behind the component specs in this folder. Read it first, then
`01_ARCHITECTURE.md`, then the per-component specs.

## The brief, stated plainly

Kala is an LTI-embedded AI tutor that lives inside Blackboard. It is an
extension of an LMS, so it has to read as **institutional and trustworthy**,
not as a consumer study-toy. But the product it is competing against on feel
is Gizmo.AI, whose whole strength is that it centers one thing — the AI — and
lets every mode (lesson, quiz, flashcard, tutor) feel like the same continuous
conversation with it.

Today Kala has the opposite problem. The AI overhaul (Stages 1–4) unified the
plumbing — every surface renders through `StudyStream` on `ai-elements` — but
the surfaces still *present* as four unrelated features. Same topic picker
bolted in front of two different experiences, a lesson that looks nothing like
a conversation, two scrollbars fighting each other, a quiz that shoves the
current message up the page instead of taking over. The plumbing got unified;
the experience did not.

The job of this redesign: make the AI the visible center of gravity, the way
Gizmo does, **without** borrowing Gizmo's soft rounded-everything consumer
skin — because Kala already has its own equity to protect.

## What Kala already owns (do not throw away)

Two things in the current build are genuinely Kala and must survive:

1. **The instrument-panel box.** Hairline slate borders, near-zero radius on
   data surfaces, corner brackets (`[ ]`) as the signature tick on panels the
   student must read precisely. This is the "Blackboard-remembers-you"
   utilitarian box feel. It is correct. The instructor dashboard is built on it
   and needs no change.

2. **The launch line.** One continuous orange rounded stroke, drawn on load
   (`routes/launch.tsx`). This is the brand's one moment of elegance — a single
   confident curve against all those right angles. It tells you the whole
   design thesis in one gesture: **utilitarian box, one elegant line.**

The redesign's entire aesthetic rule falls out of #2:

> **Boxes for what you read. The rounded line for what you do with the AI.**

Radius is not decoration here — it is *signage*. A right angle means "this is
content/data, read it." A generous radius means "this is a live conversational
affordance, act through it." Right now those two vocabularies are scrambled
(rounded quiz option buttons sit inside boxy panels; the chat input is a boxy
thing when it is the single most conversational element on the screen). We fix
the scramble by assigning radius a *meaning* and holding to it.

## Pass 1 — the plan

### Color

No new palette. The existing token system (`globals.css`) is good and locked to
the brand board. We are only tightening *usage*:

- `--brand-ink` (#0e1b33) — structural base, the conversation "rail," primary
  buttons.
- `--brand-orange` (#ff8a00) — the single action accent. Reserved now for
  **the AI conversational layer**: the compose input's focus state, the
  "Continue" primary, the active step marker, the launch line. Orange = "the
  AI is waiting on you / this moves the session forward."
- `--brand-gold` (#ffc63d) — mastery/achievement only. Unchanged.
- `--brand-green` / `--brand-red` — correctness/at-risk only. Unchanged.
- `--muted` / `--border` — the quiet box vocabulary. Everything that is "read
  me" content sits in this register so the orange has somewhere to pop from.

The discipline (frontend skill: "spend your boldness in one place"): **one
orange primary action per view** — exactly one thing the student acts on next.
Progress fill and focus rings are semantic exceptions, not competing primaries:
they're orange because they're derived from the same "this is the live AI
session" meaning (a filling bar, a focused field), not because they're a second
call to action. The test isn't "count every orange pixel," it's "how many
different *things* is the student being asked to act on." If two different
actionable elements are both orange, one of them is wrong.

### Type

No new typefaces. Roles stay:
- `--font-display` (Space Grotesk) — surface titles, the lesson topic name.
- `--font-sans` (Inter) — all body, teaching content, chat.
- `--font-mono` (JetBrains Mono) — data ticks only: step counters `1/5`,
  mastery numbers, XP. Mono is a *data* signal, never used for prose.

One removal: the tracked-out uppercase eyebrow (`PageHeader`'s `eyebrow` prop,
`GUIDED LESSONS` etc.) is exactly the "template chrome eyebrow above every
heading" tell from the frontend skill, and the user explicitly called it out
as space-wasting. It goes from the *session* views entirely. It may stay on the
landing/index views where a page genuinely needs a title, but never above a
live session.

### Layout — the core move

The current model: every surface is a normal page that scrolls, with a
fixed-height `StudyStream` box living *inside* that scroll. Two scroll owners.
That is the bug.

The new model, taken straight from Gizmo's lesson-open behavior: **a live
session is a focused surface that owns the viewport.** One scroll owner. The
page chrome (title, eyebrow, topic picker) is *gone* while you are in session,
not merely pushed up.

```
  BEFORE (broken — two scroll owners)              AFTER (one scroll owner)
  ┌──────────────────────────────┐                ┌──────────────────────────────┐
  │ rail │ PageHeader (eyebrow)   │ ← page scroll  │ rail │ ◀ back   1/5 ▓▓░░  ▶  │ ← floating bar, fixed
  │      │ Work through it…       │                │      ├───────────────────────┤
  │      │ ┌───────────────────┐  │                │      │                       │
  │      │ │ panel header      │  │                │      │   teaching bubble      │
  │      │ │ ┌───────────────┐ │  │                │      │   teaching bubble      │ ← the ONLY
  │      │ │ │ StudyStream   │ │ ←── inner scroll  │      │   ▸ quiz takes over    │   scroll
  │      │ │ │  (h-[62vh])   │ │  │                │      │                       │
  │      │ │ └───────────────┘ │  │                │      ├───────────────────────┤
  │      │ └───────────────────┘  │                │      │ ⌨ Continue · Ask…  ◗  │ ← floating compose, fixed
  └──────────────────────────────┘                └──────────────────────────────┘
```

The session surface is three fixed zones and one scroll zone:
- **Top:** a floating session bar — back chevron (to picker/materials),
  progress, forward chevron (next step / next item). Persistent, does not
  scroll away. This is Gizmo's floating navbar.
- **Middle (scrolls):** the conversation stream. The single scroll owner. Fills
  all remaining height.
- **Bottom:** the compose dock — the anchored, rounded conversational input.
  Persistent. This is where "Continue" and "Ask a follow-up" live.

Alignment: the stream is left-aligned assistant bubbles with a max measure of
~72ch for teaching prose (frontend skill: <80ch line length), user bubbles
right-aligned. The compose dock and session bar span the full content column.

### The radius rule, concretely

| Element | Radius | Why |
|---|---|---|
| Session bar container | 0 (bottom border only) | chrome frame, instrument |
| Teaching bubble | `rounded-md` (6px) | content you read, but *in* the conversation — a hair of softening, not a pill |
| Quiz/answer card | 0 border, corner brackets | pure "read this precisely + answer" data surface |
| Answer option buttons | `rounded-md` | interactive, but disciplined — they are choices, not the AI |
| **Compose dock (both states)** | `rounded-full` | THE conversational affordance — one slot that toggles between the primary action and the follow-up input, same shape either way. **Checkpoint 2 correction:** originally spec'd as `rounded-2xl` for the input vs. `rounded-full` for a separate button; Checkpoint 2 review (screenshots against actual Gizmo) showed they're the same slot in two states and must match exactly, not two related-but-different radii. See `02`. |
| Back/forward chevrons + dock toggle | `rounded-full` icon buttons | Gizmo-style nav, and they are AI-session controls |

The one generous radius (`rounded-full`) appears **only** on the
compose dock and the small circular session controls around it — the elements
that *are* the conversation. Everything you read stays boxy. That is the whole
system: the eye learns in five seconds that "round = talk to Kala / move
forward," "square
= read this."

### Principles (what makes this Kala and not Gizmo)

1. **One line of elegance, everything else instrument.** Gizmo is soft
   everywhere; that reads as consumer. Kala is boxy everywhere *except* the
   live conversational controls. The contrast is the identity.
2. **Radius is signage, not taste.** Enforced by the table above and a lint
   note in the spec. No component picks a radius for "feel."
3. **The AI is the surface, not a panel on the surface.** No more "chat window
   as a component inside a page." The session *is* the stream.
4. **Modes converge on one grammar.** Lesson, practice, flashcard, diagnostic,
   tutor are all "a stream you move through with a compose dock at the bottom."
   They differ in *what the dock offers* (Continue vs. Next item vs. just Ask),
   not in their skeleton.

## Pass 2 — review against the brief (self-critique)

Working the frontend skill's "did I just produce the generic default?" check
against each decision:

- **Did I reach for the AI-generated cream/serif/terracotta cluster?** No —
  palette is the pre-existing institutional ink/orange, untouched. Good.
- **Did I reach for "SaaS card kit: one radius on everything"?** This was the
  *existing* problem. The fix explicitly assigns *different* radii by meaning,
  which is the opposite of the tell. Good — but it means the spec must be
  pedantic about the radius table or an implementer will "tidy" it back into
  uniformity. Added an explicit lint note (`06`).
- **Did I reach for the ALL-CAPS eyebrow?** It exists today; I am *removing* it
  from sessions. Good.
- **Is "floating bar + centered stream + anchored input" just the ChatGPT
  default?** It is the conventional chat layout, yes — and that convention is
  correct here because the brief *is* "make it feel like one conversation with
  the AI." The frontend skill says follow the brief's pinned direction exactly
  even when it is a known pattern. Where Kala departs from generic chat: the
  instrument-box stream content, corner-bracketed quiz cards, mono data ticks,
  and the radius-as-signage rule are all non-default. The *skeleton* is
  conventional on purpose; the *skin and the radius grammar* are Kala. This is
  the right place to be conventional (navigation) and bold (the box/line
  contrast).
- **One thing memorable?** The compose dock as the single soft, rounded element
  against an otherwise square instrument panel — that is the spent boldness. It
  literally rhymes with the launch line. Everything else stays quiet.

Revision made during pass 2: my first cut had the teaching bubble at
`rounded-lg` and the quiz card at `rounded-md`, which started to creep toward
"everything's a little rounded" — the exact tell. Pulled the quiz card back to
0-radius-with-brackets (it is a *data* surface) and held the bubble at a single
`rounded-md`, so there is a clear two-step ladder (content `rounded-md`,
conversational affordance `rounded-full`) instead of a mushy gradient of
radii. Documented in the radius table. **Checkpoint 2 sharpened this further:**
the conversational tier itself collapsed from two radii (`rounded-2xl` compose,
`rounded-full` button) to one (`rounded-full` for both), once it became clear
via the Gizmo comparison that they're the same slot, not two related
affordances — see `02`'s `ComposeDock` section.

## What this plan explicitly does NOT touch

- The instructor dashboard (`features/instructor`). The user confirmed it is
  done and correct on the box approach. Out of scope.
- The token values in `globals.css`. Usage tightens; values do not change.
- Any backend, migration, grading, tour-gating, or SRS logic. This is a
  frontend presentation redesign. Every server contract stays byte-identical,
  same as the Stage 1–4 discipline.
- The launch screen. It is the reference, not a target.
