import type { ReactNode } from "react";
import { InView } from "@/components/motion/in-view";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { MasteryBand } from "@/components/kala";
import { EmptyState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { groupByModule } from "@/features/twin";
import type { TwinSkill } from "@/features/twin";

// The shared topic-choice landing — extracted from routes/course/lessons.tsx
// (Stage 3 of the AI overhaul, docs/AI_OVERHAUL_TODO.md): Practice and
// Flashcards each get their own version of exactly this page now, choosing
// what to work on is a session-scoped decision, not something you switch
// mid-session (that's what the Sheet+Command picker got wrong, and why
// it's gone rather than patched again). Grouped by module via the shared
// groupByModule, an optional highlighted "recommended" card above the
// grid for surfaces that have an obvious default pick (Practice's weakest
// skill, Flashcards' due-first).
export function TopicLanding({
  isLoading,
  skills,
  onChoose,
  recommended,
  caption,
  gridId,
  firstCardId,
}: {
  isLoading: boolean;
  skills: TwinSkill[];
  onChoose: (skillId: string) => void;
  /** Rendered above the grouped list — a highlighted recommended pick.
   * Optional; Lessons has no single "best" skill to default to. */
  recommended?: ReactNode;
  /** Static caption shown under the Bloom chip on every card — what this
   * surface actually does ("guided walkthrough with checks", "quick
   * graded reps", "spaced recall card"), differs per surface. */
  caption: string;
  /** Tour anchor for the first module's grid. */
  gridId?: string;
  /** Tour anchor for the very first skill card — only relevant where the
   * tour clicks a grid card directly rather than the recommended card. */
  firstCardId?: string;
}) {
  if (isLoading) {
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  if (skills.length === 0) {
    return (
      <EmptyState
        title="No skills mapped yet"
        description="This needs approved skills for the course. Course content needs the ingest + skill-proposal pass first."
      />
    );
  }

  const grouped = groupByModule(skills);

  return (
    <div className="space-y-5">
      {recommended}
      <InView
        once
        variants={{ hidden: { opacity: 0, y: 8 }, visible: { opacity: 1, y: 0 } }}
        transition={{ duration: 0.35 }}
      >
        <Accordion type="multiple" defaultValue={grouped.map(([module]) => module)}>
          {grouped.map(([module, moduleSkills], mi) => (
            <AccordionItem key={module} value={module}>
              <AccordionTrigger>
                <span className="flex items-center gap-1.5">
                  <span className="capitalize">{module}</span>
                  <span className="font-mono text-xs text-muted-foreground">
                    {moduleSkills.length}
                  </span>
                </span>
              </AccordionTrigger>
              <AccordionContent>
                {/* Anchor only on the first module's grid — the original
                    Lessons version put this id unconditionally on every
                    module's grid div, which is invalid HTML (duplicate
                    ids across simultaneously-open accordion panels) that
                    happened to work by accident since querySelector just
                    grabs the first match. Fixed while unifying this into
                    a shared component. */}
                <div id={mi === 0 ? gridId : undefined} className="grid gap-3 sm:grid-cols-2">
                  {moduleSkills.map((s, si) => (
                    <button
                      key={s.skillId}
                      type="button"
                      id={mi === 0 && si === 0 ? firstCardId : undefined}
                      onClick={() => onChoose(s.skillId)}
                      className="group border bg-card p-4 text-left transition-colors hover:bg-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm font-semibold text-foreground group-hover:underline">
                          {s.name}
                        </span>
                        <MasteryBand band={s.band} />
                      </div>
                      <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        {s.bloomLevel ? (
                          <span className="rounded-sm bg-muted px-1.5 py-0.5 text-[10px] font-semibold capitalize text-muted-foreground">
                            {s.bloomLevel}
                          </span>
                        ) : null}
                        <span>{caption}</span>
                      </p>
                    </button>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </InView>
    </div>
  );
}
