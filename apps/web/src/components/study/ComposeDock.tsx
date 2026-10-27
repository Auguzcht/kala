import { useState, type ComponentType, type ReactNode, type Ref } from "react";
import {
  PromptInput,
  PromptInputBody,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from "@/components/ai-elements/prompt-input";
import { dockLayout } from "@/components/ai-elements/dock-layout";
import { MessageCircleIcon } from "@/components/ui/message-circle";
import { XIcon } from "@/components/ui/x";
import { useIconHover } from "@/hooks/use-icon-hover";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";

/** An animated lucide-animated icon: forwards a ref with the imperative
 * startAnimation/stopAnimation handle, so the dock's button — not just the
 * icon's own pixels — can drive the animation on hover. */
type AnimatedIconHandle = { startAnimation: () => void; stopAnimation: () => void };
type AnimatedIcon = ComponentType<{
  size?: number;
  className?: string;
  ref?: Ref<AnimatedIconHandle>;
}>;

export type ComposeDockPrimary = {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  /** Replace the action icon with the shared spinner while work is pending. */
  pending?: boolean;
  /** Animated icon component (not a rendered node) — the dock renders it and
   * owns its ref, so hovering the button animates the icon. */
  icon?: AnimatedIcon;
  /** Tour anchor for the action button. */
  id?: string;
};

// One rounded conversational slot that toggles between a forward action and a
// follow-up input. The two states are intentionally never visible together.
export function ComposeDock({
  primary,
  secondary,
  onAsk,
  askDisabled,
  askPending,
  placeholder = "Ask Kala a follow-up…",
  attachmentSlot,
  attachmentChips,
  inputId,
  tourId,
}: {
  primary?: ComposeDockPrimary | null;
  secondary?: ComposeDockPrimary;
  onAsk?: (text: string) => void;
  askDisabled?: boolean;
  askPending?: boolean;
  placeholder?: string;
  attachmentSlot?: ReactNode;
  attachmentChips?: ReactNode;
  /** Applied to PromptInput's form to preserve the Tutor tour contract. */
  inputId?: string;
  tourId?: string;
}) {
  const canToggle = Boolean(primary) && Boolean(onAsk);
  const [userMode, setUserMode] = useState<"action" | "compose">("action");
  const mode = !primary ? "compose" : !onAsk ? "action" : userMode;

  // Hovering the action BUTTON animates its icon (the icon's own hover only
  // covers a 16px target inside a full-width button — the rail does the same
  // forwarding). Declared unconditionally so hook order is stable across mode
  // flips, which unmount the button.
  const primaryIcon = useIconHover<AnimatedIconHandle>();
  const secondaryIcon = useIconHover<AnimatedIconHandle>();
  const toggleIcon = useIconHover<AnimatedIconHandle>();
  const ToggleIcon = userMode === "action" ? MessageCircleIcon : XIcon;
  const PrimaryIcon = primary?.icon;

  // One height for the whole dock. The action button, the compose input pill,
  // and the toggle are three shapes of the SAME control, so they are pinned to
  // the same height — previously the action button was py-3 while the input
  // grew to its textarea's min-height, so toggling visibly resized the slot.
  const DOCK_HEIGHT = "h-12";

  return (
    <div id={tourId} className={dockLayout.footer}>
      <div className={cn("flex w-full items-end gap-2", dockLayout.content)}>
        <div className="min-w-0 flex-1">
          {attachmentChips ? (
            <div className="mb-2 flex flex-wrap gap-2">{attachmentChips}</div>
          ) : null}

          {mode === "action" && primary ? (
            secondary ? (
              <div className="flex w-full gap-2">
                <button
                  type="button"
                  id={secondary.id ?? (tourId ? `${tourId}-secondary` : undefined)}
                  onClick={secondary.onClick}
                  disabled={secondary.disabled || secondary.pending}
                  aria-busy={secondary.pending || undefined}
                  onMouseEnter={secondaryIcon.play}
                  onMouseLeave={secondaryIcon.stop}
                  onFocus={secondaryIcon.play}
                  onBlur={secondaryIcon.stop}
                  className={cn(
                    "flex min-w-0 flex-1 items-center justify-center gap-2 rounded-full",
                    DOCK_HEIGHT,
                    "border border-border bg-card px-3 text-sm font-semibold text-foreground",
                    "transition-colors hover:bg-accent disabled:opacity-40",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  )}
                >
                  {secondary.pending ? <Spinner aria-hidden /> : secondary.icon ? <secondary.icon ref={secondaryIcon.ref} size={16} aria-hidden /> : null}
                  {secondary.label}
                </button>
                <button
                  type="button"
                  id={primary.id ?? (tourId ? `${tourId}-primary` : undefined)}
                  onClick={primary.onClick}
                  disabled={primary.disabled || primary.pending}
                  aria-busy={primary.pending || undefined}
                  onMouseEnter={primaryIcon.play}
                  onMouseLeave={primaryIcon.stop}
                  onFocus={primaryIcon.play}
                  onBlur={primaryIcon.stop}
                  className={cn(
                    "flex min-w-0 flex-1 items-center justify-center gap-2 rounded-full",
                    DOCK_HEIGHT,
                    "bg-brand-orange px-3 text-sm font-semibold text-brand-orange-foreground",
                    "shadow-sm transition-opacity hover:opacity-90 disabled:opacity-40",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  )}
                >
                  {primary.pending ? <Spinner aria-hidden /> : PrimaryIcon ? <PrimaryIcon ref={primaryIcon.ref} size={16} aria-hidden /> : null}
                  {primary.label}
                </button>
              </div>
            ) : (
              <button
                type="button"
                id={primary.id ?? (tourId ? `${tourId}-primary` : undefined)}
                onClick={primary.onClick}
                disabled={primary.disabled || primary.pending}
                aria-busy={primary.pending || undefined}
                onMouseEnter={primaryIcon.play}
                onMouseLeave={primaryIcon.stop}
                onFocus={primaryIcon.play}
                onBlur={primaryIcon.stop}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-full",
                  DOCK_HEIGHT,
                  "bg-brand-orange px-5 text-sm font-semibold text-brand-orange-foreground",
                  "shadow-sm transition-opacity hover:opacity-90 disabled:opacity-40",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                )}
              >
                {primary.pending ? <Spinner aria-hidden /> : PrimaryIcon ? (
                  <PrimaryIcon ref={primaryIcon.ref} size={16} aria-hidden />
                ) : null}
                {primary.label}
              </button>
            )
          ) : (
            <PromptInput
              id={inputId ?? (tourId ? `${tourId}-input` : undefined)}
              onSubmit={(message) => {
                if (message.text.trim()) onAsk?.(message.text);
              }}
              className={cn(dockLayout.form, dockLayout.pill)}
            >
              <div className={dockLayout.row}>
                <PromptInputBody>
                  <PromptInputTextarea
                    rows={1}
                    placeholder={placeholder}
                    className={dockLayout.textarea}
                  />
                </PromptInputBody>
                <PromptInputTools className="shrink-0 pl-1">
                  {attachmentSlot}
                </PromptInputTools>
                <PromptInputSubmit
                  className={dockLayout.control}
                  disabled={askDisabled || askPending}
                  aria-busy={askPending || undefined}
                />
              </div>
            </PromptInput>
          )}
        </div>

        {canToggle ? (
          <button
            type="button"
            id={tourId ? `${tourId}-toggle` : undefined}
            onClick={() => setUserMode((mode) => mode === "action" ? "compose" : "action")}
            onMouseEnter={toggleIcon.play}
            onMouseLeave={toggleIcon.stop}
            aria-label={userMode === "action" ? "Ask a follow-up" : "Cancel"}
            className={cn(
              // Same height as the slot it sits beside, toggled between modes.
              "flex",
              DOCK_HEIGHT,
              "aspect-square shrink-0 items-center justify-center rounded-full",
              "border border-border text-muted-foreground transition-colors",
              "hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            )}
          >
            <ToggleIcon ref={toggleIcon.ref} size={18} />
          </button>
        ) : null}
      </div>
    </div>
  );
}
