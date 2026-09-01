import { useEffect, useRef, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { ChevronDownIcon } from "lucide-react";
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
  useProposedSkills,
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
import { cn } from "@/lib/utils";

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

  // The skill review section was disappearing in practice, not in code: a
  // plain uppercase text link, collapsed by default, at the bottom of an
  // already long page, with no visible signal that there was anything
  // waiting behind it. If this course has skill proposals sitting unreviewed
  // right now, nothing on the collapsed trigger said so.
  //
  // Two fixes: a real chevron so it reads as expandable at a glance, and a
  // count badge sourced from the same query the panel itself uses (a cache
  // hit, not a second request). The section still auto-opens the first
  // time it learns there's something pending — but only once, tracked by
  // the ref below, so it never fights a teacher who deliberately collapses
  // it back after reviewing.
  const proposedSkills = useProposedSkills(courseId);
  const pendingSkillCount = proposedSkills.data?.proposed.length ?? 0;
  const [skillPanelOpen, setSkillPanelOpen] = useState(false);
  const hasAutoOpened = useRef(false);
  useEffect(() => {
    if (!hasAutoOpened.current && pendingSkillCount > 0) {
      setSkillPanelOpen(true);
      hasAutoOpened.current = true;
    }
  }, [pendingSkillCount]);

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
            <TabsTrigger id="tour-tab-trends" value="trends">Trends</TabsTrigger>
            <TabsTrigger id="tour-tab-heatmap" value="heatmap">
              Skills &times; Bloom&apos;s
            </TabsTrigger>
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
            human approves here (docs/SKILL_PIPELINE.md). Auto-opens the
            first time this page learns there's something pending, so a
            real review queue is never hidden behind a click; stays exactly
            where a teacher leaves it after that. */}
        <Collapsible open={skillPanelOpen} onOpenChange={setSkillPanelOpen}>
          <CollapsibleTrigger
            id="tour-skill-review-trigger"
            className={cn(
              "flex w-full items-center gap-2 border-t pt-4 text-left text-[11.5px] font-semibold uppercase tracking-[0.05em] hover:text-foreground",
              pendingSkillCount > 0 ? "text-foreground" : "text-brand-slate"
            )}
          >
            <ChevronDownIcon
              className={cn(
                "size-3.5 shrink-0 transition-transform",
                skillPanelOpen ? "rotate-0" : "-rotate-90"
              )}
              aria-hidden
            />
            Skill mapping and review
            {pendingSkillCount > 0 ? (
              <span className="rounded-full bg-brand-orange px-2 py-0.5 font-mono text-[11px] font-bold normal-case tracking-normal text-brand-orange-foreground">
                {pendingSkillCount} pending
              </span>
            ) : null}
            <span className="font-normal normal-case tracking-normal text-muted-foreground">
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
