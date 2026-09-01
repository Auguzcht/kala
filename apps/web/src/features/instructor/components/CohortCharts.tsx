import type { ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  XAxis,
  YAxis,
} from "recharts";
import { useCohortStats } from "@/features/instructor";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { MasteryBand } from "@/components/kala";
import { EmptyState } from "@/components/shared/EmptyState";

// Four charts, each answering a question a teacher actually asks:
//
//   Readiness trend   is the class moving, and in which direction
//   Daily activity    is anyone working, and did practice land
//   Band mix          how much of the class is where on the mastery scale
//   Weakest skills    what should I reteach on Monday
//
// All four are drawn from series the backend computed from the same
// evidence log the twin runs on. Nothing here is a fitted curve or a
// placeholder — an empty chart says "no evidence yet", it does not invent
// a shape.

const trendConfig = {
  readiness: { label: "Cohort readiness", color: "var(--brand-gold)" },
} satisfies ChartConfig;

const activityConfig = {
  correct: { label: "Correct", color: "var(--brand-gold)" },
  missed: { label: "Missed", color: "var(--brand-slate)" },
} satisfies ChartConfig;

const BAND_FILL: Record<string, string> = {
  "no-evidence": "var(--band-none)",
  developing: "var(--band-developing)",
  proficient: "var(--band-proficient)",
  mastered: "var(--band-mastered)",
};

function shortDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// A genuinely empty chart — every bar at zero, a trend line with one point —
// does not read as "no data yet" to a viewer. It reads as broken: thin
// stray gridlines, a bar chart with nothing in it, labels that look
// misaligned because there's no shape to anchor them to. That was exactly
// what "Weakest skills" and "Practice volume" looked like with a
// zero-evidence cohort.
//
// This renders a fixed, clearly-fake sample of the SAME chart type — muted
// colors, blurred, never brand-gold so it can't be mistaken for real data —
// with the actual empty-state message overlaid on top. The illustrative
// shape does the job a live chart does (showing what this panel will look
// like once there's evidence) without asserting anything untrue about this
// cohort. Height matches each real chart exactly so swapping between empty
// and populated never shifts the layout.
function ChartSkeleton({
  height,
  message,
  children,
}: {
  height: number;
  message: string;
  children: ReactNode;
}) {
  return (
    <div className="relative" style={{ height }}>
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 select-none opacity-40 blur-[3px] grayscale-[0.4]"
      >
        {children}
      </div>
      <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-b from-card/30 via-card/75 to-card/30 px-8">
        <p className="max-w-[240px] text-center text-xs leading-relaxed text-muted-foreground">
          {message}
        </p>
      </div>
    </div>
  );
}

// Fixed illustrative series for the three skeletons below. Not random —
// random data would redraw differently on every refresh, which looks like
// a glitch rather than a placeholder.
const SAMPLE_TREND = [
  { label: "Wk 1", readiness: 0.42 },
  { label: "Wk 2", readiness: 0.47 },
  { label: "Wk 3", readiness: 0.51 },
  { label: "Wk 4", readiness: 0.5 },
  { label: "Wk 5", readiness: 0.58 },
  { label: "Wk 6", readiness: 0.63 },
];

const SAMPLE_ACTIVITY = [
  { label: "Mon", correct: 3, missed: 1 },
  { label: "Tue", correct: 2, missed: 2 },
  { label: "Wed", correct: 4, missed: 1 },
  { label: "Thu", correct: 1, missed: 1 },
  { label: "Fri", correct: 3, missed: 0 },
  { label: "Sat", correct: 1, missed: 0 },
  { label: "Sun", correct: 2, missed: 1 },
];

const SAMPLE_WEAKEST = [
  { short: "Sample skill A", estimate: 0.28 },
  { short: "Sample skill B", estimate: 0.35 },
  { short: "Sample skill C", estimate: 0.48 },
  { short: "Sample skill D", estimate: 0.55 },
];

function SampleTrendChart() {
  return (
    <ChartContainer config={trendConfig} className="h-full w-full">
      <AreaChart data={SAMPLE_TREND} margin={{ left: -20, right: 8, top: 8 }}>
        <CartesianGrid vertical={false} stroke="var(--border)" />
        <XAxis dataKey="label" tickLine={false} axisLine={false} tick={false} />
        <YAxis domain={[0, 1]} tickLine={false} axisLine={false} tick={false} />
        <Area
          type="monotone"
          dataKey="readiness"
          stroke="var(--muted-foreground)"
          strokeWidth={2}
          fill="var(--muted)"
        />
      </AreaChart>
    </ChartContainer>
  );
}

function SampleActivityChart() {
  return (
    <ChartContainer config={activityConfig} className="h-full w-full">
      <BarChart data={SAMPLE_ACTIVITY} margin={{ left: -20, right: 8, top: 8 }}>
        <CartesianGrid vertical={false} stroke="var(--border)" />
        <XAxis dataKey="label" tickLine={false} axisLine={false} tick={false} />
        <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={false} />
        <Bar dataKey="correct" stackId="a" fill="var(--muted-foreground)" />
        <Bar dataKey="missed" stackId="a" fill="var(--border)" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ChartContainer>
  );
}

function SampleWeakestChart() {
  return (
    <ChartContainer config={{ estimate: { label: "Sample", color: "var(--muted-foreground)" } }} className="h-full w-full">
      <BarChart data={SAMPLE_WEAKEST} layout="vertical" margin={{ left: 0, right: 10 }}>
        <CartesianGrid horizontal={false} stroke="var(--border)" />
        <XAxis type="number" domain={[0, 1]} tickLine={false} axisLine={false} tick={false} />
        <YAxis
          type="category"
          dataKey="short"
          width={90}
          tickLine={false}
          axisLine={false}
          tick={{ fontSize: 10.5, fill: "var(--muted-foreground)" }}
        />
        <Bar dataKey="estimate" fill="var(--muted-foreground)" radius={[0, 2, 2, 0]} />
      </BarChart>
    </ChartContainer>
  );
}

export function CohortCharts({ courseId }: { courseId: string }) {
  const { data, isLoading } = useCohortStats(courseId);

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Skeleton className="h-64 w-full lg:col-span-7" />
        <Skeleton className="h-64 w-full lg:col-span-5" />
      </div>
    );
  }

  const trend = data.readinessTrend.map((t) => ({ ...t, label: shortDate(t.date) }));
  const activity = data.activitySeries.map((a) => ({ ...a, label: shortDate(a.date) }));
  const bands = data.bandDistribution;
  const bandTotal = bands.reduce((sum, b) => sum + b.count, 0) || 1;
  const weakest = data.skillBreakdown.slice(0, 6);
  const noActivity = activity.every((a) => a.correct + a.missed + a.ungraded === 0);
  // Distinct from "no skills mapped" (weakest.length === 0, handled by the
  // EmptyState below): skills exist, but nobody has attempted any of them
  // yet, so every estimate is null and the bars would all sit at 0% with
  // nothing to distinguish one from another.
  const noSkillEvidence = weakest.length > 0 && data.skillsCovered === 0;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      {/* Readiness trend — the movement question. Real history from the
          worker's snapshots, so a flat line means the class is flat, not
          that the chart is a placeholder. */}
      <Card className="lg:col-span-7">
        <CardHeader>
          <CardTitle className="text-base">Cohort readiness over time</CardTitle>
          <p className="text-xs text-muted-foreground">
            Nightly snapshots, last 28 days. Averaged across every learner with evidence.
          </p>
        </CardHeader>
        <CardContent>
          {trend.length < 2 ? (
            <ChartSkeleton
              height={200}
              message="Not enough history yet. The trend line draws once there are snapshots from two or more days."
            >
              <SampleTrendChart />
            </ChartSkeleton>
          ) : (
            <ChartContainer config={trendConfig} className="h-[200px] w-full">
              <AreaChart data={trend} margin={{ left: -20, right: 8, top: 8 }}>
                <defs>
                  <linearGradient id="kala-readiness-fill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--brand-gold)" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="var(--brand-gold)" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis
                  dataKey="label"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                  minTickGap={24}
                />
                <YAxis
                  domain={[0, 1]}
                  tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Area
                  type="monotone"
                  dataKey="readiness"
                  stroke="var(--brand-gold)"
                  strokeWidth={2}
                  fill="url(#kala-readiness-fill)"
                />
              </AreaChart>
            </ChartContainer>
          )}
        </CardContent>
      </Card>

      {/* Band mix — how much of the class sits where. Stacked as one bar
          rather than a donut: a donut hides small slices, and "how many
          cells have no evidence at all" is the slice that matters most
          early in a term. Not gated behind a skeleton: "100% no-evidence"
          is a real, informative answer for a fresh course, not an empty
          chart. */}
      <Card className="lg:col-span-5">
        <CardHeader>
          <CardTitle className="text-base">Mastery mix</CardTitle>
          <p className="text-xs text-muted-foreground">
            Every learner × skill cell, {bandTotal} in total.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex h-3 w-full overflow-hidden rounded-[2px] border">
            {bands.map((b) =>
              b.count === 0 ? null : (
                <span
                  key={b.band}
                  className="h-full"
                  style={{
                    width: `${(b.count / bandTotal) * 100}%`,
                    background: BAND_FILL[b.band],
                  }}
                  title={`${b.band}: ${b.count}`}
                />
              )
            )}
          </div>
          <div className="space-y-2">
            {bands.map((b) => (
              <div key={b.band} className="flex items-center gap-3">
                <MasteryBand band={b.band} />
                <span className="flex-1 text-right font-mono text-xs tabular-nums text-muted-foreground">
                  {b.count} · {Math.round((b.count / bandTotal) * 100)}%
                </span>
              </div>
            ))}
          </div>
          {data.bloomCoverage.length > 0 ? (
            <div className="border-t pt-3">
              <p className="mb-2 text-[10.5px] font-semibold uppercase tracking-[0.05em] text-brand-slate">
                By Bloom's level
              </p>
              <div className="space-y-1.5">
                {data.bloomCoverage.map((b) => (
                  <div key={b.level} className="flex items-center gap-2">
                    <span className="w-20 shrink-0 text-[11.5px] capitalize text-foreground">
                      {b.level}
                    </span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-brand-gold"
                        style={{ width: `${Math.round((b.estimate ?? 0) * 100)}%` }}
                      />
                    </div>
                    <span className="w-9 shrink-0 text-right font-mono text-[11px] tabular-nums text-muted-foreground">
                      {b.estimate === null ? "—" : `${Math.round(b.estimate * 100)}%`}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Daily activity — did anyone actually work, and did it land. */}
      <Card className="lg:col-span-7">
        <CardHeader>
          <CardTitle className="text-base">Practice volume, last 14 days</CardTitle>
          <p className="text-xs text-muted-foreground">
            Evidence events per day across the cohort, correct against missed.
          </p>
        </CardHeader>
        <CardContent>
          {noActivity ? (
            <ChartSkeleton height={180} message="No practice recorded in this window.">
              <SampleActivityChart />
            </ChartSkeleton>
          ) : (
            <ChartContainer config={activityConfig} className="h-[180px] w-full">
              <BarChart data={activity} margin={{ left: -20, right: 8, top: 8 }}>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis
                  dataKey="label"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                  minTickGap={16}
                />
                <YAxis
                  allowDecimals={false}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="correct" stackId="a" fill="var(--brand-gold)" radius={[0, 0, 0, 0]} />
                <Bar dataKey="missed" stackId="a" fill="var(--brand-slate)" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ChartContainer>
          )}
        </CardContent>
      </Card>

      {/* Weakest skills — the reteach list, which is the most directly
          actionable thing on this page. */}
      <Card className="lg:col-span-5">
        <CardHeader>
          <CardTitle className="text-base">Weakest skills across the class</CardTitle>
          <p className="text-xs text-muted-foreground">
            Where a whole-class reteach would pay off most.
          </p>
        </CardHeader>
        <CardContent>
          {weakest.length === 0 ? (
            <EmptyState
              title="No skills mapped yet"
              description="Course content hasn't been tagged to the skill taxonomy. Run the ingest pass to seed this."
            />
          ) : noSkillEvidence ? (
            <ChartSkeleton
              height={210}
              message="No practice evidence yet on any skill. Once learners start attempts, the weakest ones surface here first."
            >
              <SampleWeakestChart />
            </ChartSkeleton>
          ) : (
            <ChartContainer
              config={{ estimate: { label: "Cohort mastery", color: "var(--brand-gold)" } }}
              className="h-[210px] w-full"
            >
              <BarChart
                data={weakest.map((s) => ({
                  ...s,
                  estimate: s.estimate ?? 0,
                  short: s.name.length > 18 ? `${s.name.slice(0, 17)}…` : s.name,
                }))}
                layout="vertical"
                margin={{ left: 0, right: 16 }}
              >
                <CartesianGrid horizontal={false} stroke="var(--border)" />
                <XAxis
                  type="number"
                  domain={[0, 1]}
                  tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                />
                <YAxis
                  type="category"
                  dataKey="short"
                  width={108}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 10.5, fill: "var(--foreground)" }}
                />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="estimate" radius={[0, 2, 2, 0]}>
                  {weakest.map((s) => (
                    <Cell key={s.skillId} fill={BAND_FILL[s.band] ?? "var(--band-none)"} />
                  ))}
                </Bar>
              </BarChart>
            </ChartContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
