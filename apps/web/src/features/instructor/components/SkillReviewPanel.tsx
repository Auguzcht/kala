import { useProposeSkills, useProposedSkills, useReviewProposedSkill, type ProposeSkillsResult } from "@/features/instructor";
import { CornerBrackets } from "@/components/kala";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

// HITL skill proposals (docs/SKILL_PIPELINE.md). AI proposes skills from
// the course's content, one module at a time; nothing proposed reaches
// learners until a human approves here. The "Refresh skills" button in the
// header is the on-demand trigger (docs/DEEPSEEK_REFRESH_BUTTON.md): it's
// incremental by module, safe to press any number of times, and only
// processes modules that don't have skills yet — so it's also the recovery
// path when a first launch produced nothing. Result messaging is honest:
// a skipped run says why, never a silent no-op.

function RefreshStatus({
  isPending,
  isError,
  isSuccess,
  data,
}: {
  isPending: boolean;
  isError: boolean;
  isSuccess: boolean;
  data?: ProposeSkillsResult;
}) {
  if (isPending) {
    return (
      <p className="mt-3 text-xs text-muted-foreground">
        Proposing — one model call per module, this can take a few seconds…
      </p>
    );
  }
  if (isError) {
    return (
      <p className="mt-3 text-xs text-destructive">
        Refresh failed — check the API log and try again.
      </p>
    );
  }
  if (isSuccess && data) {
    const processed = data.modulesProcessed ?? 0;
    if (data.skipped || processed === 0) {
      return (
        <p className="mt-3 text-xs text-muted-foreground">
          All modules already have skills — nothing new to propose.
        </p>
      );
    }
    return (
      <p className="mt-3 text-xs text-muted-foreground">
        Processed {processed} new module{processed === 1 ? "" : "s"}, {data.proposed ?? 0} skill
        {(data.proposed ?? 0) === 1 ? "" : "s"} ready for review
        {data.auto_approved ? `, ${data.auto_approved} auto-matched from another course` : ""}.
      </p>
    );
  }
  return null;
}

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

  return (
    <div className="relative border bg-card">
      <CornerBrackets />
      <div className="flex flex-wrap items-center gap-3 border-b px-5 py-4">
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-[16px] font-semibold text-foreground">
            Skill proposals
          </h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            AI-drafted from this course's content, one module at a time. Approve to make them
            live for learners.
          </p>
        </div>
        {proposed.length > 0 ? (
          <span className="rounded-full bg-brand-orange/15 px-2.5 py-0.5 font-mono text-[11.5px] font-bold text-brand-orange-foreground">
            {proposed.length} pending
          </span>
        ) : null}
        <Button
          variant="outline"
          size="sm"
          disabled={propose.isPending}
          onClick={() => propose.mutate()}
        >
          {propose.isPending ? "Refreshing…" : "Refresh skills"}
        </Button>
      </div>

      {proposed.length === 0 ? (
        <div className="px-5 py-6">
          <p className="text-[13px] text-muted-foreground">
            No proposals pending. If this course hasn't been through proposal yet — or a launch
            only produced a partial result — press Refresh skills to draft the missing modules.
          </p>
          <RefreshStatus
            isPending={propose.isPending}
            isError={propose.isError}
            isSuccess={propose.isSuccess}
            data={propose.data}
          />
        </div>
      ) : (
        <div className="divide-y divide-border">
          <div className="px-5 pt-3">
            <RefreshStatus
              isPending={propose.isPending}
              isError={propose.isError}
              isSuccess={propose.isSuccess}
              data={propose.data}
            />
          </div>
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
      )}
    </div>
  );
}
