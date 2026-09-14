import { useState, type ComponentType, type ReactNode, type Ref } from "react";
import {
  PromptInput,
  PromptInputBody,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from "@/components/ai-elements/prompt-input";
import { MessageCircleIcon } from "@/components/ui/message-circle";
import { XIcon } from "@/components/ui/x";
import { useIconHover } from "@/hooks/use-icon-hover";
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
  onAsk,
  askDisabled,
  askPending,
  placeholder = "Ask Kala a follow-up…",
  attachmentSlot,
  attachmentChips,
  inputId,
}: {
  primary?: ComposeDockPrimary | null;
  onAsk?: (text: string) => void;
  askDisabled?: boolean;
  askPending?: boolean;
  placeholder?: string;
  attachmentSlot?: ReactNode;
  attachmentChips?: ReactNode;
  /** Applied to PromptInput's form to preserve the Tutor tour contract. */
  inputId?: string;
}) {
  const canToggle = Boolean(primary) && Boolean(onAsk);
  const [userMode, setUserMode] = useState<"action" | "compose">("action");
  const mode = !primary ? "compose" : !onAsk ? "action" : userMode;

  // Hovering the action BUTTON animates its icon (the icon's own hover only
  // covers a 16px target inside a full-width button — the rail does the same
  // forwarding). Declared unconditionally so hook order is stable across mode
  // flips, which unmount the button.
  const primaryIcon = useIconHover<AnimatedIconHandle>();
  const toggleIcon = useIconHover<AnimatedIconHandle>();
  const ToggleIcon = userMode === "action" ? MessageCircleIcon : XIcon;
  const PrimaryIcon = primary?.icon;

  // One height for the whole dock. The action button, the compose input pill,
  // and the toggle are three shapes of the SAME control, so they are pinned to
  // the same height — previously the action button was py-3 while the input
  // grew to its textarea's min-height, so toggling visibly resized the slot.
  const DOCK_HEIGHT = "h-12";

  return (
    <div className="bg-gradient-to-t from-background via-background/95 to-background/0 px-4 pb-3 pt-6 backdrop-blur-sm">
      <div className="mx-auto flex max-w-[800px] items-end gap-2">
        <div className="min-w-0 flex-1">
          {attachmentChips ? (
            <div className="mb-2 flex flex-wrap gap-2">{attachmentChips}</div>
          ) : null}

          {mode === "action" && primary ? (
            <button
              type="button"
              id={primary.id}
              onClick={primary.onClick}
              disabled={primary.disabled}
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
              {PrimaryIcon ? (
                <PrimaryIcon ref={primaryIcon.ref} size={16} aria-hidden />
              ) : null}
              {primary.label}
            </button>
          ) : (
            <PromptInput
              id={inputId}
              onSubmit={(message) => {
                if (message.text.trim()) onAsk?.(message.text);
              }}
              className={cn(
                // The textarea auto-grows (field-sizing) for long questions,
                // but the collapsed pill matches the action button exactly;
                // content-box + auto height keeps it from jumping to the
                // textarea's own min-height on focus.
                "[&_[data-slot=input-group]]:h-auto",
                "[&_[data-slot=input-group]]:min-h-12",
                "[&_[data-slot=input-group]]:rounded-full",
                "[&_[data-slot=input-group]]:border-input",
                "[&_[data-slot=input-group]]:shadow-sm",
                "[&_[data-slot=input-group]]:px-1.5"
              )}
            >
              <PromptInputBody>
                <PromptInputTextarea
                  rows={1}
                  placeholder={placeholder}
                  className="min-h-12 max-h-32 py-3"
                />
              </PromptInputBody>
              <PromptInputTools className="shrink-0 pl-1">{attachmentSlot}</PromptInputTools>
              <PromptInputSubmit
                className="shrink-0 rounded-full"
                disabled={askDisabled || askPending}
                status={askPending ? "submitted" : undefined}
              />
            </PromptInput>
          )}
        </div>

        {canToggle ? (
          <button
            type="button"
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
