import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

// DESIGN-REQ-002: the stream and dock inherit one width and one set of gutters.
// The surface is the inline-size container. Its inset centers 752px of content
// (the 800px shell minus desktop gutters) without narrowing the scroll region.
export function StudyColumn({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn(
      "flex w-full min-h-0 flex-1 flex-col",
      "[--study-column-gutter:1rem] sm:[--study-column-gutter:1.5rem]",
      "[--study-column-inset:max(var(--study-column-gutter),calc((100cqw_-_752px)/2))] px-(--study-column-inset)",
      className,
    )}>
      {children}
    </div>
  );
}
