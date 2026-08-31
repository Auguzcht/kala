import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { LessonChat } from "@/features/lessons";
import { useTwin } from "@/features/twin";
import { MasteryBand } from "@/components/kala";
import { InView } from "@/components/motion/in-view";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { EmptyState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ChevronLeftIcon } from "@/components/ui/chevron-left";
import type { TwinSkill } from "@/features/twin";

export const Route = createFileRoute("/course/lessons")({
  component: LessonsPage,
});

// Lessons are grouped by TOPIC (module_ref), not by Bloom's level — a
// student opening Lessons wants "what topic is this," not "what cognitive
// tier." Bloom stays as a small secondary tag on each card. Skills without a
// module land in "Other topics" so nothing is hidden.
function groupByModule(skills: TwinSkill[]) {
  const byModule = new Map<string, TwinSkill[]>();
  for (const s of skills) {
    const key = s.moduleRef?.trim() || "Other topics";
    byModule.set(key, [...(byModule.get(key) ?? []), s]);
  }
  return [...byModule.entries()].sort((a, b) =>
    a[0] === "Other topics" ? 1 : b[0] === "Other topics" ? -1 : a[0].localeCompare(b[0])
  );
}

function LessonsPage() {
  const courseId = useSession()?.courseId ?? "";
  const { data: twin, isLoading } = useTwin(courseId);
  const [skillId, setSkillId] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        eyebrow="Guided lessons"
        title="Work through it, step by step"
        description="Kala walks you through one skill at a time — explain, check, advance. Lessons are written once and replayed, so every pass is consistent."
      />
      {skillId ? (
        <div className="space-y-4">
          <Button variant="outline" size="sm" onClick={() => setSkillId(null)}>
            <ChevronLeftIcon size={14} /> Choose another skill
          </Button>
          <LessonChat courseId={courseId} skillId={skillId} />
        </div>
      ) : isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : !twin || twin.skills.length === 0 ? (
        <EmptyState
          title="No skills mapped yet"
          description="Lessons are built from approved skills. Course content needs the ingest + skill-proposal pass first."
        />
      ) : (
        <InView
          once
          variants={{ hidden: { opacity: 0, y: 8 }, visible: { opacity: 1, y: 0 } }}
          transition={{ duration: 0.35 }}
        >
          <Accordion
            type="multiple"
            defaultValue={groupByModule(twin.skills).map(([module]) => module)}
          >
            {groupByModule(twin.skills).map(([module, moduleSkills], mi) => (
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
                  <div id="tour-lessons-picker" className="grid gap-3 sm:grid-cols-2">
                    {moduleSkills.map((s, si) => (
                      <button
                        key={s.skillId}
                        type="button"
                        id={mi === 0 && si === 0 ? "tour-lessons-first-card" : undefined}
                        onClick={() => setSkillId(s.skillId)}
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
                          <span>guided walkthrough with checks</span>
                        </p>
                      </button>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </InView>
      )}
    </>
  );
}
