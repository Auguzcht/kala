# Shared Session Components — Build Spec

Three new files, built first, before any mode migrates. Each compiles and can be
smoke-tested on its own. All class names use existing tokens (`globals.css`) —
no new tokens, no hardcoded hex.

Radius rule reminder (from `00_DESIGN_PLAN.md`), enforced here:
- content you read → `rounded-md` max
- data/answer surfaces → `0` + corner brackets
- **conversational affordances → `rounded-2xl` / `rounded-full`, and ONLY here**

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
  progress?: { current: number; total: number; label?: string };
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

The unified rounded conversational dock. **This is the one component that makes
the four features feel like one.** It is the only element (with the Continue
primary) that gets the generous `rounded-2xl` — the launch-line's elegance,
applied to the AI's input.

```tsx
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import {
  PromptInput,
  PromptInputBody,
  PromptInputTextarea,
  PromptInputFooter,
  PromptInputTools,
  PromptInputSubmit,
} from "@/components/ai-elements/prompt-input";

// The anchored conversational dock at the bottom of every session surface.
// Two coexisting halves:
//   • primaryAction — the mode's forward move (Continue / Next item / Next
//     card / Submit). Orange, rounded-full. The default thing to do.
//   • compose — "Ask Kala a follow-up." A PromptInput. Sending injects a
//     grounded Q&A turn into the stream; it does NOT advance the session.
//     After an answer, focus returns to the primary ("point back to Continue
//     when ready").
//
// Tutor is the degenerate case: no primaryAction, compose only — which is
// exactly what Tutor already is, now wearing the shared dock so it reads as
// the same product as the lesson/quiz surfaces.
//
// Radius rule: this container is the ONE place rounded-2xl is allowed. It is
// the conversational affordance. Everything you read stays boxy; this is what
// you talk through. Do not "tidy" this to match the boxier panels — the
// contrast is the design.
export function ComposeDock({
  primaryAction,
  onAsk,
  askDisabled,
  askPending,
  placeholder = "Ask Kala a follow-up…",
  attachmentSlot,
  attachmentChips,
  inputId,
}: {
  /** The mode's forward move. Omit for Tutor (compose-only). */
  primaryAction?: ReactNode;
  /** Called when the student sends a free-text follow-up. */
  onAsk?: (text: string) => void;
  askDisabled?: boolean;
  askPending?: boolean;
  placeholder?: string;
  /** Optional attach control (Tutor's file input trigger) rendered in tools. */
  attachmentSlot?: ReactNode;
  /** Optional row of attachment chips rendered above the input (Tutor). */
  attachmentChips?: ReactNode;
  /** Tour anchor id. CORRECTED WORDING: this id goes on the PromptInput
   * FORM (passed through to PromptInput's `id` prop below), not on the
   * textarea. TourRunner.tsx does `document.querySelector("#tour-tutor-input
   * textarea")` to find the field (a descendant lookup) but then does
   * `document.querySelector("#tour-tutor-input")?.requestSubmit()` — and
   * requestSubmit() only exists on a <form>. If this id is moved onto the
   * <textarea> instead, requestSubmit() silently fails to submit and the
   * tour stalls with no error, the same failure class the original
   * HTMLInputElement/HTMLTextAreaElement native-setter bug was. Keep it on
   * PromptInput ("#tour-tutor-input" on the form the Tutor surface). */
  inputId?: string;
}) {
  return (
    <div className="border-t border-border/60 bg-background/80 px-4 py-3 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-end gap-3">
        {primaryAction ? <div className="shrink-0 pb-1">{primaryAction}</div> : null}

        {onAsk ? (
          <div className="min-w-0 flex-1">
            {attachmentChips ? (
              <div className="mb-2 flex flex-wrap gap-2">{attachmentChips}</div>
            ) : null}
            {/* rounded-2xl lives HERE — but NOT via className on PromptInput.
                CORRECTED: PromptInput's className lands on the <form> it
                renders (`<form className={cn("w-full", className)}>`), while
                the actual visible border/radius comes from the FontGroup it
                wraps internally — `<InputGroup className="overflow-hidden">`
                — which is hardcoded `rounded-md border border-input` in
                components/ui/input-group.tsx (data-slot="input-group"). A
                bare className="rounded-2xl" on PromptInput compiles fine and
                visibly does nothing; the dock stays boxy. Use a descendant
                override targeting the slot: */}
            <PromptInput
              id={inputId}
              onSubmit={(m) => {
                if (m.text?.trim()) onAsk(m.text);
              }}
              className="[&_[data-slot=input-group]]:rounded-2xl [&_[data-slot=input-group]]:shadow-sm"
            >
              <PromptInputBody>
                <PromptInputTextarea placeholder={placeholder} />
              </PromptInputBody>
              <PromptInputFooter>
                <PromptInputTools>{attachmentSlot}</PromptInputTools>
                <PromptInputSubmit
                  disabled={askDisabled}
                  status={askPending ? "submitted" : undefined}
                />
              </PromptInputFooter>
            </PromptInput>
            {/* Alternative, if you'd rather not hand-write descendant
                selectors: add a dedicated `inputGroupClassName` prop to
                PromptInput itself (threaded onto its internal `<InputGroup>`)
                and use that instead. Either is acceptable; the descendant
                selector above needs no changes to the vendored ai-elements
                file, so it's the lower-risk default. */}
          </div>
        ) : null}
      </div>
    </div>
  );
}
```

### The primary-action helper (Continue / Next item / …)

To keep the orange `rounded-full` primary consistent everywhere, add a small
shared button rather than re-styling per mode. Put it in the same file or in
`components/study/PrimaryAdvance.tsx`:

```tsx
import { cn } from "@/lib/utils";

// The single orange forward action, rounded-full (radius rule: the "move
// forward with the AI" control). Used as ComposeDock's primaryAction across
// modes: "Continue", "Next item", "Next card", "Submit", "Finish".
export function PrimaryAdvance({
  label,
  onClick,
  disabled,
  icon,
  id,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  icon?: React.ReactNode;
  id?: string;
}) {
  return (
    <button
      type="button"
      id={id}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center gap-2 rounded-full bg-brand-orange px-5 py-2.5",
        "text-sm font-semibold text-brand-orange-foreground",
        "transition-opacity hover:opacity-90 disabled:opacity-40",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      )}
    >
      {icon}
      {label}
    </button>
  );
}
```

Notes:
- **Do not use `<Button variant="orange">` for the primary.** That variant is
  hardcoded `rounded-md` in `components/ui/button.tsx`. The radius rule needs the
  primary advance at `rounded-full`, so `PrimaryAdvance` is its own component. If
  you'd rather add a `variant="advance"` to `button.tsx` with `rounded-full`,
  that's fine too — just don't ship the primary at `rounded-md`.
- `PromptInput` already accepts a `className` and forwards it to the root
  (verified in the vendored `ai-elements`). The `rounded-2xl` must land on the
  outer bordered element, not the textarea.
- The dock's `max-w-3xl` keeps the compose measure readable and centered under
  the stream; the stream content uses the same measure so they align.
- Accessibility: the primary action and the textarea are both keyboard
  reachable; `PromptInputSubmit` is the Enter target inside compose, the
  primary is a separate Tab stop. Do not trap focus.
