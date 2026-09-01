import { useCohortStats } from "@/features/instructor";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

// The KPI strip. Six numbers a teacher can read in one pass before they
// look at anything else: how many learners, how many are moving, where the
// cohort sits, whether practice is working, how much evidence exists, and
// how many AI proposals are waiting on them.
//
// Every tile pairs its number with what produced it. A dashboard number
// without a denominator is decoration — "72% engagement" means nothing,
// "18 of 24 active this week" means something a teacher can act on.

type Tone = "neutral" | "gold" | "orange" | "green" | "red";

const TONE_RING: Record<Tone, string> = {
  neutral: "bg-brand-slate",
  gold: "bg-brand-gold",
  orange: "bg-brand-orange",
  green: "bg-brand-green",
  red: "bg-destructive",
};

function StatTile({
  label,
  value,
  sub,
  tone = "neutral",
  help,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: Tone;
  help?: string;
}) {
  const body = (
    <div className="relative flex min-h-[116px] min-w-0 flex-col justify-center border bg-card px-5 py-4">
      <span
        className={cn("absolute inset-y-0 left-0 w-[3px]", TONE_RING[tone])}
        aria-hidden
      />
      <p className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-brand-slate">
        {label}
      </p>
      <p className="mt-1.5 font-display text-3xl font-semibold leading-none tabular-nums text-foreground">
        {value}
      </p>
      {sub ? (
        <p className="mt-1.5 truncate font-mono text-[11px] text-muted-foreground">{sub}</p>
      ) : null}
    </div>
  );

  if (!help) return body;
  return (
    <Tooltip>
      <TooltipTrigger asChild>{body}</TooltipTrigger>
      <TooltipContent className="max-w-64">{help}</TooltipContent>
    </Tooltip>
  );
}

function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${Math.round(value * 100)}%`;
}

export function CohortStats({ courseId }: { courseId: string }) {
  const { data, isLoading } = useCohortStats(courseId);

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[116px] w-full" />
        ))}
      </div>
    );
  }

  const activeShare = data.learners > 0 ? data.activeLearners / data.learners : 0;

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
      <StatTile
        label="Learners"
        value={String(data.learners)}
        sub={`${data.notStartedLearners} not started`}
        tone="neutral"
        help="Enrolled students only. Co-teachers and admins are excluded from the roster even if they have an enrollment row."
      />
      <StatTile
        label="Active this week"
        value={`${data.activeLearners}`}
        sub={`of ${data.learners} · ${Math.round(activeShare * 100)}%`}
        tone={activeShare >= 0.6 ? "green" : activeShare >= 0.3 ? "orange" : "red"}
        help="Produced at least one evidence event in the last 7 days."
      />
      <StatTile
        label="Cohort readiness"
        value={pct(data.cohortReadiness)}
        sub={`median ${pct(data.medianReadiness)}`}
        tone="gold"
        help="Blueprint-weighted rollup of mastery across every tracked skill. A heuristic estimate from evidence to date, not a grade prediction."
      />
      <StatTile
        label="Accuracy"
        value={pct(data.accuracy)}
        sub={`${data.evidenceCount} graded events`}
        tone={
          data.accuracy === null ? "neutral" : data.accuracy >= 0.7 ? "green" : data.accuracy >= 0.5 ? "orange" : "red"
        }
        help="Share of graded attempts answered correctly across the whole cohort."
      />
      <StatTile
        label="Skills covered"
        value={`${data.skillsCovered}/${data.skillsTracked}`}
        sub={`${data.hintsUsed} hints used`}
        tone="neutral"
        help="Approved skills with at least one learner's evidence against them. Uncovered skills have no measurement yet."
      />
      <StatTile
        label="Pending decisions"
        value={String(data.decisions.pending)}
        sub={`${data.decisions.approved} approved · ${data.decisions.rejected} declined`}
        tone={data.decisions.pending > 0 ? "orange" : "green"}
        help="AI recommendations proposed for individual learners. None of them reach a learner until you approve or modify them."
      />
    </div>
  );
}
