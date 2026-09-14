# Tutor Rebuild + the Deck / Materials Hierarchy Question

Two things in this doc: the (small) Tutor migration, and a design decision the
user raised about Gizmo's deck → subdeck → materials organizing hierarchy and
whether Kala should adopt it.

---

## Tutor — `features/tutor/components/TutorChat.tsx`

Tutor is already 90% of the target: it is a persisted stream on `StudyStream`
with a `PromptInput` at the bottom. The migration makes it wear the shared
`StudySurface` + `ComposeDock` so it reads as the same product as the other
surfaces (right now its input is a bespoke boxy `border-t p-3` block; it should
be *the same rounded dock* the lesson uses — that visual echo is the whole
"unified" point).

### Changes
- Wrap in `StudySurface`.
- The conversation switcher (`Select` + New chat) moves into `SessionBar`'s
  `right` slot (it is session chrome). Its title = active conversation title or
  "Ask Kala".
- The entire bottom block (attachment chips + hidden file input + `PromptInput`)
  becomes `ComposeDock` in **compose-only mode** (`primaryAction` omitted):
  - `onAsk` → `askQuestion(text)` (existing).
  - `attachmentSlot` → the existing attach `PromptInputButton` that triggers the
    hidden file input. **Ownership stays with `TutorChat`**: the hidden
    `<input type="file" ref={fileInputRef}>` element and its `onChange`
    handler (`handleFileSelect`) are NOT moved into `ComposeDock`.
    `ComposeDock`'s `attachmentSlot` prop only receives the trigger *button*
    (`onClick={() => fileInputRef.current?.click()}`) — the ref and the actual
    `<input>` stay declared in `TutorChat`, same as today. `ComposeDock` is a
    layout/visual shell here, not a new owner of upload state.
  - `attachmentChips` → the existing `AttachmentChip` row (data still comes
    from `TutorChat`'s `active.data.attachments`, just rendered inside the
    dock's slot now instead of the old `border-t p-3` block).
  - `inputId="tour-tutor-input"` → **critical, and the id belongs on the
    PromptInput form, not the textarea.** `TourRunner.tsx` does
    `document.querySelector("#tour-tutor-input textarea")` to find the field
    (a descendant selector — it expects the id on an ancestor) and then
    `document.querySelector("#tour-tutor-input")?.requestSubmit()` to send it —
    `requestSubmit()` only exists on `<form>` elements. `ComposeDock` passes
    `inputId` straight to `<PromptInput id={inputId}>`, which is correct
    because `PromptInput` renders that id onto its own `<form>`. Do not move
    this id onto the `<textarea>` — that breaks `requestSubmit()` silently
    (no thrown error, the tour just stalls), the same failure class as the
    original `HTMLInputElement`/`HTMLTextAreaElement` native-setter bug from
    Stage 2.
- The follow-up chips (`FollowUpChips`, the eli5/detail styles) stay in the
  stream after the last answer, unchanged.

### Remove
- The bespoke `border bg-card` wrapper + its `border-b px-5 py-3` title header.
  `SessionBar` owns the title. `CornerBrackets` on the tutor panel can go too —
  tutor is a conversation, not a data panel to read precisely, so the bracket
  motif (reserved for "read this precisely" surfaces per the brief) does not
  belong here. Removing it is on-brief.

### Route `routes/course/tutor.tsx`
Drop the `PageHeader` (eyebrow "Tutor" / "Ask Kala" / description). Tutor is a
session; the title lives in the bar. The route becomes basically
`<TutorChat courseId={courseId} />` full-height.

### Anchors
`tour-tutor-input`, `tour-tutor-thinking`, `tour-tutor-response` — all
preserved. `tour-tutor-input` on the dock's `PromptInput` **form** (see above —
not the textarea), the other two on their stream blocks as today.

### Why this matters even though Tutor "works"
The user's thesis is coherence: the AI is the product, and every surface should
feel like the same conversation. If Tutor keeps its own boxy input while lessons
get the rounded dock, the two read as different apps. Same dock everywhere = one
app. This is the cheapest, highest-signal migration for the "unified" goal.

---

## The deck / subdeck / materials hierarchy

The user pointed at Gizmo's organizing model:

> They use decks as their main organizing folders; within decks there are
> subdecks; the **Materials** tab neatly organizes the subdecks, its lessons
> (step by step), etc. Clicking a lesson gives the full modal…

And contrasted it with Kala, where Lessons / Practice / Flashcards / Diagnostic
are **separate left-rail destinations** even though they operate on the same
underlying skills — which is a big part of why they feel like unrelated
features.

This is the deeper structural version of the same complaint. Worth being
explicit about the options, because it is a bigger decision than the visual
redesign and should be made deliberately, not by accident.

### Kala's actual hierarchy today

Kala's source of truth is the LMS. The real spine is:
`course → module → skill → (twin mastery per skill)`.
Lessons, Practice, Flashcards, Diagnostic are **modes of engaging a skill**, not
separate content collections. `TopicLanding` already groups skills by module —
that grouping *is* Kala's "materials" view, it just isn't framed as one.

So Kala already has Gizmo's structure latent in it. Gizmo's "deck" ≈ Kala's
"module"; Gizmo's "study a deck" fanning into lesson/quiz/flashcard modes ≈
Kala's skill-with-modes. The difference is purely presentational: Gizmo makes
the *deck* the hub and the modes are things you launch *from inside it*; Kala
makes the *mode* the hub (left-rail tab) and the skill is chosen inside it.

### Two ways to close the gap

**Option 1 — keep mode-first rails, unify the session grammar (this redesign).**
Do nothing structural. The `StudySurface`/dock work already makes the modes feel
like one product because they share the conversation grammar. Cheapest, ships
now, no routing change, no backend change. The picker demotion (`04`) softens
the "four separate features" feel a lot on its own.

**Option 2 — a skill/module hub (the Gizmo "deck materials" move).**
Introduce a `course/module/:id` or `course/skill/:id` hub view that is Kala's
"Materials": it shows a skill (or module) and offers **Lesson · Practice ·
Flashcards** as launch actions *from that hub*, opening the same `StudySurface`
takeover. The left rail could then collapse from four mode-tabs to essentially
"Workspace / Diagnostic / Tutor," with Lesson/Practice/Flashcards reached
*through* a skill rather than as top-level tabs. This is genuinely closer to
Gizmo and resolves the "separate features that aren't" problem at the root —
but it is a routing + IA change, not just a restyle, and should be its own
staged effort *after* the visual redesign lands.

### Recommendation

**Do Option 1 now** (it is this whole spec) and **write Option 2 down as the
next epic**, don't fold it into this pass. Reasons:
- The visual/scroll/takeover fixes are self-contained, low-risk, and deliver
  most of the "feels like one product" win. Ship them first, get the click-
  through, see how much of the "separate features" feeling remains.
- Option 2 touches routing, the side rail, the tour (rail anchors!), and
  probably the workspace/index. That is a real IA project with its own review,
  not a rider on a styling pass. Stacking it here would make this
  undeliverable in one clean reviewable chunk — the same "don't stack unreviewed
  stages" discipline from the original overhaul.
- Nothing in Option 1 blocks Option 2; the `StudySurface` takeover is exactly
  what a skill-hub would launch into. Option 1 is a prerequisite, not a detour.

If the user wants Option 2, the follow-up epic is roughly: (a) a `SkillHub`
route that reuses `TopicLanding`'s per-skill card as a detail view, (b) rail
collapse from mode-tabs to skill-first nav, (c) mode launches as
params/overlays off the hub, (d) tour rewrite for the new nav. Flag it, scope
it separately.

---

## Summary of the "separate features that aren't" fix in THIS pass

Without any routing change, three things in this redesign already attack the
perception:

1. **Shared session grammar** — every mode is the same StudySurface + dock, so
   they read as one product even while remaining separate routes.
2. **Picker demotion** — the topic picker stops being a full-page feature and
   becomes a lightweight gate, so Lessons and Practice stop presenting as twins.
3. **The dock as connective tissue** — the same rounded conversational input
   under a lesson, a practice card, and the tutor is the single strongest signal
   that "this is all one AI you're talking to," which is Gizmo's whole trick.

Option 2 would finish the job at the IA level; Option 1 makes it *feel* solved
now.
