# Token Usage Reference

No new tokens. This is the *usage discipline* for the redesign, so an
implementer reaches for the right existing token instead of a hardcoded hex or
an arbitrary radius. All values already live in `apps/web/src/styles/globals.css`.

## Color — one meaning per token

| Token | Means | Used in v2 on |
|---|---|---|
| `--brand-ink` / `bg-primary` | structural base | primary buttons' dark variant, the launch line's context |
| `--brand-orange` / `bg-brand-orange` | **action / move-forward with the AI** | ComposeDock primary (Continue/Next/Submit), compose focus ring, active step marker, session progress fill. **One orange primary action per view** — progress fill and focus rings are semantic exceptions (derived from the same "live AI session" meaning), not competing primaries. Two different *actionable* elements both orange is the bug to catch. |
| `--brand-gold` | mastery / achievement | mastery bands, XP — never as a CTA |
| `--brand-green` | correct / on-track | AnswerableCard correct state, "step complete ✓" |
| `--brand-red` / `--destructive` | incorrect / at-risk | AnswerableCard wrong state, misconception rule |
| `--muted` / `--border` | the quiet box vocabulary | teaching bubble bg, panel borders, everything "read me" |
| `--ring` (orange) | focus | every focusable control's `focus-visible:ring-ring` |

Rule: if two things on one screen are orange, one is miscolored. Orange is the
single "here's your next move with Kala" signal.

## Radius — signage, not taste

| Class | Meaning | Where |
|---|---|---|
| (none) / `rounded-none` | instrument frame / data surface | SessionBar, quiz/answer card containers |
| `rounded-sm` / `rounded-md` | content you read (slight softening) | teaching bubble, answer option buttons, chips |
| `rounded-full` | **the conversational slot + move-forward / nav controls** | `ComposeDock` in both its action and compose states (they're the same slot — see `02`), the dock's toggle button, `SessionBar` chevrons |

**Checkpoint 2 correction:** the conversational tier used to be split across
`rounded-2xl` (compose input) and `rounded-full` (the primary button), on the
theory that they were two different affordances. Comparing the built Lessons
dock against Gizmo showed that's wrong — button and input are the *same slot*
toggling states, so they have to be pixel-identical in shape. `rounded-2xl` is
retired; the conversational register is `rounded-full` only, everywhere.

This one generous radius is the spent boldness. It appears only on the
elements that *are* the conversation. See `06`'s lint (updated).

## Type — role, not decoration

| Token | Role | Never |
|---|---|---|
| `--font-display` (Space Grotesk) | surface/lesson titles in SessionBar | not for body prose |
| `--font-sans` (Inter) | all teaching + chat + UI text | — |
| `--font-mono` (JetBrains Mono) | data ticks: `1/5`, mastery %, XP | not for prose, not for labels-as-style |

Removed treatment: the tracked-out uppercase eyebrow (`PageHeader eyebrow`) is
gone from all in-session views. It is the generated-page tell and the user
called it out. Keep sentence-case titles.

## Corner brackets (`CornerBrackets`)

The `[ ]` motif is reserved, per the brand brief, for **data panels the student
must read precisely**. In v2 that means: the quiz/answer card (yes — you read it
precisely then answer). NOT the tutor conversation (removed there — it is a
chat, not a data readout), NOT the compose dock. Using brackets everywhere
dilutes them; hold them to the quiz card.

## Motion

- One-shot, state-encoding only (frontend skill). The check/x draw once on a
  graded result (already in `AnswerableCard` — keep). The takeover pop is a
  mount transition. No looping, no per-card hover fades, no section-entrance
  slides.
- `useReducedMotion` respected on the takeover pop and any dock transition.
