import type { ReactNode } from "react";
import { Spinner } from "@/components/ui/spinner";
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
      {busy ? <Spinner aria-hidden className="absolute right-3 top-1/2 -translate-y-1/2" /> : null}
    </div>
  );
}
