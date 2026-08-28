import { useState } from "react";
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
import type { Twin, TwinSkill } from "@/features/twin";
import { MasteryBand, BloomsLadder, EvidenceLedger, MasteryRing, MasteryRadar } from "@/components/kala";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

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
  const ranked = [...skills].sort((a, b) => {
    const aNull = a.estimate === null ? -1 : a.estimate;
    const bNull = b.estimate === null ? -1 : b.estimate;
    return aNull - bNull;
  });

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
                      <span className="capitalize">{g.level}</span>
                      <span className="ml-2 font-mono text-xs text-muted-foreground">
                        {g.skills.length}
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
