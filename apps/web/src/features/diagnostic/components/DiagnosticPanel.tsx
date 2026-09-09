import { useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useReducedMotion } from "motion/react";
import { useDiagnostic, useSubmitDiagnostic } from "@/features/diagnostic/hooks/use-diagnostic";
import { StudySessionShell } from "@/components/study/StudySessionShell";
import { StudyStream } from "@/components/study/StudyStream";
import { AnswerableCard } from "@/components/study/AnswerableCard";
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
import { MasteryDelta, CornerBrackets } from "@/components/kala";
import { TransitionPanel } from "@/components/motion/transition-panel";
import { Spinner } from "@/components/ui/spinner";
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
// Stage 3 of the AI overhaul (docs/AI_OVERHAUL_TODO.md): the question list
// now renders through the same AnswerableCard/StudyStream every other quiz
// surface uses, instead of a bespoke RadioGroup — Diagnostic was the one
// surface still on its own custom rendering. The batch-silent, blur/reveal,
// closing-dialog mechanics below are UNCHANGED on purpose: they're tuned
// and working, there was no bug driving this migration, only the shared
// question-rendering primitive changed.
//
// Diagnostic is the one surface that puts more than one AnswerableCard on
// screen at once (every other surface shows a single question/card at a
// time) — every card below passes firstChoiceId={null} so their first
// choice buttons don't all fight over the same "tour-first-choice" id.
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
  const masteryDeltaRows = useMemo(
    () =>
      (submit.data?.masteryDelta ?? []).map((d) => ({
        skillId: d.skillId,
        skillName: d.skillName,
        priorBand: d.priorBand,
        posteriorBand: d.posteriorBand,
      })),
    [submit.data?.masteryDelta]
  );

  if (isLoading)
    return (
      <LoadingPanel
        label="Checking your baseline…"
        lines={4}
      />
    );
  if (isError)
    return (
      <EmptyState
        title="We could not load the diagnostic"
        description="Check your connection and try again."
        action={<Button variant="outline">Retry</Button>}
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
      <StudySessionShell
        progress={{ current: answeredCount, total: data.questions.length, label: "answered" }}
      >
        <TransitionPanel
          activeIndex={submitted ? 1 : 0}
          variants={reduceMotion ? REVEAL_VARIANTS_REDUCED : REVEAL_VARIANTS}
          transition={{ duration: reduceMotion ? 0 : 0.35, ease: "easeInOut" }}
        >
        {[
          <div key="answering" id="tour-diagnostic-card" className="relative border bg-card">
            <CornerBrackets />
            <div className="flex items-center justify-between gap-3 border-b px-5 py-3">
              <span className="text-sm font-semibold text-foreground">Course diagnostic</span>
            </div>

            <StudyStream height="h-[55vh]">
              {data.questions.map((q, qi) => (
                <div key={q.id} className="rounded-md border bg-card p-4">
                  <AnswerableCard
                    prompt={q.prompt}
                    choices={q.choices}
                    selectedId={selections[q.id] ?? null}
                    onSelect={(choiceId) => setSelections((s) => ({ ...s, [q.id]: choiceId }))}
                    result={null}
                    isPending={submit.isPending}
                    choicesAnchorId={qi === 0 ? "tour-diagnostic-choices" : undefined}
                    firstChoiceId={null}
                  />
                </div>
              ))}
            </StudyStream>

            <div className="border-t p-4">
              <Button
                id="tour-diagnostic-submit"
                variant="orange"
                disabled={!allAnswered || submit.isPending}
                onClick={handleSubmit}
              >
                {submit.isPending ? (
                  <>
                    <Spinner className="size-3.5" /> Building your baseline…
                  </>
                ) : (
                  "Submit diagnostic"
                )}
              </Button>
            </div>
          </div>,

          <Card key="reveal">
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
              <Button variant="outline" onClick={() => navigate({ to: "/course" })}>
                Back to workspace
              </Button>
            </CardContent>
          </Card>,
        ]}
      </TransitionPanel>
      </StudySessionShell>

      <Dialog open={closingDialogOpen} onOpenChange={setClosingDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Baseline set</DialogTitle>
            <DialogDescription>
              That's it for now. Kala will let you know the moment there's a new topic worth
              baselining, no need to check back here on your own.
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
