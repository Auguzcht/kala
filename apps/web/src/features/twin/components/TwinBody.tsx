import { useEffect, useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { FlameIcon } from "@/components/ui/flame";
import type { FlameIconHandle } from "@/components/ui/flame";
import { ZapIcon } from "@/components/ui/zap";
import { Bar, BarChart, CartesianGrid, XAxis } from "recharts";
import { InView } from "@/components/motion/in-view";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { Button } from "@/components/ui/button";
import { useGamification } from "@/features/gamification";
import type { Twin, TwinSkill } from "@/features/twin";
import { MasteryBand, BloomsLadder, EvidenceLedger, MasteryRing, MasteryRadar } from "@/components/kala";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

// Presentational twin body: readiness gauge, mastery radar, skills grouped
// by Bloom level with pagination, Bloom's ladder, and the append-only
// evidence ledger. Shared by the student's own twin (/course/twin) and the
// instructor's per-student drill-down (/class/student/:uid).

const BLOOM_ORDER = [
  "remember",
  "understand",
  "apply",
  "analyze",
  "evaluate",
  "create",
];

const PAGE_SIZE = 8;

// Recent activity — a real graph built from the same evidence the ledger
// already shows below, not decorative data. Buckets the (capped, most
// recent) evidence events by calendar day and splits correct vs. missed, so
// the shape of a study session is visible at a glance instead of only as a
// scrolling log. The API caps evidence at the 20 most recent events, so on
// a very active day this undercounts rather than overcounts — acceptable
// for an at-a-glance trend, called out in the label below the chart.
function activityByDay(evidence: Twin["evidence"]) {
  const byDay = new Map<string, { correct: number; missed: number; label: string }>();
  for (const e of evidence) {
    if (!e.createdAt) continue;
    const d = new Date(e.createdAt);
    const key = d.toISOString().slice(0, 10);
    const label = d.toLocaleDateString(undefined, { weekday: "short" });
    const bucket = byDay.get(key) ?? { correct: 0, missed: 0, label };
    if (e.correct === true) bucket.correct += 1;
    else if (e.correct === false) bucket.missed += 1;
    byDay.set(key, bucket);
  }
  // Oldest to newest, left to right, matching how a week reads.
  return [...byDay.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, v]) => v);
}

const activityChartConfig = {
  correct: { label: "Correct", color: "var(--brand-gold)" },
  missed: { label: "Missed", color: "var(--border)" },
} satisfies ChartConfig;

function ActivityChart({ evidence }: { evidence: Twin["evidence"] }) {
  const data = activityByDay(evidence);
  if (data.length === 0) {
    return (
      <p className="py-6 text-center text-xs text-muted-foreground">
        No recent activity yet — it fills in as you study.
      </p>
    );
  }
  return (
    <div>
      <ChartContainer config={activityChartConfig} className="h-[120px] w-full">
        <BarChart data={data} barGap={2}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
          />
          <ChartTooltip content={<ChartTooltipContent />} />
          <Bar dataKey="correct" stackId="a" fill="var(--brand-gold)" radius={[2, 2, 0, 0]} />
          <Bar dataKey="missed" stackId="a" fill="var(--border)" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ChartContainer>
      <p className="mt-1 text-[10.5px] text-muted-foreground">
        Last {evidence.length} events, most recent activity
      </p>
    </div>
  );
}

function SkillGroupList({ skills }: { skills: TwinSkill[] }) {
  const [page, setPage] = useState(0);
  const pages = Math.max(1, Math.ceil(skills.length / PAGE_SIZE));
  const slice = skills.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div className="space-y-1">
      {slice.map((s) => (
        <div
          key={s.skillId}
          className="flex items-center gap-3 rounded-sm px-2 py-2 hover:bg-accent/50"
          title={
            s.estimate === null
              ? undefined
              : `Estimate ${Math.round(s.estimate * 100)}% · ${s.attempts} attempt${s.attempts === 1 ? "" : "s"}`
          }
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

      {pages > 1 ? (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                className={page === 0 ? "pointer-events-none opacity-40" : undefined}
              />
            </PaginationItem>
            {Array.from({ length: pages }).map((_, i) => (
              <PaginationItem key={i}>
                <PaginationLink
                  isActive={i === page}
                  onClick={() => setPage(i)}
                >
                  {i + 1}
                </PaginationLink>
              </PaginationItem>
            ))}
            <PaginationItem>
              <PaginationNext
                onClick={() => setPage((p) => Math.min(pages - 1, p + 1))}
                className={page >= pages - 1 ? "pointer-events-none opacity-40" : undefined}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      ) : null}
    </div>
  );
}

export function TwinBody({ twin, own = true }: { twin: Twin; own?: boolean }) {
  const navigate = useNavigate();
  const skills = twin.skills;
  // The streak/XP tile and the "Practice this" CTA are OWNER-scoped: they
  // read the signed-in user's gamification and navigate them into their own
  // practice. The instructor drill-down renders this same body for a
  // student's twin — for that viewer those two tiles would show the
  // instructor's own numbers and navigate them somewhere wrong, so they're
  // suppressed unless `own` (the student's own /course/twin). The hook
  // itself stays unconditional (rules of hooks); the fetch is harmless and
  // cached, only the render is gated.
  const gamification = useGamification(twin.courseId);

  // Flame draws once when the streak actually increases (real state change).
  const streakFlameRef = useRef<FlameIconHandle | null>(null);
  const prevStreakRef = useRef<number | null>(null);
  useEffect(() => {
    const s = gamification.data?.streakDays ?? 0;
    if (prevStreakRef.current !== null && s > prevStreakRef.current) {
      streakFlameRef.current?.startAnimation();
    }
    prevStreakRef.current = s;
  }, [gamification.data?.streakDays]);
  const ranked = [...skills].sort((a, b) => {
    const aNull = a.estimate === null ? -1 : a.estimate;
    const bNull = b.estimate === null ? -1 : b.estimate;
    return aNull - bNull;
  });

  // Module rollup: average mastery per module_ref (mirrors the radar's
  // aggregation, but along the topic axis the learner actually works in).
  const modules = new Map<string, { total: number; count: number; attempts: number }>();
  for (const s of skills) {
    const key = s.moduleRef?.trim() || "Other topics";
    const m = modules.get(key) ?? { total: 0, count: 0, attempts: 0 };
    m.total += s.estimate ?? 0;
    m.count += 1;
    m.attempts += s.attempts;
    modules.set(key, m);
  }
  const moduleRows = [...modules.entries()]
    .map(([name, m]) => ({ name, avg: m.count > 0 ? m.total / m.count : 0, count: m.count }))
    .sort((a, b) => a.name.localeCompare(b.name));

  // Focus area: the weakest skill, mirroring the server's weakest_skill
  // rule (never-attempted ranks weakest of all).
  const focus = [...skills].sort(
    (a, b) => (a.estimate ?? -1) - (b.estimate ?? -1)
  )[0];

  const groups = BLOOM_ORDER.map((level) => ({
    level,
    skills: ranked.filter((s) => (s.bloomLevel ?? "").toLowerCase() === level),
  })).filter((g) => g.skills.length > 0);
  const untyped = ranked.filter((s) => !BLOOM_ORDER.includes((s.bloomLevel ?? "").toLowerCase()));
  if (untyped.length > 0) groups.push({ level: "other", skills: untyped });

  return (
    <div className="space-y-6">
      {/*
        A genuine bento grid, not flex-1 equal-stretch: explicit column spans
        so the readiness ring and radar — the two signature instruments —
        get real weight, and the four supporting tiles below don't all
        inflate to match whichever one happens to be tallest. 12-column base
        so spans divide cleanly; collapses to a single column on mobile.
      */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-12">
        <Card className="flex flex-col items-center justify-center gap-4 py-10 md:col-span-4" id="tour-twin-readiness">
          <MasteryRing estimate={twin.readiness} size={176} strokeWidth={12} label="Board readiness" />
          <div className="text-center">
            <p className="font-display text-base font-semibold">Board readiness</p>
            <p className="mt-1 text-xs text-muted-foreground">Rollup of mastery across skills</p>
            <p className="mt-3 font-mono text-[11px] text-muted-foreground">
              {twin.evidence.length > 0
                ? `${twin.evidence.length} recent event${twin.evidence.length === 1 ? "" : "s"} feeding this estimate`
                : "Fills in as you study"}
            </p>
          </div>
        </Card>

        <Card id="tour-twin-radar" className="md:col-span-8">
          <CardHeader>
            <CardTitle className="text-base">Mastery across skills</CardTitle>
          </CardHeader>
          <CardContent>
            <MasteryRadar
              skills={skills}
              pulseKey={twin.evidence.length}
              className="mx-auto max-w-lg"
            />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-12">
        <Card className="md:col-span-5" id="tour-twin-activity">
          <CardHeader>
            <CardTitle className="text-base">Progress by module</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {moduleRows.length === 0 ? (
              <p className="py-4 text-sm text-muted-foreground">
                No modules mapped yet.
              </p>
            ) : (
              moduleRows.map((m) => (
                <div key={m.name} className="space-y-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="truncate text-[13px] font-medium text-foreground">
                      {m.name}
                    </span>
                    <span className="shrink-0 font-mono text-xs text-muted-foreground">
                      {Math.round(m.avg * 100)}% · {m.count} skill{m.count === 1 ? "" : "s"}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        m.avg > 0 ? "bg-brand-gold" : "bg-border"
                      )}
                      style={{ width: `${Math.min(100, Math.round(m.avg * 100))}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="md:col-span-7">
          <CardHeader>
            <CardTitle className="text-base">Recent activity</CardTitle>
          </CardHeader>
          <CardContent>
            <ActivityChart evidence={twin.evidence} />
          </CardContent>
        </Card>

        {/* Focus area — one point of view, not a data dump, now with a
            direct path to act on it instead of just describing it. */}
        {focus ? (
          <Card className={own ? "md:col-span-7" : "md:col-span-12"}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ZapIcon size={16} className="text-brand-orange" aria-hidden />
                Focus area
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm font-semibold text-foreground">{focus.name}</p>
                <div className="mt-1.5 flex items-center gap-2">
                  <MasteryBand band={focus.band} />
                  <span className="font-mono text-xs text-muted-foreground">
                    {focus.attempts > 0 ? `${focus.attempts}× practiced` : "not practiced yet"}
                  </span>
                </div>
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">
                {focus.estimate === null
                  ? "This skill has no evidence yet — one practice session starts its curve."
                  : "This is your lowest mastery right now — practice moves the needle most here."}
              </p>
              {own ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate({ to: "/course/practice" })}
                >
                  Practice this <ArrowRightIcon size={14} />
                </Button>
              ) : null}
            </CardContent>
          </Card>
        ) : null}

        {own ? (
          <Card className="md:col-span-5">
            <CardHeader>
              <CardTitle className="text-base">Streak & XP</CardTitle>
            </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-6">
              <div>
                <div className="flex items-center gap-1.5 font-display text-3xl font-semibold text-foreground">
                  <FlameIcon
                    ref={streakFlameRef}
                    size={24}
                    className={
                      (gamification.data?.streakDays ?? 0) > 0
                        ? "text-brand-gold"
                        : "text-muted-foreground/50"
                    }
                    aria-hidden
                  />
                  {gamification.data?.streakDays ?? 0}
                </div>
                <p className="text-[10.5px] uppercase tracking-wide text-muted-foreground">
                  day streak
                </p>
              </div>
              <div>
                <p className="font-display text-3xl font-semibold text-foreground">
                  {gamification.data?.xp ?? 0}
                </p>
                <p className="text-[10.5px] uppercase tracking-wide text-muted-foreground">XP</p>
              </div>
              {gamification.data ? (
                <div>
                  <p className="font-display text-3xl font-semibold text-foreground">
                    {gamification.data.correct}
                    <span className="text-base font-medium text-muted-foreground">
                      /{gamification.data.attempts}
                    </span>
                  </p>
                  <p className="text-[10.5px] uppercase tracking-wide text-muted-foreground">
                    correct
                  </p>
                </div>
              ) : null}
            </div>
            {gamification.data && gamification.data.badges.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 border-t pt-3">
                {gamification.data.badges.map((b) => (
                  <span
                    key={`${b.kind}-${b.label}`}
                    className="rounded-sm bg-brand-gold/15 px-1.5 py-0.5 text-[10px] font-semibold capitalize text-foreground"
                    title={`${b.kind} badge · ${b.tier}`}
                  >
                    {b.label}
                  </span>
                ))}
              </div>
            ) : (
              <p className="border-t pt-3 text-xs text-muted-foreground">
                Badges appear here as skills and Bloom's levels reach proficient.
              </p>
            )}
          </CardContent>
          </Card>
        ) : null}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Skills</CardTitle>
        </CardHeader>
        <CardContent>
          {groups.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No skills mapped for this course yet.
            </p>
          ) : (
            <InView
              once
              variants={{ hidden: { opacity: 0, y: 8 }, visible: { opacity: 1, y: 0 } }}
              transition={{ duration: 0.35 }}
            >
              <Accordion type="multiple" defaultValue={groups.map((g) => g.level)} className="w-full">
                {groups.map((g) => (
                  <AccordionItem key={g.level} value={g.level}>
                    <AccordionTrigger>
                      <span className="flex items-center gap-1.5">
                        <span className="capitalize">{g.level}</span>
                        <span className="font-mono text-xs text-muted-foreground">
                          {g.skills.length}
                        </span>
                      </span>
                    </AccordionTrigger>
                    <AccordionContent>
                      <SkillGroupList skills={g.skills} />
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </InView>
          )}
        </CardContent>
      </Card>

      <BloomsLadder skills={skills} />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Evidence ledger</CardTitle>
        </CardHeader>
        <CardContent>
          <EvidenceLedger events={twin.evidence} />
        </CardContent>
      </Card>
    </div>
  );
}
