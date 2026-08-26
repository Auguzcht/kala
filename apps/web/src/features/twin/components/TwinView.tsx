import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
} from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { useTwin } from "@/features/twin";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MasteryBand, BloomsLadder, EvidenceLedger, MasteryRing } from "@/components/kala";
import { Skeleton } from "@/components/ui/skeleton";

// The signature surface: the student's own twin. Radar across skills
// (no-evidence skills sit at center — honest, they fill in as you practice),
// readiness as one instrument-panel gauge, mastery as qualitative bands,
// and the append-only evidence ledger below.

const chartConfig = {
  mastery: { label: "Mastery", color: "var(--chart-3)" },
} satisfies ChartConfig;

export function TwinView({ courseId }: { courseId: string }) {
  const { data, isLoading, isError, refetch } = useTwin(courseId);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }
  if (isError || !data) {
    return (
      <EmptyState
        title="We could not load your twin"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  }

  const skills = data.skills;
  const noEvidence = skills.filter((s) => s.estimate === null);
  const radarData = skills.map((s) => ({
    skill: s.name,
    mastery: s.estimate ?? 0,
  }));
  const ranked = [...skills].sort((a, b) => {
    const aNull = a.estimate === null ? -1 : a.estimate;
    const bNull = b.estimate === null ? -1 : b.estimate;
    return aNull - bNull;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-stretch gap-4">
        {/* Readiness gauge */}
        <Card className="flex min-w-56 flex-1 flex-col items-center justify-center gap-3 py-8">
          <MasteryRing estimate={data.readiness} size={112} strokeWidth={8} label="Board readiness" />
          <div className="text-center">
            <p className="font-display text-sm font-semibold">Board readiness</p>
            <p className="text-xs text-muted-foreground">Rollup of your mastery across skills</p>
          </div>
        </Card>

        {/* Radar */}
        <Card className="min-w-72 flex-1">
          <CardHeader>
            <CardTitle className="text-base">Mastery across skills</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer config={chartConfig} className="mx-auto aspect-square max-h-[300px]">
              <RadarChart data={radarData}>
                <PolarGrid stroke="var(--border)" />
                <PolarAngleAxis dataKey="skill" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
                <Radar dataKey="mastery" stroke="var(--chart-3)" fill="var(--chart-3)" fillOpacity={0.35} />
                <ChartTooltip content={<ChartTooltipContent />} />
              </RadarChart>
            </ChartContainer>
            {noEvidence.length > 0 ? (
              <p className="mt-2 text-center text-xs text-muted-foreground">
                {noEvidence.length === 1 ? "One skill has no evidence yet" : `${noEvidence.length} skills have no evidence yet`} — they sit at the center until you practice them.
              </p>
            ) : null}
          </CardContent>
        </Card>
      </div>

      {/* Skills by Bloom's */}
      <div className="flex flex-wrap items-stretch gap-4">
        <Card className="min-w-72 flex-1">
          <CardHeader>
            <CardTitle className="text-base">Skills</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {ranked.map((s) => (
              <div
                key={s.skillId}
                className="flex items-center gap-3 rounded-sm px-2 py-2 hover:bg-accent/50"
                title={s.estimate === null ? undefined : `Estimate ${Math.round(s.estimate * 100)}% · ${s.attempts} attempt${s.attempts === 1 ? "" : "s"}`}
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{s.name}</p>
                  <p className="text-[10.5px] uppercase tracking-wide text-muted-foreground">
                    {s.bloomLevel ?? "skill"}
                  </p>
                </div>
                <span className="font-mono text-xs tabular-nums text-muted-foreground">
                  {s.attempts > 0 ? `${s.attempts}×` : ""}
                </span>
                <MasteryBand band={s.band} />
              </div>
            ))}
            {ranked.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No skills mapped for this course yet.
              </p>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <BloomsLadder skills={skills} />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Evidence ledger</CardTitle>
        </CardHeader>
        <CardContent>
          <EvidenceLedger events={data.evidence} />
        </CardContent>
      </Card>
    </div>
  );
}
