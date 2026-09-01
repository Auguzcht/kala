import { useRef, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import {
  AtRiskList,
  AutoMatchedSection,
  CohortCharts,
  CohortStats,
  Heatmap,
  LearnerSheet,
  RosterTable,
  SkillReviewPanel,
} from "@/features/instructor";
import type { LearnerStatus } from "@/features/instructor";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/class/")({
  component: ClassDashboard,
});

// The instructor overview, read top to bottom the way a teacher triages:
//
//   1. KPI strip      is the class moving, and is anything waiting on me
//   2. Roster         who needs me first (real names, sortable, searchable)
//   3. Trends         is practice working, what should I reteach
//   4. Skill mapping  the setup work, collapsed because it is not daily
//
// De-identify is ONE switch at the page level, not one per panel. Roster
// and Needs support both read names from the same identity lookup
// (cohort.load_identities), so they must show the same thing at the same
// time — two independent toggles could disagree with each other mid-demo,
// which is worse than not having the feature.
//
// The roster's status filter is likewise lifted here so Needs support can
// hand off into it: past a threshold, the panel stops growing its own list
// and instead switches the roster to the same filter and scrolls it into
// view, rather than the page growing unboundedly as the flagged count does.

function ClassDashboard() {
  const courseId = useSession()?.courseId ?? "";
  const [selected, setSelected] = useState<string | null>(null);
  const [deidentified, setDeidentified] = useState(false);
  const [rosterFilter, setRosterFilter] = useState<"all" | LearnerStatus>("all");
  const rosterRef = useRef<HTMLDivElement | null>(null);

  const viewNeedsSupportInRoster = () => {
    setRosterFilter("needs-support");
    rosterRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <>
      <PageHeader
        eyebrow="Instructor dashboard"
        title="Class overview"
        description="Kala reads every learner's evidence and tells you who needs you first. It recommends what each one should do next. You decide which of those recommendations reaches them."
      />

      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CohortStats courseId={courseId} />
        </div>

        <div className="flex items-center justify-end gap-2">
          <Switch
            id="page-deidentify"
            checked={deidentified}
            onCheckedChange={setDeidentified}
          />
          <Label htmlFor="page-deidentify" className="text-[11.5px] text-muted-foreground">
            De-identify names on this page
          </Label>
        </div>

        <div className="flex flex-wrap items-start gap-6">
          <div className="min-w-0 flex-1" id="roster-panel" ref={rosterRef}>
            <RosterTable
              courseId={courseId}
              selectedUserId={selected}
              onSelect={setSelected}
              filter={rosterFilter}
              onFilterChange={setRosterFilter}
              deidentified={deidentified}
            />
          </div>

          <div id="at-risk-list" className="w-full max-w-sm shrink-0">
            <AtRiskList
              courseId={courseId}
              deidentified={deidentified}
              onViewAllInRoster={viewNeedsSupportInRoster}
            />
          </div>
        </div>

        <Tabs defaultValue="trends">
          <TabsList>
            <TabsTrigger value="trends">Trends</TabsTrigger>
            <TabsTrigger value="heatmap">Skills &times; Bloom&apos;s</TabsTrigger>
          </TabsList>
          <TabsContent value="trends" className="mt-4">
            <div id="cohort-analytics">
              <CohortCharts courseId={courseId} />
            </div>
          </TabsContent>
          <TabsContent value="heatmap" className="mt-4">
            <div id="heatmap-panel">
              <Heatmap courseId={courseId} deidentified={deidentified} />
            </div>
          </TabsContent>
        </Tabs>

        {/* HITL skill proposals: nothing proposed reaches learners until a
            human approves here (docs/SKILL_PIPELINE.md). Collapsed by
            default because it is course-setup work, not daily teaching —
            the panel itself still surfaces its own pending count. */}
        <Collapsible>
          <CollapsibleTrigger className="flex w-full items-center gap-2 border-t pt-4 text-left text-[11.5px] font-semibold uppercase tracking-[0.05em] text-brand-slate hover:text-foreground">
            Skill mapping and review
            <span className="text-[10.5px] font-normal normal-case tracking-normal text-muted-foreground">
              what Kala measures in this course
            </span>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-4 space-y-6">
            <SkillReviewPanel courseId={courseId} />
            <AutoMatchedSection courseId={courseId} />
          </CollapsibleContent>
        </Collapsible>
      </div>

      <LearnerSheet
        courseId={courseId}
        userId={selected}
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      />
    </>
  );
}
