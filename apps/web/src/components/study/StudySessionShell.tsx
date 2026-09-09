import { type ReactNode } from "react";
import { ChevronLeftIcon } from "@/components/ui/chevron-left";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// Study session chrome — the floating persistent bar the Gizmo-style surfaces
// share: back affordance, a slim progress indicator whose meaning the caller
// passes in (card N/total for flashcards, step N/total for lessons, session
// count for practice), and an optional right slot for anything else a
// specific surface needs. GamificationSummary is NOT dropped in here by
// callers anymore — it lives once, persistently, in CourseShell's topbar
// (mounting a second copy per-surface was firing duplicate badge toasts).
// This component stays feature-agnostic and never imports one itself.
//
// It owns ONLY the chrome. Tutor, Lessons, Flashcards, and Practice render
// their own content as children; the shell has no idea what's inside.

export function StudySessionShell({
  progress,
  onBack,
  right,
  children,
}: {
  progress?: { current: number; total: number; label?: string };
  onBack?: () => void;
  right?: ReactNode;
  children: ReactNode;
}) {
  const pct = progress && progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0;
  // The chrome row only exists when it has content. A surface with none of
  // the three (back / progress / right slot) gets no bar and no separator
  // — an empty header with a bare border reads as a broken layout.
  const hasChrome = Boolean(onBack || progress || right);

  return (
    <div className="space-y-5">
      {hasChrome ? (
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-border/60 pb-3">
        {onBack ? (
          <Button variant="ghost" size="sm" onClick={onBack} className="px-2">
            <ChevronLeftIcon size={16} className="text-muted-foreground" />
            Back
          </Button>
        ) : null}

        {progress ? (
          <div className="flex min-w-40 flex-1 items-center gap-3">
            <div
              className="h-1 max-w-xs flex-1 overflow-hidden rounded-full bg-muted"
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

        {right ? <div className="ml-auto">{right}</div> : null}
      </div>
      ) : null}

      <div className={cn("min-w-0")}>{children}</div>
    </div>
  );
}
