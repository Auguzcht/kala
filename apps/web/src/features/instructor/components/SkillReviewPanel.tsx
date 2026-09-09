import { useRef, useState } from "react";
import { useProposeSkills, useProposedSkills, useReviewProposedSkill, type ProposeSkillsResult } from "@/features/instructor";
import { CornerBrackets } from "@/components/kala";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Skeleton } from "@/components/ui/skeleton";
import { TriangleAlertIcon } from "lucide-react";
import { CheckIcon, type CheckIconHandle } from "@/components/ui/check";
import { XIcon, type XIconHandle } from "@/components/ui/x";
import { SparklesIcon, type SparklesIconHandle } from "@/components/ui/sparkles";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { pageWindow } from "@/lib/pagination";

// A course's proposal queue can run to dozens of rows (this course has 32)
// once every module's draft lands — a flat list pushes the first page of
// reviews below the fold and hides how much queue is actually waiting.
// Same pagination as the roster: 8 per page, windowed page links, and a
// "1–8 of 32" range line so the queue length is always visible.
const PAGE_SIZE = 8;

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
        {data.auto_approved ? `, ${data.auto_approved} auto-matched from another course` : ""}
        {data.insertFailed ? `, ${data.insertFailed} failed to save — press Refresh to retry` : ""}.
      </p>
    );
  }
  return null;
}

// Per-row decision buttons. Own refs so EVERY row's icons animate on its
// own button hover (a shared ref would make all rows drive the last-mounted
// icon). The check draws on Approve's hover, the x on Reject's; clicking
// still fires the same mutation the panel drives.
function ReviewActions({
  disabled,
  isFirst,
  onApprove,
  onReject,
}: {
  disabled: boolean;
  isFirst: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  const checkRef = useRef<CheckIconHandle | null>(null);
  const xRef = useRef<XIconHandle | null>(null);
  return (
    <div className="flex shrink-0 items-center justify-end gap-1.5">
      <Button
        id={isFirst ? "tour-skill-approve" : undefined}
        variant="green"
        size="sm"
        disabled={disabled}
        onClick={onApprove}
        onMouseEnter={() => checkRef.current?.startAnimation()}
        onMouseLeave={() => checkRef.current?.stopAnimation()}
        className="h-7 px-2.5 text-[12px] [&_svg]:size-3"
      >
        <CheckIcon ref={checkRef} size={13} /> Approve
      </Button>
      <Button
        variant="outline"
        size="sm"
        disabled={disabled}
        onClick={onReject}
        onMouseEnter={() => xRef.current?.startAnimation()}
        onMouseLeave={() => xRef.current?.stopAnimation()}
        className="h-7 px-2.5 text-[12px] [&_svg]:size-3"
      >
        <XIcon ref={xRef} size={13} /> Reject
      </Button>
    </div>
  );
}

export function SkillReviewPanel({ courseId }: { courseId: string }) {
  const { data, isLoading, isError, refetch } = useProposedSkills(courseId);
  const review = useReviewProposedSkill(courseId);
  const propose = useProposeSkills(courseId);
  const [page, setPage] = useState(0);
  // Animated icons: the check/x/sparkle draw when their BUTTON is hovered
  // (controlled-mode handlers), same as the decision buttons elsewhere.
  const refreshRef = useRef<SparklesIconHandle | null>(null);

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
  const pages = Math.max(1, Math.ceil(proposed.length / PAGE_SIZE));
  const safePage = Math.min(page, pages - 1);
  const slice = proposed.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  return (
    <div className="relative border bg-card" id="tour-skill-review-panel">
      <CornerBrackets />
      <div className="flex flex-wrap items-center gap-3 border-b px-5 py-4">
        <div className="min-w-0">
          <h2 className="font-display text-[19px] font-semibold text-foreground">
            Skill proposals
          </h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {proposed.length} pending · AI-drafted from this course's content, one module at a
            time. Approve to make them live for learners.
          </p>
        </div>
        <div className="flex-1" />
        <Button
          variant="orange"
          size="sm"
          disabled={propose.isPending}
          onClick={() => propose.mutate()}
          onMouseEnter={() => refreshRef.current?.startAnimation()}
          onMouseLeave={() => refreshRef.current?.stopAnimation()}
          className="h-8 px-3 text-[12.5px] [&_svg]:size-3.5"
        >
          {propose.isPending ? (
            <>
              <Spinner className="size-3.5" /> Refreshing…
            </>
          ) : (
            <>
              <SparklesIcon ref={refreshRef} size={13} /> Refresh skills
            </>
          )}
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
        <>
          <div className="px-5 pt-3">
            <RefreshStatus
              isPending={propose.isPending}
              isError={propose.isError}
              isSuccess={propose.isSuccess}
              data={propose.data}
            />
          </div>
          {/* Roster-scale table: same Table primitives, cell padding, and
              font sizes as the class roster, so the review queue reads as
              part of the same instrument. */}
          <Table className="table-fixed">
            <colgroup>
              <col className="w-[42%]" />
              <col className="w-[38%]" />
              <col className="w-[20%]" />
            </colgroup>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-[11px] uppercase tracking-[0.05em]">
                  Proposed skill
                </TableHead>
                <TableHead className="text-[11px] uppercase tracking-[0.05em]">
                  Source
                </TableHead>
                <TableHead className="text-right text-[11px] uppercase tracking-[0.05em]">
                  Review
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {slice.map((s) => {
                const rawSource = s.proposed_source ?? "";
                // Two warning flavors come from different places: the
                // proposer bakes "⚠️ " into module-level sources, and the
                // review layer prefixes "possible duplicate" rows. Both
                // render as ONE warning badge (the triangle icon chip);
                // the raw glyph is stripped from the message.
                const isDuplicate = rawSource.startsWith("possible duplicate");
                const hasWarningGlyph = /^\s*⚠/.test(rawSource);
                const flagged = isDuplicate || hasWarningGlyph;
                const message = rawSource.replace(/^\s*⚠️?\s*/, "");
                return (
                  <TableRow key={s.id}>
                    <TableCell>
                      <div className="min-w-0">
                        <p className="truncate text-[13px] font-semibold [overflow-wrap:anywhere] text-foreground">
                          {s.name}
                        </p>
                        <div className="mt-1 flex flex-wrap items-center gap-1.5">
                          <span className="rounded-sm border border-border bg-muted px-1.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide text-muted-foreground">
                            {s.bloom_level ?? "unmapped"}
                          </span>
                          {/* Weight is a real number a reviewer must see:
                              it is how much this skill counts toward the
                              readiness rollup (masterplan 8). Badge it in
                              gold like the readiness accents, never inline
                              muted text. */}
                          <span className="rounded-sm border border-brand-gold/30 bg-brand-gold/10 px-1.5 py-0.5 font-mono text-[10.5px] font-bold text-brand-gold-foreground">
                            w {s.blueprint_weight}
                          </span>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {s.proposed_source ? (
                        <div className="flex min-w-0 items-center gap-1.5">
                          {flagged ? (
                            <span
                              className="inline-flex size-4 shrink-0 items-center justify-center rounded-[2px] bg-brand-orange/15 text-brand-orange"
                              aria-hidden
                            >
                              <TriangleAlertIcon size={11} />
                            </span>
                          ) : null}
                          <span
                            className={
                              flagged
                                ? "min-w-0 flex-1 truncate text-[12.5px] font-medium text-brand-orange-foreground"
                                : "min-w-0 flex-1 truncate text-[12.5px] text-foreground/80"
                            }
                            title={s.proposed_source}
                          >
                            {message}
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <ReviewActions
                        disabled={review.isPending}
                        isFirst={slice[0].id === s.id}
                        onApprove={() => review.mutate({ skillId: s.id, status: "approved" })}
                        onReject={() => review.mutate({ skillId: s.id, status: "rejected" })}
                      />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </>
      )}

      {/* Review queue footer: range line + windowed pager, same as the
          roster. Approving/rejecting removes a row, so safePage clamps if
          the last item on a page is cleared. */}
      {proposed.length > PAGE_SIZE ? (
        <div className="flex flex-wrap items-center justify-between gap-2 border-t px-5 py-3">
          <p className="font-mono text-[11px] text-muted-foreground">
            {proposed.length === 0
              ? "0 pending"
              : `${safePage * PAGE_SIZE + 1}–${Math.min(
                  proposed.length,
                  (safePage + 1) * PAGE_SIZE
                )} of ${proposed.length}`}
          </p>
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  className={safePage === 0 ? "pointer-events-none opacity-40" : undefined}
                />
              </PaginationItem>
              {pageWindow(safePage, pages).map((item, i) =>
                item === null ? (
                  <PaginationItem key={`gap-${i}`}>
                    <span className="px-0.5 font-mono text-xs text-muted-foreground">…</span>
                  </PaginationItem>
                ) : (
                  <PaginationItem key={item}>
                    <PaginationLink isActive={item === safePage} onClick={() => setPage(item)}>
                      {item + 1}
                    </PaginationLink>
                  </PaginationItem>
                )
              )}
              <PaginationItem>
                <PaginationNext
                  onClick={() => setPage((p) => Math.min(pages - 1, p + 1))}
                  className={safePage >= pages - 1 ? "pointer-events-none opacity-40" : undefined}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      ) : null}
    </div>
  );
}
