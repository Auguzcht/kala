import type { ReactNode } from "react";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { cn } from "@/lib/utils";

// Shared stream container for every surface that presents a sequence of
// blocks — teaching bubbles, quiz cards, eventually chat messages — instead
// of a single static panel. Current shared-surface boundaries are in
// docs/features/tutor/README.md#tutor-req-011-preserve-the-tutor-and-study-hub-component-boundary.
// Tutor owns its conversation surface; reuse does not imply one shared state owner.
//
// Built on ai-elements' Conversation, which wraps use-stick-to-bottom:
// content sticks to the bottom as blocks are added, and stops fighting the
// student the moment they scroll up to reread something earlier, with a
// "scroll to bottom" button to jump back down. This replaces every
// surface's own hand-rolled `scrollRef.current.scrollTop = scrollHeight`
// effect (LessonChat had one), which just jumps hard on every render and
// has no way back down once you've scrolled up.
//
// Conversation needs a parent with a REAL height to flex into (it's
// `flex-1` internally). In a StudySurface it fills that flex slot; the
// temporary height prop keeps the pre-migration surfaces stable until each
// mode moves onto StudySurface.
export function StudyStream({
  children,
  className,
  height,
}: {
  children: ReactNode;
  className?: string;
  /** Transitional legacy height for surfaces not yet migrated to
   * StudySurface. New surfaces must omit this and fill the flex slot. */
  height?: string;
}) {
  return (
    <div
      className={cn(
        "relative flex h-full min-h-0 flex-1 flex-col",
        height,
        className
      )}
    >
      <Conversation>
        <ConversationContent className="gap-5 pt-6 pb-24">
          <div className="mx-auto flex w-full max-w-[800px] flex-col gap-5">
            {children}
          </div>
        </ConversationContent>
        <ConversationScrollButton className="bottom-20" />
      </Conversation>
    </div>
  );
}
