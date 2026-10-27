import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { StudyColumn } from "@/components/study/StudyColumn";

// The active-session shell. Its parent in CourseShell supplies a real height;
// the stream child then owns the only scrollable region.
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
    <div
      data-study-surface
      className={cn("flex h-full min-h-0 flex-col [container-type:inline-size]", className)}
    >
      {bar ? <div className="shrink-0">{bar}</div> : null}
      <StudyColumn>
        <div className="min-h-0 flex-1">{children}</div>
        {dock ? <div className="shrink-0">{dock}</div> : null}
      </StudyColumn>
    </div>
  );
}
