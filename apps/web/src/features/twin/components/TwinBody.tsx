import { useState } from "react";
import { Flame, Target } from "lucide-react";
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

export function TwinBody({ twin }: { twin: Twin }) {
  const skills = twin.skills;
  const gamification = useGamification(twin.courseId);
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
      <div className="flex flex-wrap items-stretch gap-4">
        <Card className="flex min-w-56 flex-1 flex-col items-center justify-center gap-3 py-8">
          <MasteryRing estimate={twin.readiness} size={112} strokeWidth={8} label="Board readiness" />
          <div className="text-center">
            <p className="font-display text-sm font-semibold">Board readiness</p>
            <p className="text-xs text-muted-foreground">Rollup of mastery across skills</p>
          </div>
        </Card>

        <Card className="min-w-72 flex-1">
          <CardHeader>
            <CardTitle className="text-base">Mastery across skills</CardTitle>
          </CardHeader>
          <CardContent>
            <MasteryRadar skills={skills} pulseKey={twin.evidence.length} />
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-wrap items-stretch gap-4">
        {/* Module-by-module progress — the topic axis a student works in */}
        <Card className="min-w-64 flex-[2]">
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

        {/* Focus area — one point of view, not a data dump */}
        {focus ? (
          <Card className="min-w-64 flex-1">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Target className="size-4 text-brand-orange" aria-hidden />
                Focus area
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm font-semibold text-foreground">{focus.name}</p>
              <div className="flex items-center gap-2">
                <MasteryBand band={focus.band} />
                <span className="font-mono text-xs text-muted-foreground">
                  {focus.attempts > 0 ? `${focus.attempts}× practiced` : "not practiced yet"}
                </span>
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">
                {focus.estimate === null
                  ? "This skill has no evidence yet — one practice session starts its curve."
                  : "This is your lowest mastery right now — practice moves the needle most here."}
              </p>
            </CardContent>
          </Card>
        ) : null}

        {/* Streak + XP + badges — the same derived reward view as the header */}
        <Card className="min-w-52 flex-1">
          <CardHeader>
            <CardTitle className="text-base">Streak & XP</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-5">
              <div>
                <p className="flex items-center gap-1.5 font-display text-2xl font-semibold text-foreground">
                  <Flame
                    className={cn(
                      "size-5",
                      (gamification.data?.streakDays ?? 0) > 0
                        ? "text-brand-gold"
                        : "text-muted-foreground/50"
                    )}
                    aria-hidden
                  />
                  {gamification.data?.streakDays ?? 0}
                </p>
                <p className="text-[10.5px] uppercase tracking-wide text-muted-foreground">
                  day streak
                </p>
              </div>
              <div>
                <p className="font-display text-2xl font-semibold text-foreground">
                  {gamification.data?.xp ?? 0}
                </p>
                <p className="text-[10.5px] uppercase tracking-wide text-muted-foreground">XP</p>
              </div>
            </div>
            {gamification.data && gamification.data.badges.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 border-t pt-2.5">
                {gamification.data.badges.slice(0, 3).map((b) => (
                  <span
                    key={`${b.kind}-${b.label}`}
                    className="rounded-sm bg-brand-gold/15 px-1.5 py-0.5 text-[10px] font-semibold capitalize text-foreground"
                    title={`${b.kind} badge · ${b.tier}`}
                  >
                    {b.label}
                  </span>
                ))}
                {gamification.data.badges.length > 3 ? (
                  <span className="px-1 py-0.5 font-mono text-[10px] text-muted-foreground">
                    +{gamification.data.badges.length - 3} more
                  </span>
                ) : null}
              </div>
            ) : null}
          </CardContent>
        </Card>
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
