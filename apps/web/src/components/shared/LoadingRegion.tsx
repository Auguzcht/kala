import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** One indicator for a skeleton region; preserves its existing grid and size. */
export function LoadingRegion({ children, className, label = "Loading…", busy = true }: {
  children: ReactNode;
  className?: string;
  label?: string;
  busy?: boolean;
}) {
  return (
    <div role={busy ? "status" : undefined} aria-label={busy ? label : undefined} aria-busy={busy || undefined} className={cn("relative", className)}>
      {children}
    </div>
  );
}
