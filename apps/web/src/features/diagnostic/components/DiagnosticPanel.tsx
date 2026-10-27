import { useMemo, useState } from "react";
import { useSession } from "@/lib/auth/AuthProvider";
import {
  useDiagnostic,
  useSubmitDiagnostic,
} from "@/features/diagnostic/hooks/use-diagnostic";
import { useBankStatus } from "@/features/bank";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { AnswerableCard } from "@/components/study/AnswerableCard";
import { PageHeader } from "@/components/shell/PageHeader";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { DiagnosticResults } from "@/features/diagnostic/components/DiagnosticResults";
import { Spinner } from "@/components/ui/spinner";
import type { Answer } from "@/features/diagnostic/schema/diagnostic.schema";

// The diagnostic establishes a baseline, it does not grade a quiz. Two
// things follow from that, both deliberate departures from how
// practice/flashcards work:
//   1. This screen only ever shows skills THIS student has never given
//      learning evidence for (see routers/diagnostic.py's due-check) —
//      it is not an always-open tab, it surfaces only when there is
//      something new to baseline.
//   2. Answers are never revealed per-question while the student is
//      taking it. Right/wrong mid-baseline turns a baseline measurement
//      into a graded quiz, which undercuts the whole point of a baseline.
//      The only outcome shown is the twin actually moving, after the
//      whole sitting is submitted. One results view presents the mastery
//      progression and exit actions without a per-question answer key.
//
export function DiagnosticPanel({ courseId }: { courseId: string }) {
  const { data, isLoading, isError, refetch } = useDiagnostic(courseId);
  const bank = useBankStatus(courseId);
  const isStudent = useSession()?.role === "student";
  const submit = useSubmitDiagnostic(courseId);
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [startedAt] = useState(() => Date.now());

  // Memoized on the actual masteryDelta reference (stable from React Query
  // until a real refetch), not recreated on every unrelated re-render — the
  // stagger effect in MasteryDelta keys off array identity, so an unstable
  // array would silently restart the reveal animation on any parent re-render.
  // Must sit above the early returns below: Hooks can't be called
  // conditionally, and this component returns early while loading/erroring.
  // Same for `submitted`: the reveal guard below reads it, so it has to be
  // defined before the empty-state early return, not after it.
  const submitted = submit.isSuccess;
  const allFailedSkillsHaveNoMaterial = Boolean(
    data &&
    data.questions.length === 0 &&
    data.failedSkillIds.length > 0 &&
    data.failedSkillIds.every(
      (skillId) =>
        bank.data?.skills.find((entry) => entry.skillId === skillId)?.status ===
        "no_material",
    ),
  );
  const masteryDeltaRows = useMemo(
    () =>
      (submit.data?.masteryDelta ?? []).map((d) => ({
        skillId: d.skillId,
        skillName: d.skillName,
        priorBand: d.priorBand,
        posteriorBand: d.posteriorBand,
      })),
    [submit.data?.masteryDelta],
  );

  // A completed sitting owns the view even if its question query refetches.
  if (submitted)
    return <DiagnosticResults rows={masteryDeltaRows} total={submit.data?.total ?? 0} celebrationKey={`diagnostic:${courseId}:${submit.submittedAt}`} />;

  if (isLoading)
    return <div className="mx-auto w-full max-w-[800px] px-4 py-6 sm:px-6"><LoadingPanel label="Checking your baseline…" lines={4} /></div>;
  if (isError && !data?.questions.length)
    return (
      <EmptyState
        title="We could not load the diagnostic"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  if (data?.status === "generating" && data.questions.length === 0)
    return (
      <div className="mx-auto w-full max-w-[800px] px-4 py-6 sm:px-6"><LoadingPanel
        label={`Waiting for baseline questions. ${data.readyCount} question${data.readyCount === 1 ? " is" : "s are"} ready.`}
        lines={4}
      /></div>
    );
  if (
    data?.status === "failed" &&
    data.questions.length === 0 &&
    data.failedSkillIds.length > 0 &&
    bank.isLoading
  )
    return <div className="mx-auto w-full max-w-[800px] px-4 py-6 sm:px-6"><LoadingPanel label={isStudent ? "Checking question availability…" : "Checking course material…"} lines={4} /></div>;
  if (allFailedSkillsHaveNoMaterial)
    return (
      <EmptyState
        title={isStudent ? "Your baseline check isn't ready yet." : "No course material yet"}
        description={isStudent ? "Check back later." : "These skills don’t have course material yet."}
      />
    );
  if (data?.status === "failed" && data.questions.length === 0)
    return (
      <EmptyState
        title="Your baseline is not ready yet"
        description={isStudent ? "Kala could not prepare your baseline questions. Check back later." : "Kala could not create a question for any of the topics currently due. Your course team can reopen the failed topic after adding material."}
      />
    );
  // Nothing due is the common, GOOD state here, not a missing-content
  // error: either every candidate skill already has this student's learning
  // evidence, or the instructor hasn't approved any skills yet. Either
  // way there is nothing to baseline right now, so this reads as caught up
  // rather than empty. BUT once a sitting has been submitted, this guard
  // must not fire: the question-list query gets invalidated on submit and
  // refetches to an empty set immediately (all skills now have evidence),
  // and swapping to this caught-up state then would yank the mastery reveal
  // out from under the just-finished sitting. A refetch from ANY cause
  // (invalidation, window refocus) resolves to empty here — the reveal is
  // the thing on screen, so it wins over the empty state until the panel
  // is visited fresh again.
  if (data?.questions.length === 0 && (data.waitingForMaterialCount ?? 0) > 0)
    return (
      <EmptyState
        title={isStudent ? "Your baseline check isn't ready yet." : "Waiting for course material"}
        description={isStudent ? "Check back later." : `${data.waitingForMaterialCount} ${data.waitingForMaterialCount === 1 ? "topic is" : "topics are"} waiting for course material. Your course team can make these topics available after adding material.`}
      />
    );
  if (!data || data.questions.length === 0)
    return (
      <EmptyState
        title="You're all caught up"
        description="Nothing new to baseline right now. This screen will have something for you the moment a new topic needs a starting point."
      />
    );

  const answeredCount = data.questions.filter((q) => selections[q.id]).length;
  const allAnswered = data.questions.every((q) => selections[q.id]);

  function handleSubmit() {
    const answers: Answer[] = data!.questions.map((q) => ({
      itemId: q.id,
      choiceId: selections[q.id],
      latencyMs: Date.now() - startedAt,
    }));
    submit.mutate(answers);
  }

  return (
    <div data-study-surface className="flex h-full min-h-0 flex-col">
      <header data-tour="diagnostic-header" className="shrink-0 border-b bg-background">
        <PageHeader
          eyebrow="Diagnostic"
          title="Find your starting point"
          description="Answer a few questions so Kala can understand what you already know and where to begin."
          className="mx-auto mb-0 w-full max-w-screen-2xl px-6 py-8 lg:px-10"
        />
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div id="tour-diagnostic-card" className="mx-auto flex w-full max-w-[800px] flex-col gap-6 px-4 py-6 sm:px-6">
          {data.pendingSkillIds.length > 0 ? (
            <p role="status" className="flex items-center gap-2 border-l-2 border-brand-orange/60 px-3 py-2 text-sm text-muted-foreground">
              <span>Waiting for questions for {data.pendingSkillIds.length} more {data.pendingSkillIds.length === 1 ? "topic" : "topics"}. Ready questions are below.</span>
            </p>
          ) : null}
          {data.questions.map((q, qi) => (
            <AnswerableCard
              key={q.id}
              prompt={q.prompt}
              choices={q.choices}
              selectedId={selections[q.id] ?? null}
              onSelect={(choiceId) => setSelections((s) => ({ ...s, [q.id]: choiceId }))}
              result={null}
              isPending={submit.isPending}
              pendingFeedback={false}
              choicesAnchorId={qi === 0 ? "tour-diagnostic-choices" : undefined}
              firstChoiceId={null}
            />
          ))}
        </div>
      </div>
      <footer className="shrink-0 border-t bg-background py-4">
        <div className="mx-auto flex w-full max-w-[800px] flex-wrap items-center justify-between gap-3 px-4 sm:px-6">
          <p role="status" className="font-mono text-xs text-muted-foreground">
            {answeredCount} of {data.questions.length} answered
          </p>
          <Button
            id="tour-diagnostic-submit"
            variant="orange"
            className="ml-auto"
            disabled={!allAnswered || submit.isPending}
            aria-busy={submit.isPending || undefined}
            onClick={handleSubmit}
          >
            {submit.isPending ? <Spinner aria-hidden /> : null}
            {submit.isPending ? "Building your baseline…" : "Submit diagnostic"}
            {!submit.isPending ? <ArrowRightIcon size={16} /> : null}
          </Button>
        </div>
        {submit.isError ? (
          <p role="alert" className="mx-auto mt-2 w-full max-w-[800px] px-4 text-sm text-destructive sm:px-6">
            Your baseline could not be saved. Please try again.
          </p>
        ) : null}
      </footer>
    </div>
  );
}
