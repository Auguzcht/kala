import { useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { useAtRisk, useLearnerRecord } from "@/features/instructor";
import { DecisionCenter } from "@/features/instructor/components/DecisionCenter";
import { LearnerStanding } from "@/features/instructor/components/LearnerStanding";
import { MasteryBand, MasteryRadar, MasteryRing, EvidenceLedger } from "@/components/kala";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/shared/EmptyState";

// The full learner record — the deep dive. This is NOT the student's twin
// with a different header on it, which is what it used to be, and it is
// deliberately different from the triage sheet (LearnerTriage): the sheet
// answers "what do I decide for this learner right now", this page answers
// "what is this learner's full picture". The mastery instruments live here
// where there is room for them; the sheet keeps only the standing block
// and the decision.

const trendConfig = {
  readiness: { label: "Readiness", color: "var(--brand-gold)" },
} satisfies ChartConfig;

const activityConfig = {
  correct: { label: "Correct", color: "var(--brand-gold)" },
  missed: { label: "Missed", color: "var(--brand-slate)" },
} satisfies ChartConfig;

function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${Math.round(value * 100)}%`;
}

function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function LearnerRecord({
  courseId,
  userId,
}: {
  courseId: string;
  userId: string;
}) {
  const record = useLearnerRecord(courseId, userId);
  const atRisk = useAtRisk(courseId);
  const [deidentified, setDeidentified] = useState(false);

  if (record.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (record.isError || !record.data) {
    return (
      <EmptyState
        title="We could not load this learner's record"
        description="Check your connection and try again."
        action={
          <Button variant="outline" onClick={() => record.refetch()}>
            Retry
          </Button>
        }
      />
    );
  }

  const r = record.data;
  const name = deidentified ? r.pseudonym : r.displayName;
  const flag = atRisk.data?.flags.find((f) => f.userId === userId);
  const trend = r.readinessTrend.map((t) => ({ ...t, label: shortDate(t.date) }));
  const activity = r.activitySeries.map((a) => ({ ...a, label: shortDate(a.date) }));
  const weakest = [...r.skills]
    .sort((a, b) => (a.estimate ?? -1) - (b.estimate ?? -1))
    .slice(0, 5);

  return (
    <div className="space-y-5">
      <LearnerStanding
        userId={userId}
        record={r}
        flag={flag}
        deidentified={deidentified}
        onDeidentifiedChange={setDeidentified}
      />

      <Tabs defaultValue="decide">
        <TabsList>
          <TabsTrigger value="decide">Decide</TabsTrigger>
          <TabsTrigger value="mastery">Mastery</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>

        {/* Decide first, deliberately. The teacher came here to do
            something, not to admire a radar chart. */}
        <TabsContent value="decide" className="mt-4">
          <DecisionCenter courseId={courseId} userId={userId} learnerName={name} />
        </TabsContent>

        <TabsContent value="mastery" className="mt-4 space-y-4">
          <div className="grid gap-4 lg:grid-cols-12">
            <Card className="flex flex-col items-center justify-center gap-3 py-8 lg:col-span-4">
              <MasteryRing estimate={r.readiness} size={144} strokeWidth={11} label="Readiness" />
              <p className="text-center text-xs text-muted-foreground">
                Blueprint-weighted rollup across {r.skills.length} tracked skills
              </p>
            </Card>
            <Card className="lg:col-span-8">
              <CardHeader>
                <CardTitle className="text-base">Mastery across skills</CardTitle>
              </CardHeader>
              <CardContent>
                <MasteryRadar skills={r.skills} className="mx-auto max-w-md" />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Where to intervene</CardTitle>
              <p className="text-xs text-muted-foreground">
                Weakest first. Never-attempted skills rank weakest of all, matching how the learner's
                own next-up is picked.
              </p>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {weakest.length === 0 ? (
                <p className="py-4 text-sm text-muted-foreground">No skills mapped yet.</p>
              ) : (
                weakest.map((s) => (
                  <div key={s.skillId} className="flex items-center gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13px] font-medium text-foreground">{s.name}</p>
                      <p className="text-[10.5px] uppercase tracking-wide text-muted-foreground">
                        {s.bloomLevel ?? "unmapped"} · {s.attempts} attempt
                        {s.attempts === 1 ? "" : "s"}
                      </p>
                    </div>
                    <div className="h-1.5 w-20 shrink-0 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-brand-gold"
                        style={{ width: `${Math.round((s.estimate ?? 0) * 100)}%` }}
                      />
                    </div>
                    <span className="w-9 shrink-0 text-right font-mono text-xs tabular-nums text-muted-foreground">
                      {pct(s.estimate)}
                    </span>
                    <MasteryBand band={s.band} />
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity" className="mt-4 space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Readiness over time</CardTitle>
              </CardHeader>
              <CardContent>
                {trend.length < 2 ? (
                  <p className="py-10 text-center text-xs text-muted-foreground">
                    Not enough snapshots yet to draw a trend.
                  </p>
                ) : (
                  <ChartContainer config={trendConfig} className="h-[160px] w-full">
                    <AreaChart data={trend} margin={{ left: -20, right: 8, top: 8 }}>
                      <defs>
                        <linearGradient id={`fill-${userId}`} x1="0" y1="0" x2="0" y2="1">
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
                        fill={`url(#fill-${userId})`}
                      />
                    </AreaChart>
                  </ChartContainer>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Practice, last 14 days</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartContainer config={activityConfig} className="h-[160px] w-full">
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
                    <Bar dataKey="correct" stackId="a" fill="var(--brand-gold)" />
                    <Bar dataKey="missed" stackId="a" fill="var(--brand-slate)" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ChartContainer>
                {r.activityByType.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-1.5 border-t pt-3">
                    {r.activityByType.map((a) => (
                      <span
                        key={a.type}
                        className="rounded-sm bg-muted px-1.5 py-0.5 text-[10.5px] capitalize text-muted-foreground"
                      >
                        {a.type} · {a.count}
                      </span>
                    ))}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Evidence ledger</CardTitle>
              <p className="text-xs text-muted-foreground">
                Append-only. Every recommendation on the Decide tab traces back to these rows.
              </p>
            </CardHeader>
            <CardContent>
              <EvidenceLedger events={r.evidence} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
