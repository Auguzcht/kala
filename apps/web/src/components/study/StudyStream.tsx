import type { ReactNode } from "react";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { cn } from "@/lib/utils";

// Shared stream container for every surface that presents a sequence of
// blocks — teaching bubbles, quiz cards, eventually chat messages — instead
// of a single static panel. Lessons is the first surface on this (Stage 1
// of the AI-overhaul plan, see docs/AI_OVERHAUL_TODO.md); Tutor and the
// quiz surfaces follow in later stages.
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
// `flex-1` internally) — max-height alone isn't enough, so this wrapper
// sets an explicit height rather than a cap.
export function StudyStream({
  children,
  className,
  height = "h-[62vh]",
}: {
  children: ReactNode;
  className?: string;
  /** Explicit height Tailwind class. Must be a real height (h-*), not a
   * max-height, or Conversation's internal flex-1 has nothing to fill. */
  height?: string;
}) {
  return (
    <div className={cn("relative flex flex-col", height, className)}>
      <Conversation>
        <ConversationContent className="gap-5 px-5 py-6">
          {children}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>
    </div>
  );
}
