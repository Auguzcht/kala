import type { Twin } from "@/features/twin";
import { MasteryBand, BloomsLadder, EvidenceLedger, MasteryRing, MasteryRadar } from "@/components/kala";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// Presentational twin body: readiness gauge, mastery radar, skills with
// qualitative bands, Bloom's ladder, and the append-only evidence ledger.
// Shared by the student's own twin (/course/twin) and the instructor's
// per-student drill-down (/class/student/:uid).

export function TwinBody({ twin }: { twin: Twin }) {
  const skills = twin.skills;
  const ranked = [...skills].sort((a, b) => {
    const aNull = a.estimate === null ? -1 : a.estimate;
    const bNull = b.estimate === null ? -1 : b.estimate;
    return aNull - bNull;
  });

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
            <MasteryRadar skills={skills} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Skills</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {ranked.map((s) => (
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
          {ranked.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No skills mapped for this course yet.
            </p>
          ) : null}
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
