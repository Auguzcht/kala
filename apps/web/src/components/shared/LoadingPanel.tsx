import { cn } from "@/lib/utils";

// Hornbill + skeleton blocks for first-load / generation waits. DESIGN.md
// signature element #7: "The hornbill as guide... loading moments." The
// skeleton is shaped loosely like the content that's coming (an MCQ card,
// a lesson step), never a bare spinner or a line of text. `role="status"`
// + aria-live so screen readers announce the wait.

export function LoadingPanel({
  label,
  lines = 3,
  className,
}: {
  label?: string;
  lines?: number;
  className?: string;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "flex flex-col items-center gap-5 rounded-md border bg-card px-6 py-10",
        className
      )}
    >
      <img
        src="/Kala-Logo.png"
        alt=""
        className="size-12 object-contain opacity-80"
      />
      {label ? <p className="text-sm text-muted-foreground">{label}</p> : null}
      <div className="w-full max-w-md space-y-2.5">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "h-3 animate-pulse rounded-sm bg-muted",
              i === 0 ? "w-2/3" : i === lines - 1 ? "w-1/3" : "w-full"
            )}
          />
        ))}
      </div>
    </div>
  );
}
