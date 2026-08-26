import { useHeatmap } from "@/features/instructor";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CornerBrackets } from "@/components/kala";
import type { MasteryBand } from "@/features/twin";

// Skills × Bloom's heatmap: rows are the cohort (and per-student), columns
// are skills grouped under their Bloom's level. Cells are mastery bands —
// color AND a short label (color is never the only signal). The structure
// (the Bloom's ladder as column groups) is the information.

const BLOOM_ORDER = ["remember", "understand", "apply", "analyze", "evaluate", "create"];

const BAND_META: Record<MasteryBand, { short: string; cell: string; label: string }> = {
  "no-evidence": { short: "–", cell: "bg-band-none text-band-none-fg", label: "No evidence" },
  developing: { short: "D", cell: "bg-band-developing text-band-developing-fg", label: "Developing" },
  proficient: { short: "P", cell: "bg-band-proficient text-band-proficient-fg", label: "Proficient" },
  mastered: { short: "M", cell: "bg-band-mastered text-band-mastered-fg", label: "Mastered" },
};

export function Heatmap({ courseId }: { courseId: string }) {
  const { data, isLoading, isError, refetch } = useHeatmap(courseId);

  if (isLoading) return <Skeleton className="h-80 w-full" />;
  if (isError || !data) {
    return (
      <EmptyState
        title="We could not load the heatmap"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  }

  if (data.skills.length === 0) {
    return (
      <EmptyState
        title="No skills mapped yet"
        description="Course content hasn't been tagged to the skill taxonomy. Run the ingest pass to seed the heatmap."
      />
    );
  }
  if (data.students.length === 0) {
    return (
      <EmptyState
        title="No students enrolled yet"
        description="The roster syncs from your LMS. Once students start the diagnostic, their mastery appears here."
      />
    );
  }

  // Column groups: skills bucketed by Bloom's level, in ladder order.
  const groups = BLOOM_ORDER.map((level) => ({
    level,
    skills: data.skills.filter((s) => (s.bloomLevel ?? "").toLowerCase() === level),
  })).filter((g) => g.skills.length > 0);
  const columns = `minmax(150px, 220px) repeat(${data.skills.length}, minmax(0, 1fr))`;

  const cellFor = (userId: string, skillId: string): (typeof data.cells)[number] | undefined =>
    data.cells.find((c) => c.userId === userId && c.skillId === skillId);

  return (
    <div className="relative border bg-card">
      <CornerBrackets />
      <div className="border-b px-5 py-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-display text-[19px] font-semibold text-foreground">
              Skills × Bloom's mastery
            </h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Cohort average across {data.students.length} students · pseudonyms shown
            </p>
          </div>
          <div className="flex items-center gap-4">
            {(["no-evidence", "developing", "proficient", "mastered"] as MasteryBand[]).map(
              (band) => (
                <span key={band} className="flex items-center gap-1.5">
                  <span className={`inline-block size-3 rounded-[2px] border border-primary/15 ${BAND_META[band].cell}`} />
                  <span className="text-[11.5px] text-brand-slate">{BAND_META[band].label}</span>
                </span>
              )
            )}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <div className="grid min-w-[640px]" style={{ gridTemplateColumns: columns }}>
          {/* column headers: Bloom's levels spanning their skills */}
          <div className="border-b border-r border-border" />
          {groups.map((g) => (
            <div
              key={g.level}
              style={{ gridColumn: `span ${g.skills.length}` }}
              className="flex flex-col items-center gap-1 border-b border-r border-border px-2 py-2.5 last:border-r-0"
            >
              <span className="grid size-4 place-items-center rounded-full bg-brand-slate font-mono text-[9px] font-bold text-background">
                {BLOOM_ORDER.indexOf(g.level) + 1}
              </span>
              <span className="text-[11.5px] font-semibold capitalize text-foreground">
                {g.level}
              </span>
            </div>
          ))}

          {/* cohort row */}
          <div className="flex items-center border-b border-r border-border px-4 py-2.5 text-[13px] font-semibold text-foreground">
            Cohort
          </div>
          {data.skills.map((s) => {
            const meta = BAND_META[s.cohortBand];
            return (
              <div
                key={s.skillId}
                title={`${s.name} — ${meta.label}`}
                className={`grid h-11 items-center justify-center border-b border-r border-border font-mono text-[13px] font-bold last:border-r-0 ${meta.cell}`}
              >
                {meta.short}
              </div>
            );
          })}

          {/* per-student rows */}
          {data.students.map((stu) => (
            <div key={stu.userId} className="contents">
              <div className="flex items-center gap-2 border-b border-r border-border px-4 py-2.5">
                <span className="text-[13px] font-medium text-foreground">{stu.pseudonym}</span>
              </div>
              {data.skills.map((s) => {
                const cell = cellFor(stu.userId, s.skillId);
                const meta = BAND_META[cell?.band ?? "no-evidence"];
                return (
                  <div
                    key={s.skillId}
                    title={`${stu.pseudonym} — ${s.name}: ${meta.label}`}
                    className={`grid h-11 items-center justify-center border-b border-r border-border font-mono text-[13px] font-bold last:border-r-0 ${meta.cell}`}
                  >
                    {meta.short}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
