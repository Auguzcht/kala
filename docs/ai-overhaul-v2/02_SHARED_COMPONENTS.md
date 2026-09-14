# Shared Session Components — Build Spec

Three new files, built first, before any mode migrates. Each compiles and can be
smoke-tested on its own. All class names use existing tokens (`globals.css`) —
no new tokens, no hardcoded hex.

Radius rule reminder (from `00_DESIGN_PLAN.md`, **updated after Checkpoint 2** —
`rounded-2xl` is retired, the conversational register is `rounded-full` only):
- content you read → `rounded-md` max
- data/answer surfaces → `0` + corner brackets
- **conversational affordances → `rounded-full`, and ONLY here**

---

## 1. `components/study/StudySurface.tsx` (NEW)

The three-zone takeover. Owns the single scroll region.

```tsx
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

// The live-session surface. Claims the course content viewport and
// establishes exactly ONE scroll owner (the middle zone). Replaces the old
// model where a session was a normal scrolling page with a second scroll
// (StudyStream's h-[62vh]) nested inside it — the source of the double
// scrollbar and premature content cut-off.
//
// Three zones: a fixed top bar, a scrolling stream, a fixed compose dock.
// The parent (<main> for session routes, see CourseShell) gives this a real
// fixed height; this fills it. `bar` and `dock` are shrink-0; `children`
// (the stream) is the only thing that scrolls.
export function StudySurface({
  bar,
  dock,
  children,
  className,
}: {
  bar?: ReactNode;
  dock?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex h-full min-h-0 flex-col", className)}>
      {bar ? <div className="shrink-0">{bar}</div> : null}
      {/* The ONLY scroll owner. min-h-0 is load-bearing: without it this
          flex child won't shrink below content height and the page scrolls
          instead — the exact bug this redesign fixes. StudyStream sets
          overflow; this just sizes the slot. */}
      <div className="min-h-0 flex-1">{children}</div>
      {dock ? <div className="shrink-0">{dock}</div> : null}
    </div>
  );
}
```

Notes for the implementer:
- Do not add padding to the outer div; the zones own their own spacing.
- `h-full` assumes the parent has a real height. That is `CourseShell`'s job
  (spec `06`, approach A). If you test `StudySurface` in isolation, wrap it in a
  `h-[100dvh]` div or you will see it collapse — that is expected, not a bug.

---

## 2. `components/study/SessionBar.tsx` (NEW — or refactor `StudySessionShell`)

The floating top nav. Gizmo's persistent bar: back on the left, progress in the
middle, a forward affordance on the right. This is chrome — **radius 0**, it is
an instrument frame, distinguished by a bottom hairline only.

```tsx
import type { ReactNode } from "react";
import { ChevronLeftIcon } from "@/components/ui/chevron-left";
import { ChevronRightIcon } from "@/components/ui/chevron-right"; // add if absent
import { cn } from "@/lib/utils";

// Persistent session chrome (was StudySessionShell's top row, now the fixed
// top zone of StudySurface). Back affordance (to the picker / deck
// materials), a slim caller-defined progress indicator, and an optional
// forward affordance (next step / next item) mirroring Gizmo's left/right
// chevrons. Feature-agnostic: it renders chrome, never knows what mode it's
// wrapping. GamificationSummary still lives once in CourseShell's topbar, not
// here (see the original StudySessionShell comment — duplicate mount fired
// duplicate badge toasts).
export function SessionBar({
  title,
  progress,
  onBack,
  backLabel = "Back",
  onForward,
  forwardLabel,
  forwardDisabled,
  right,
}: {
  title?: string;
  progress?: {
    current: number;
    total: number;
    label?: string;
    /** Checkpoint 2 addition: the current step's Bloom ladder position
     * (e.g. "remember", "apply"). Lessons-only — the per-step value from
     * `lessonStepSchema.bloomLevel`, NOT the skill-level tag already shown
     * on the topic picker. Rendered inline with the counter, mono, same
     * register as `1/5 step`. Omit for modes without a per-item ladder
     * (Practice, Flashcards, Diagnostic). */
    bloomLevel?: string | null;
  };
  onBack?: () => void;
  backLabel?: string;
  onForward?: () => void;
  forwardLabel?: string;
  forwardDisabled?: boolean;
  right?: ReactNode;
}) {
  const pct =
    progress && progress.total > 0
      ? Math.round((progress.current / progress.total) * 100)
      : 0;

  return (
    <div className="flex items-center gap-3 border-b border-border/60 bg-background/80 px-4 py-2.5 backdrop-blur">
      {/* Back — rounded-full icon button: this is an AI-session nav control,
          it earns the conversational radius (radius rule). */}
      {onBack ? (
        <button
          type="button"
          onClick={onBack}
          aria-label={backLabel}
          className="inline-flex size-8 shrink-0 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronLeftIcon size={16} />
        </button>
      ) : null}

      {title ? (
        <span className="truncate font-display text-sm font-semibold text-foreground">
          {title}
        </span>
      ) : null}

      {progress ? (
        <div className="flex min-w-32 flex-1 items-center gap-3">
          <div
            className="h-1 flex-1 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={progress.total}
            aria-valuenow={progress.current}
          >
            <div
              className="h-full rounded-full bg-brand-orange transition-all duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
            {progress.current}
            {progress.total > 0 ? `/${progress.total}` : ""}
            {progress.label ? ` ${progress.label}` : ""}
            {progress.bloomLevel ? ` · ${progress.bloomLevel}` : ""}
          </span>
        </div>
      ) : (
        <div className="flex-1" />
      )}

      {right}

      {/* Forward — mirror of back. Present only when the mode has a
          bar-level forward move (lessons/flashcards). Practice advances via
          the dock's "Next item", so it may omit this. */}
      {onForward ? (
        <button
          type="button"
          onClick={onForward}
          disabled={forwardDisabled}
          aria-label={forwardLabel ?? "Next"}
          className="inline-flex size-8 shrink-0 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors hover:bg-accent disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronRightIcon size={16} />
        </button>
      ) : null}
    </div>
  );
}
```

Notes:
- If `ChevronRightIcon` doesn't exist in `components/ui`, add it mirroring
  `chevron-left` (same animated-lucide pattern the rail uses).
- The bar carries the lesson **title** now (moved off the old in-panel
  `border-b px-5 py-3` header inside `LessonChat`). One title, in the chrome,
  not a second header inside the content box.
- Keep the `hasChrome`-style guard from `StudySessionShell` if you want, but in
  practice every session has at least a back + progress, so the bar always
  renders.

---


## 3. `components/study/ComposeDock.tsx` (NEW)

> **Corrected after Checkpoint 2 review.** The first version of this component
> put a `PrimaryAdvance` button and a compose input side by side, permanently
> both visible. Checkpoint 2 (screenshots of the built Lessons mode against the
> actual Gizmo reference) showed that's wrong on two counts: Gizmo shows only
> ONE control by default (a full-width action button, "Ok, I understand"), and
> a small circular toggle swaps that same slot into a text input — button and
> input are literally the same box in two states, which is why they visually
> match. The side-by-side layout is what made the built dock read as "two
> different rounded things bolted together" instead of one coherent control.
> This section replaces the original design. If Step 1/2 were already built
> against the old version, see `08_CHECKPOINT2_FIXES.md` for the exact delta.

The unified conversational dock — **one slot that toggles between two states**,
plus a small circular toggle button beside it. This is the one component that
makes the four features feel like one, and the toggle mechanic is the whole
reason it reads as a single coherent object instead of a row of controls.

```
 action mode (default)                    compose mode (after tapping toggle)
┌────────────────────────────┐  ╭───╮    ┌────────────────────────────┐  ╭───╮
│      ▸  Continue            │  │ ⋯ │    │  Ask Kala a follow-up…     │  │ ✕ │
└────────────────────────────┘  ╰───╯    └────────────────────────────┘  ╰───╯
   rounded-full, bg-brand-orange  rounded-full     rounded-full, bg-card    rounded-full
   (or bg-primary — see below)    icon toggle        border-input              icon toggle
```

Both states occupy the exact same `flex-1` slot at the exact same `rounded-full`
radius — that identity is the point. The small circular button to the right is
the only thing that's a second element, and it stays `rounded-full` too (same
family as `SessionBar`'s chevrons).

```tsx
import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { MessageCircleIcon } from "@/components/ui/message-circle"; // add if absent
import { XIcon } from "@/components/ui/x";
import {
  PromptInput,
  PromptInputBody,
  PromptInputTextarea,
  PromptInputFooter,
  PromptInputTools,
  PromptInputSubmit,
} from "@/components/ai-elements/prompt-input";

export type ComposeDockPrimary = {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  icon?: ReactNode;
  /** Tour anchor, e.g. "tour-lesson-continue". */
  id?: string;
};

// The anchored dock at the bottom of every session surface. ONE slot that
// toggles between two states — "action" (the mode's forward move: Continue /
// Next item / Next card / Submit) and "compose" (free-text "ask a follow-up").
// They are never both visible at once; a small circular icon button (chat
// bubble ↔ ✕) switches between them. This mirrors Gizmo exactly: the default
// is the full-width action button, tapping the small circle swaps it for the
// input, tapping the ✕ (same circle) swaps back.
//
// Degenerate cases, both valid and both drop the toggle chrome entirely
// (nothing to toggle between):
//   - `primary` omitted, `onAsk` present → compose-only, no toggle button.
//     This is Tutor's shape: it's always composing, there's no "advance".
//   - `primary` present, `onAsk` omitted → action-only, no toggle button.
//     This is Diagnostic's shape: no mid-baseline ask, ever.
// Both present → the toggle appears and the slot starts in "action" mode.
export function ComposeDock({
  primary,
  onAsk,
  askDisabled,
  askPending,
  placeholder = "Ask Kala a follow-up…",
  attachmentSlot,
  attachmentChips,
  inputId,
}: {
  /** The mode's forward move. Omit for Tutor (compose-only, no toggle). */
  primary?: ComposeDockPrimary | null;
  /** Called when the student sends a free-text follow-up. Omit for
   * Diagnostic (action-only, no toggle — asking mid-baseline undercuts it). */
  onAsk?: (text: string) => void;
  askDisabled?: boolean;
  askPending?: boolean;
  placeholder?: string;
  attachmentSlot?: ReactNode;
  attachmentChips?: ReactNode;
  /** Tour anchor for the textarea's FORM ancestor — passed straight to
   * PromptInput's own `id`. Do not move this onto the <textarea> itself;
   * TourRunner calls requestSubmit() on this id, which only exists on
   * <form>. See 05_TUTOR_AND_HIERARCHY.md. */
  inputId?: string;
}) {
  const canToggle = Boolean(primary) && Boolean(onAsk);
  const [userMode, setUserMode] = useState<"action" | "compose">("action");
  // No toggle available → the mode is forced by whichever prop exists.
  const mode = !primary ? "compose" : !onAsk ? "action" : userMode;

  return (
    <div className="border-t border-border/60 bg-background/80 px-4 py-3 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center gap-2">
        {attachmentChips ? (
          <div className="flex w-full flex-wrap gap-2 sm:hidden">{attachmentChips}</div>
        ) : null}

        <div className="min-w-0 flex-1">
          {attachmentChips ? (
            <div className="mb-2 hidden flex-wrap gap-2 sm:flex">{attachmentChips}</div>
          ) : null}

          {mode === "action" && primary ? (
            <button
              type="button"
              id={primary.id}
              onClick={primary.onClick}
              disabled={primary.disabled}
              className={cn(
                "flex w-full items-center justify-center gap-2 rounded-full",
                "bg-brand-orange px-5 py-3 text-sm font-semibold text-brand-orange-foreground",
                "shadow-sm transition-opacity hover:opacity-90 disabled:opacity-40",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              )}
            >
              {primary.icon}
              {primary.label}
            </button>
          ) : (
            <PromptInput
              id={inputId}
              onSubmit={(m) => {
                if (m.text?.trim()) onAsk?.(m.text);
              }}
              // Same rounded-full slot the button occupies — this is the
              // "button matches the roundedness of the input" fix. Target
              // the internal InputGroup (see the note in the old section 3
              // below, or 08_CHECKPOINT2_FIXES.md): PromptInput's own
              // className lands on its <form>, not the bordered element.
              className={cn(
                "[&_[data-slot=input-group]]:rounded-full",
                "[&_[data-slot=input-group]]:border-input",
                "[&_[data-slot=input-group]]:shadow-sm",
                "[&_[data-slot=input-group]]:px-1.5"
              )}
            >
              <PromptInputBody>
                <PromptInputTextarea placeholder={placeholder} className="py-2.5" />
              </PromptInputBody>
              <PromptInputFooter className="pr-1">
                <PromptInputTools>{attachmentSlot}</PromptInputTools>
                <PromptInputSubmit
                  disabled={askDisabled}
                  status={askPending ? "submitted" : undefined}
                />
              </PromptInputFooter>
            </PromptInput>
          )}
        </div>

        {canToggle ? (
          <button
            type="button"
            onClick={() => setUserMode((m) => (m === "action" ? "compose" : "action"))}
            aria-label={userMode === "action" ? "Ask a follow-up" : "Cancel"}
            className={cn(
              "flex size-11 shrink-0 items-center justify-center rounded-full",
              "border border-border text-muted-foreground transition-colors",
              "hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            )}
          >
            {userMode === "action" ? (
              <MessageCircleIcon size={18} />
            ) : (
              <XIcon size={18} />
            )}
          </button>
        ) : null}
      </div>
    </div>
  );
}
```

### Behavior notes

- **Default is action mode.** A session opens showing the primary move, not an
  empty compose box — matches "its default is actually Ok I understand," not a
  waiting-for-input state.
- **Sending a follow-up does not auto-revert to action mode.** Let the student
  ask a second question without re-tapping the toggle each time; they close it
  themselves via the ✕ when they're done, or by taking the primary action once
  they toggle back. (If in practice this reads as the dock "getting stuck open"
  during testing, the alternative is auto-revert once an answer finishes
  streaming — flag it as a judgment call during Lessons review, not a fixed
  rule either way.)
- **`primary` is a config object now, not a `ReactNode`.** This is the
  breaking change from the original spec: `ComposeDock` has to own rendering
  of both states itself to guarantee they're pixel-identical in shape, so it
  needs structured data (`label`, `onClick`, `disabled`, `icon`, `id`), not a
  pre-rendered element that might carry its own inconsistent styling. Every
  mode spec (`03`, `04`, `05`) is updated for this — grep `primaryAction=` in
  those files for any stale reference if you're reading an older copy.
- **`PrimaryAdvance` as a standalone component is retired.** It existed only
  to give the old side-by-side layout a `rounded-full` button; `ComposeDock`
  now renders that button itself in `action` mode. If some other part of the UI
  independently needs a lone advance button outside a dock context, it's fine
  to keep a `PrimaryAdvance` helper around for that — just don't use it inside
  `ComposeDock` anymore.
- **Add `MessageCircleIcon` if it doesn't exist** in `components/ui`, mirroring
  the existing animated-lucide pattern (`chevron-left.tsx` etc.).

### Why this collapses the radius rule

The original design had two "conversational" radii — `rounded-2xl` for compose,
`rounded-full` for the primary button — reasoning they were different affordances.
Checkpoint 2 shows they're not different affordances, they're the *same* slot in
two states, so they must be the *same* radius. **`rounded-2xl` is retired from
the palette.** The conversational register is now just `rounded-full`,
consistently: the dock slot in both modes, the toggle button, `SessionBar`'s
chevrons. See `07_TOKEN_USAGE_REFERENCE.md` (updated) for the corrected table.
