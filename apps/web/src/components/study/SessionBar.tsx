import type { ReactNode } from "react";
import { ChevronLeftIcon } from "@/components/ui/chevron-left";
import { ChevronRightIcon } from "@/components/ui/chevron-right";

export function SessionBar({
  title,
  progress,
  onBack,
  backLabel = "Back",
  onForward,
  forwardLabel,
  forwardDisabled,
  right,
}: {
  title?: string;
  progress?: {
    current: number;
    total: number;
    label?: string;
    bloomLevel?: string | null;
  };
  onBack?: () => void;
  backLabel?: string;
  onForward?: () => void;
  forwardLabel?: string;
  forwardDisabled?: boolean;
  right?: ReactNode;
}) {
  const pct = progress && progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : 0;

  return (
    <div className="flex items-center gap-3 bg-gradient-to-b from-background via-background/95 to-background/0 px-4 py-3 backdrop-blur-sm">
      {onBack ? (
        <button
          type="button"
          onClick={onBack}
          aria-label={backLabel}
          className="inline-flex size-8 shrink-0 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronLeftIcon size={16} />
        </button>
      ) : null}

      {title ? (
        <span className="truncate font-display text-sm font-semibold text-foreground">
          {title}
        </span>
      ) : null}

      {progress ? (
        <div className="flex min-w-32 flex-1 items-center gap-3">
          <div
            className="h-1 flex-1 overflow-hidden rounded-full bg-muted"
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
            {progress.bloomLevel ? (
              <>
                {" · "}
                <span className="capitalize">{progress.bloomLevel}</span>
              </>
            ) : null}
          </span>
        </div>
      ) : <div className="flex-1" />}

      {right}

      {onForward ? (
        <button
          type="button"
          onClick={onForward}
          disabled={forwardDisabled}
          aria-label={forwardLabel ?? "Next"}
          className="inline-flex size-8 shrink-0 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors hover:bg-accent disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronRightIcon size={16} />
        </button>
      ) : null}
    </div>
  );
}
