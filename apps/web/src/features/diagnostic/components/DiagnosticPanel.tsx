import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useReducedMotion } from "motion/react";
import {
  useDiagnostic,
  useSubmitDiagnostic,
} from "@/features/diagnostic/hooks/use-diagnostic";
import { useBankStatus } from "@/features/bank";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { AnswerableCard } from "@/components/study/AnswerableCard";
import { PageHeader } from "@/components/shell/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { MasteryDelta } from "@/components/kala";
import { TransitionPanel } from "@/components/motion/transition-panel";
import type { Answer } from "@/features/diagnostic/schema/diagnostic.schema";

// The diagnostic establishes a baseline, it does not grade a quiz. Two
// things follow from that, both deliberate departures from how
// practice/flashcards work:
//   1. This screen only ever shows skills THIS student has never given
//      diagnostic evidence for (see routers/diagnostic.py's due-check) —
//      it is not an always-open tab, it surfaces only when there is
//      something new to baseline.
//   2. Answers are never revealed per-question while the student is
//      taking it. Right/wrong mid-baseline turns a baseline measurement
//      into a graded quiz, which undercuts the whole point of a baseline.
//      The only outcome shown is the twin actually moving, after the
//      whole sitting is submitted — a blur-out on the question set,
//      crossfading into the mastery-delta reveal (MasteryDelta already
//      builds that "your twin just updated" moment; this panel just stops
//      undercutting it with an inline answer key).
//
const REVEAL_VARIANTS = {
  enter: { opacity: 0, filter: "blur(6px)" },
  center: { opacity: 1, filter: "blur(0px)" },
  exit: { opacity: 0, filter: "blur(6px)" },
};
const REVEAL_VARIANTS_REDUCED = {
  enter: { opacity: 0 },
  center: { opacity: 1 },
  exit: { opacity: 0 },
};

export function DiagnosticPanel({ courseId }: { courseId: string }) {
  const { data, isLoading, isError } = useDiagnostic(courseId);
  const bank = useBankStatus(courseId);
  const submit = useSubmitDiagnostic(courseId);
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [startedAt] = useState(() => Date.now());
  const [closingDialogOpen, setClosingDialogOpen] = useState(false);

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

  if (isLoading)
    return <LoadingPanel label="Checking your baseline…" lines={4} />;
  if (isError)
    return (
      <EmptyState
        title="We could not load the diagnostic"
        description="Check your connection and try again."
        action={<Button variant="outline">Retry</Button>}
      />
    );
  if (data?.status === "generating" && data.questions.length === 0)
    return (
      <LoadingPanel
        label={`Preparing your baseline. ${data.readyCount} question${data.readyCount === 1 ? " is" : "s are"} ready.`}
        lines={4}
      />
    );
  if (
    data?.status === "failed" &&
    data.failedSkillIds.length > 0 &&
    bank.isLoading
  )
    return <LoadingPanel label="Checking course material…" lines={4} />;
  if (allFailedSkillsHaveNoMaterial)
    return (
      <EmptyState
        title="No course material yet"
        description="These skills don’t have course material yet."
      />
    );
  if (data?.status === "failed")
    return (
      <EmptyState
        title="Your baseline is not ready yet"
        description="Kala could not create a question for any of the topics currently due. Your course team can reopen the failed topic after adding material."
      />
    );
  // Nothing due is the common, GOOD state here, not a missing-content
  // error: either every mapped skill already has this student's diagnostic
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
  if (!data || (data.questions.length === 0 && !submitted))
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
    <>
      <div data-study-surface className="flex h-full min-h-0 flex-col">
        {!submitted ? (
          <header className="shrink-0 border-b bg-background">
            <PageHeader
              eyebrow="Diagnostic"
              title="Find your starting point"
              description="Answer a few questions so Kala can understand what you already know and where to begin."
              className="mx-auto mb-0 w-full max-w-[800px] px-4 py-4 sm:px-6"
            />
          </header>
        ) : null}
        <TransitionPanel
          className="min-h-0 flex-1 overflow-y-auto [&>div]:min-h-full"
          activeIndex={submitted ? 1 : 0}
          variants={reduceMotion ? REVEAL_VARIANTS_REDUCED : REVEAL_VARIANTS}
          transition={{ duration: reduceMotion ? 0 : 0.35, ease: "easeInOut" }}
        >
          {[
            <div
              key="answering"
              id="tour-diagnostic-card"
              className="mx-auto flex w-full max-w-[800px] flex-col gap-6 px-4 py-6 sm:px-6"
            >
              {data.pendingSkillIds.length > 0 ? (
                <p className="border-l-2 border-brand-orange/60 px-3 py-2 text-sm text-muted-foreground">
                  Preparing questions for {data.pendingSkillIds.length} more{" "}
                  {data.pendingSkillIds.length === 1 ? "topic" : "topics"}.
                  Ready questions are below.
                </p>
              ) : null}
              {data.questions.map((q, qi) => (
                <AnswerableCard
                  key={q.id}
                  prompt={q.prompt}
                  choices={q.choices}
                  selectedId={selections[q.id] ?? null}
                  onSelect={(choiceId) =>
                    setSelections((s) => ({ ...s, [q.id]: choiceId }))
                  }
                  result={null}
                  isPending={submit.isPending}
                  choicesAnchorId={
                    qi === 0 ? "tour-diagnostic-choices" : undefined
                  }
                  firstChoiceId={null}
                />
              ))}
            </div>,

            <Card
              key="reveal"
              className="mx-auto my-6 w-[calc(100%-2rem)] max-w-[800px]"
            >
              <CardHeader>
                <CardTitle>Baseline set</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                <p className="text-sm text-muted-foreground">
                  Here's where your twin landed. Practice moves it from here.
                </p>
                {masteryDeltaRows.length > 0 ? (
                  <MasteryDelta
                    rows={masteryDeltaRows}
                    onRevealComplete={() => setClosingDialogOpen(true)}
                  />
                ) : null}
                <Button
                  variant="outline"
                  onClick={() => navigate({ to: "/course" })}
                >
                  Back to workspace
                </Button>
              </CardContent>
            </Card>,
          ]}
        </TransitionPanel>
        <footer className="shrink-0 border-t bg-background py-4">
          <div className="mx-auto flex w-full max-w-[800px] flex-wrap items-center justify-between gap-3 px-4 sm:px-6">
            <p
              role="status"
              className="font-mono text-xs text-muted-foreground"
            >
              {submitted
                ? "Baseline set"
                : `${answeredCount} of ${data.questions.length} answered`}
            </p>
            <Button
              id={submitted ? undefined : "tour-diagnostic-submit"}
              variant="orange"
              className="ml-auto"
              disabled={!submitted && (!allAnswered || submit.isPending)}
              aria-busy={submit.isPending || undefined}
              onClick={
                submitted ? () => navigate({ to: "/course" }) : handleSubmit
              }
            >
              {submitted
                ? "Back to workspace"
                : submit.isPending
                  ? "Building your baseline…"
                  : "Submit diagnostic"}
              <ArrowRightIcon size={16} />
            </Button>
          </div>
          {submit.isError ? (
            <p
              role="alert"
              className="mx-auto mt-2 w-full max-w-[800px] px-4 text-sm text-destructive sm:px-6"
            >
              Your baseline could not be saved. Please try again.
            </p>
          ) : null}
        </footer>
      </div>

      <Dialog open={closingDialogOpen} onOpenChange={setClosingDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Baseline set</DialogTitle>
            <DialogDescription>
              That's it for now. Kala will let you know the moment there's a new
              topic worth baselining, no need to check back here on your own.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="orange"
              onClick={() => {
                setClosingDialogOpen(false);
                navigate({ to: "/course" });
              }}
            >
              Back to workspace
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
