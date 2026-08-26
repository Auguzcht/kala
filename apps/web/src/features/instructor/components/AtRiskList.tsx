import { useNavigate } from "@tanstack/react-router";
import { useAtRisk } from "@/features/instructor";
import { Skeleton } from "@/components/ui/skeleton";

// Needs-support list. Flags are evidence-triggered with supportive wording
// ("Needs support", never "Failing"); every flag carries its reason. The
// good-news empty state reads as success, not a broken screen.

export function AtRiskList({ courseId }: { courseId: string }) {
  const { data, isLoading } = useAtRisk(courseId);
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  const flags = data?.flags ?? [];

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <h2 className="font-display text-base font-semibold text-foreground">Needs support</h2>
        {flags.length > 0 ? (
          <span className="rounded-full bg-destructive px-2 py-0.5 font-mono text-[11.5px] font-bold text-white">
            {flags.length}
          </span>
        ) : null}
      </div>

      {flags.length === 0 ? (
        <div className="flex items-start gap-3 border border-dashed bg-card p-5">
          <span className="mt-1 size-2 shrink-0 rounded-full bg-brand-green" aria-hidden />
          <p className="text-[13px] leading-relaxed text-muted-foreground">
            No one needs support right now. Check back after the next activity.
          </p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {flags.map((f) => (
            <button
              key={f.userId}
              type="button"
              onClick={() => navigate({ to: "/class/student/$uid", params: { uid: f.userId } })}
              className="group w-full border bg-card p-4 text-left transition-colors hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <div className="flex items-center gap-2.5">
                <span className="grid size-7 shrink-0 place-items-center rounded-full bg-brand-slate text-[10.5px] font-bold text-background">
                  {f.initials}
                </span>
                <span className="flex-1 text-[13px] font-semibold text-foreground group-hover:underline">
                  {f.pseudonym}
                </span>
                {f.daysInactive != null && f.daysInactive >= 1 ? (
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {f.daysInactive}d inactive
                  </span>
                ) : null}
              </div>
              <p className="mt-2.5 text-[12.5px] leading-relaxed text-muted-foreground">
                {f.reason}
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
