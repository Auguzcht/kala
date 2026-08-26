import { useProposeSkills, useProposedSkills, useReviewProposedSkill } from "@/features/instructor";
import { CornerBrackets } from "@/components/kala";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

// HITL skill proposals (docs/SKILL_PIPELINE.md). AI proposes skills from
// the course's content on first instructor launch; nothing proposed reaches
// learners until a human approves here. A workflow surface, built bespoke —
// one reviewable list, Approve/Reject per row, the "possible duplicate"
// note shown prominently (it's the reviewer's main signal).

export function SkillReviewPanel({ courseId }: { courseId: string }) {
  const { data, isLoading, isError, refetch } = useProposedSkills(courseId);
  const review = useReviewProposedSkill(courseId);
  const propose = useProposeSkills(courseId);

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-5 w-56" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (isError && !data) {
    return (
      <div className="border bg-card p-5">
        <p className="text-sm font-semibold text-foreground">Skill proposals</p>
        <p className="mt-1 text-xs text-muted-foreground">
          We could not load pending proposals.
        </p>
        <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  const proposed = data?.proposed ?? [];

  // Empty steady state: the trigger for the FIRST proposal run, on demand,
  // no relaunch needed (docs/DEEPSEEK_ONDEMAND_PROPOSAL.md). modulesProcessed
  // is the demo-day sanity check that every module was actually seen.
  if (proposed.length === 0) {
    return (
      <div className="relative border bg-card">
        <CornerBrackets />
        <div className="flex items-center justify-between border-b px-5 py-4">
          <div>
            <h2 className="font-display text-[16px] font-semibold text-foreground">
              Skill proposals
            </h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              AI-draft this course's skills from its content, one module at a time.
            </p>
          </div>
        </div>
        <div className="px-5 py-6">
          <Button
            variant="default"
            size="sm"
            disabled={propose.isPending}
            onClick={() => propose.mutate()}
          >
            {propose.isPending ? "Proposing…" : "Run skill proposal"}
          </Button>
          {propose.isError ? (
            <p className="mt-3 text-xs text-destructive">
              Proposal failed. Check the API log and try again.
            </p>
          ) : null}
          {propose.isSuccess ? (
            <p className="mt-3 text-xs text-muted-foreground">
              {propose.data.skipped
                ? "This course already has skills — nothing to propose. Delete existing rows to re-run from scratch."
                : `Processed ${propose.data.modulesProcessed ?? 0} modules, ${propose.data.proposed ?? 0} proposals ready for review`}
            </p>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="relative border bg-card">
      <CornerBrackets />
      <div className="flex items-center justify-between border-b px-5 py-4">
        <div>
          <h2 className="font-display text-[16px] font-semibold text-foreground">
            Skill proposals
          </h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            AI-drafted skills from this course's content. Approve to make them live for learners.
          </p>
        </div>
        <span className="rounded-full bg-brand-orange/15 px-2.5 py-0.5 font-mono text-[11.5px] font-bold text-brand-orange-foreground">
          {proposed.length} pending
        </span>
      </div>

      <div className="divide-y divide-border">
        {proposed.map((s) => {
          const isDuplicate = (s.proposed_source ?? "").startsWith("possible duplicate");
          return (
            <div key={s.id} className="flex flex-wrap items-center gap-3 px-5 py-4">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-[13.5px] font-semibold text-foreground">{s.name}</p>
                  <span className="rounded-sm border border-border bg-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                    {s.bloom_level}
                  </span>
                  <span className="font-mono text-[11px] text-muted-foreground">
                    weight {s.blueprint_weight}
                  </span>
                </div>
                {s.proposed_source ? (
                  <p
                    className={
                      isDuplicate
                        ? "mt-1.5 text-xs font-medium text-brand-orange-foreground"
                        : "mt-1.5 text-xs text-muted-foreground"
                    }
                  >
                    {isDuplicate ? "⚠ " : ""}
                    {s.proposed_source}
                  </p>
                ) : null}
              </div>
              <div className="flex shrink-0 gap-2">
                <Button
                  variant="green"
                  size="sm"
                  disabled={review.isPending}
                  onClick={() => review.mutate({ skillId: s.id, status: "approved" })}
                >
                  Approve
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={review.isPending}
                  onClick={() => review.mutate({ skillId: s.id, status: "rejected" })}
                >
                  Reject
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
