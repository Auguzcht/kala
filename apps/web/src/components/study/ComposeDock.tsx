import type { ReactNode } from "react";
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from "@/components/ai-elements/prompt-input";

// Shared conversational dock. The input group, rather than the form, receives
// the generous radius because PromptInput renders the form as its outer node.
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
  primaryAction?: ReactNode;
  onAsk?: (text: string) => void;
  askDisabled?: boolean;
  askPending?: boolean;
  placeholder?: string;
  attachmentSlot?: ReactNode;
  attachmentChips?: ReactNode;
  /** Applied to PromptInput's form to preserve the Tutor tour contract. */
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
            <PromptInput
              id={inputId}
              onSubmit={(message) => {
                if (message.text.trim()) onAsk(message.text);
              }}
              className="[&_[data-slot=input-group]]:rounded-2xl [&_[data-slot=input-group]]:shadow-sm"
            >
              <PromptInputBody>
                <PromptInputTextarea placeholder={placeholder} />
              </PromptInputBody>
              <PromptInputFooter>
                <PromptInputTools>{attachmentSlot}</PromptInputTools>
                <PromptInputSubmit
                  disabled={askDisabled || askPending}
                  status={askPending ? "submitted" : undefined}
                />
              </PromptInputFooter>
            </PromptInput>
          </div>
        ) : null}
      </div>
    </div>
  );
}
