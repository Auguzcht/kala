import { ChevronDown } from "lucide-react";
import { useAutoMatchedSkills, useDetachAutoMatchedSkill } from "@/features/instructor";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

// Auto-matched skills audit (docs/DEEPSEEK_DEDUP_AND_AUDIT.md): skills this
// course inherited via cross-course auto-match (they resembled an
// already-approved skill in another course, >= 0.92 similarity). Reuse is a
// default, not a lock-in — each row can be detached back to a course-local
// proposed skill for tuning. Hidden entirely when there's nothing inherited.

export function AutoMatchedSection({ courseId }: { courseId: string }) {
  const { data, isLoading } = useAutoMatchedSkills(courseId);
  const detach = useDetachAutoMatchedSkill(courseId);

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-5 w-72" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }

  const items = data?.autoMatched ?? [];
  if (items.length === 0) return null;

  return (
    <Collapsible defaultOpen>
      <div className="border bg-card">
        <CollapsibleTrigger className="flex w-full items-center gap-3 px-5 py-4 text-left">
          <div className="min-w-0 flex-1">
            <h2 className="font-display text-[16px] font-semibold text-foreground">
              Auto-matched from other courses
            </h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              These skills were reused from another course. Tune one to make a course-specific
              copy for review.
            </p>
          </div>
          <span className="rounded-full bg-muted px-2.5 py-0.5 font-mono text-[11.5px] font-bold text-muted-foreground">
            {items.length}
          </span>
          <ChevronDown className="size-4 text-muted-foreground transition-transform data-[state=open]:rotate-180" />
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="divide-y divide-border border-t">
            {items.map((s) => (
              <div key={s.id} className="flex flex-wrap items-center gap-3 px-5 py-3.5">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-[13.5px] font-semibold text-foreground">{s.name}</p>
                    <span className="rounded-sm border border-border bg-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                      {s.bloom_level}
                    </span>
                    <span className="font-mono text-[11px] text-muted-foreground">
                      weight {s.blueprint_weight}
                    </span>
                    {s.module_ref ? (
                      <span className="text-[11px] text-muted-foreground">· {s.module_ref}</span>
                    ) : null}
                  </div>
                  {s.proposed_source ? (
                    <p className="mt-1 text-xs text-muted-foreground">{s.proposed_source}</p>
                  ) : null}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={detach.isPending}
                  onClick={() => detach.mutate(s.id)}
                >
                  {detach.isPending ? (
                    <>
                      <Spinner className="size-3.5" /> Detaching…
                    </>
                  ) : (
                    "Tune for this course"
                  )}
                </Button>
              </div>
            ))}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}
