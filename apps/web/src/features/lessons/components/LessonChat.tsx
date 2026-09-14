import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { BrainIcon } from "@/components/ui/brain";
import { GraduationCapIcon } from "@/components/ui/graduation-cap";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { PartyPopperIcon } from "@/components/ui/party-popper";
import { RotateCCWIcon } from "@/components/ui/rotate-ccw";
import { AnswerableCard } from "@/components/study/AnswerableCard";
import { AssistantBlock } from "@/components/study/AssistantBlock";
import { ComposeDock, type ComposeDockPrimary } from "@/components/study/ComposeDock";
import { SessionBar } from "@/components/study/SessionBar";
import { StudyStream } from "@/components/study/StudyStream";
import { StudySurface } from "@/components/study/StudySurface";
import { TeachingBlock } from "@/components/study/TeachingBlock";
import { UserBlock } from "@/components/study/UserBlock";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { useLesson, useSubmitStepCheck } from "@/features/lessons/hooks/use-lessons";
import type { LessonCheckResult } from "@/features/lessons/schema/lessons.schema";
import { useTutorAsk } from "@/features/tutor";
import { celebrate } from "@/lib/celebrate";

type FollowUpTurn = { question: string; answer: string };

// A lesson's current step is one slot, not a growing list. The teaching turn
// stays dimmed behind the mounted check so the check takes the slot over rather
// than becoming another bubble below it.
export function LessonChat({
  courseId,
  skillId,
  onExit,
}: {
  courseId: string;
  skillId: string;
  onExit: () => void;
}) {
  const reduceMotion = useReducedMotion();
  const { data, isLoading, isError, refetch } = useLesson(courseId, skillId);
  const submit = useSubmitStepCheck(courseId);
  const checkAsk = useTutorAsk(courseId);
  const checkFollowUp = useTutorAsk(courseId);
  const followUp = useTutorAsk(courseId);

  const [stepIndex, setStepIndex] = useState(0);
  const [checkOpen, setCheckOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<LessonCheckResult | null>(null);
  const [checkThreadOpen, setCheckThreadOpen] = useState(false);
  const [checkExplanation, setCheckExplanation] = useState<string | null>(null);
  // True once this check has been graded at least once. Keeps the dock mounted
  // through a retry: docking the check takes over the lane only while the
  // student is answering for the FIRST time. After a miss they have just used
  // the dock ("Try again") and it vanishing the moment they press it left the
  // surface with no visible affordance at all.
  const [hasAnsweredOnce, setHasAnsweredOnce] = useState(false);
  // Which check-thread requests are in flight, so the loading placeholder can
  // say the right thing (a hint is not an explanation).
  const [checkThreadKind, setCheckThreadKind] = useState<"hint" | "explain">("hint");
  // Kinds already answered for this check. Used to disable the buttons once
  // they have nothing left to do, and to allow a hint to be upgraded into a
  // full explanation (but never a second time).
  const [answeredKinds, setAnsweredKinds] = useState<Set<"hint" | "explain">>(
    () => new Set()
  );
  const [checkFollowUpTurns, setCheckFollowUpTurns] = useState<FollowUpTurn[]>([]);
  const [followUpTurns, setFollowUpTurns] = useState<FollowUpTurn[]>([]);
  // The question whose answer is still in flight. Rendered immediately as a
  // student turn + pending Kala reply, then cleared once the answer lands.
  const [pendingFollowUp, setPendingFollowUp] = useState<string | null>(null);
  const [pendingCheckFollowUp, setPendingCheckFollowUp] = useState<string | null>(null);
  const checkThreadRef = useRef<HTMLDivElement | null>(null);
  const hintsUsedRef = useRef(0);
  const startedAtRef = useRef(Date.now());

  function resetStepState() {
    setCheckOpen(false);
    setSelected(null);
    setResult(null);
    setCheckThreadOpen(false);
    setCheckExplanation(null);
    setCheckThreadKind("hint");
    setCheckFollowUpTurns([]);
    setFollowUpTurns([]);
    setPendingFollowUp(null);
    setPendingCheckFollowUp(null);
    hintsUsedRef.current = 0;
    startedAtRef.current = Date.now();
  }

  useEffect(() => {
    setStepIndex(0);
    resetStepState();
  }, [data?.lessonId]);

  // Bring the opened check thread into view once it has actually painted.
  // Runs on checkThreadOpen (and whenever an answer lands) so the student is
  // taken to the explanation even if the check card is taller than the
  // viewport — the "redirect the user there" half of the Explain/Hint
  // interaction. Declared before the loading/error early returns below,
  // since hooks must run in the same order on every render.
  useEffect(() => {
    if (!checkThreadOpen) return;
    const node = checkThreadRef.current;
    if (!node) return;
    node.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
  }, [checkThreadOpen, checkExplanation, checkAsk.isPending, reduceMotion]);

  if (isLoading || data?.status === "generating") {
    return (
      <div id="tour-lesson-generating" className="w-full">
        <LoadingPanel label="Kala is writing your lesson — first pass takes a moment…" lines={5} />
      </div>
    );
  }
  if (isError) {
    return (
      <EmptyState
        title="We could not load this lesson"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  }
  if (!data || data.steps.length === 0) {
    return (
      <EmptyState
        title="No lesson here yet"
        description="This skill doesn't have a lesson yet. Come back after course content is ingested."
      />
    );
  }

  const total = data.steps.length;
  const done = stepIndex >= total;
  const current = done ? null : data.steps[stepIndex];
  const hasGradedCheck = checkOpen && result !== null;

  function openCheck() {
    if (!current?.check) {
      resetStepState();
      setStepIndex((index) => index + 1);
      return;
    }
    setSelected(null);
    setResult(null);
    setCheckThreadOpen(false);
    setCheckExplanation(null);
    setCheckThreadKind("hint");
    setAnsweredKinds(new Set());
    setCheckFollowUpTurns([]);
    setFollowUpTurns([]);
    setPendingFollowUp(null);
    setPendingCheckFollowUp(null);
    setHasAnsweredOnce(false);
    hintsUsedRef.current = 0;
    startedAtRef.current = Date.now();
    setCheckOpen(true);
  }

  function choose(choiceId: string) {
    if (!current?.check || result) return;
    setSelected(choiceId);
    submit.mutate(
      {
        stepId: current.id,
        itemId: current.check.itemId,
        choiceId,
        latencyMs: Date.now() - startedAtRef.current,
        hintsUsed: hintsUsedRef.current,
      },
      { onSuccess: (nextResult) => { setResult(nextResult); setHasAnsweredOnce(true); } }
    );
  }

  function checkContext(instruction: string) {
    if (!current?.check) return instruction;
    const grading = result
      ? `The student's submission was graded ${result.correct ? "correct" : "incorrect"}. The authoritative feedback is: "${result.explanation}".`
      : "The student has not submitted an answer yet.";

    return [
      "You are Kala in a guided lesson. Stay strictly within this one comprehension check; do not broaden into unrelated course material.",
      `Check question: "${current.check.prompt}"`,
      grading,
      instruction,
    ].join("\n\n");
  }

  function openCheckThread(kind: "hint" | "explain") {
    if (!current?.check) return;
    // The thread opens IMMEDIATELY, before the answer exists — the student's
    // attention moves to where the explanation will appear (a Kala header
    // with a pending bubble), rather than staring at the button they just
    // pressed while it silently swaps into a spinner.
    setCheckThreadOpen(true);

    // One request per kind, ever. Previously this bailed out only while a
    // request was in flight, which left two holes: a second tap after the
    // answer had landed re-opened the thread with no new request (so the
    // button looked live but did nothing), and asking for the OTHER kind
    // was silently swallowed — a student who read the hint could never
    // escalate to the full explanation. Tracking which kinds have already
    // been answered fixes both: an answered kind is inert, an unanswered
    // one still works. It also stops repeated taps from inflating
    // hintsUsedRef, which feeds hints_used on the evidence event and so
    // would have moved the student's mastery for free.
    if (checkAsk.isPending || answeredKinds.has(kind)) return;

    setCheckThreadKind(kind);
    checkAsk.mutate(
      {
        question: checkContext(
          kind === "hint"
            ? "Give a concise hint that helps the student reason toward the answer without revealing it."
            : "Explain the answer clearly, including why the other options do not fit."
        ),
        style: kind === "hint" ? "eli5" : "default",
      },
      {
        onSuccess: (answer) => {
          setCheckExplanation(answer.answer);
          setAnsweredKinds((kinds) => new Set(kinds).add(kind));
          if (kind === "hint") hintsUsedRef.current += 1;
        },
      }
    );
  }

  function askCheckFollowUp(question: string) {
    if (!current?.check) return;
    setCheckThreadOpen(true);
    setPendingCheckFollowUp(question);
    checkFollowUp.mutate(
      { question: checkContext(`The student asks: "${question}"`), style: "default" },
      {
        onSuccess: (answer) => {
          setCheckFollowUpTurns((turns) => [...turns, { question, answer: answer.answer }]);
          setPendingCheckFollowUp(null);
        },
        onError: () => setPendingCheckFollowUp(null),
      }
    );
  }

  function askFollowUp(question: string) {
    if (!current) return;
    // The student's turn goes into the stream NOW, with a pending Kala reply
    // under it. Waiting for onSuccess and then appending {question, answer}
    // as one unit is why the whole exchange appeared at once with no
    // animation: neither half existed until the model had finished.
    setPendingFollowUp(question);
    followUp.mutate(
      { question, style: "default" },
      {
        onSuccess: (answer) => {
          setFollowUpTurns((turns) => [...turns, { question, answer: answer.answer }]);
          setPendingFollowUp(null);
        },
        onError: () => setPendingFollowUp(null),
      }
    );
  }

  function advanceStep() {
    if (!result?.advance) return;
    const finishing = stepIndex + 1 >= total;
    resetStepState();
    setStepIndex((index) => index + 1);
    // Fire only on the transition into the done state, and only when motion
    // is welcome. `total` is the lesson length, so this is the last step.
    if (finishing && !reduceMotion) celebrate();
  }

  function retry() {
    setSelected(null);
    setResult(null);
    // The explanation is the answer key; leaving it on screen through a retry
    // defeats the retry. Close the thread and drop any explanation with it —
    // including the answered-kind record, so the student can ask for a fresh
    // hint on the retry rather than finding the button permanently dead.
    setCheckThreadOpen(false);
    setCheckExplanation(null);
    setAnsweredKinds(new Set());
    setPendingCheckFollowUp(null);
    setCheckFollowUpTurns([]);
    startedAtRef.current = Date.now();
  }

  function goBack() {
    if (checkThreadOpen) {
      setCheckThreadOpen(false);
      return;
    }
    if (checkOpen) {
      setCheckOpen(false);
      return;
    }
    onExit();
  }

  function restartLesson() {
    resetStepState();
    setStepIndex(0);
  }

  const isCheckTakeover = Boolean(checkOpen && current?.check);
  const checkDockVisible = isCheckTakeover && (checkThreadOpen || hasGradedCheck || hasAnsweredOnce);
  const hintPending = checkThreadKind === "hint";
  // Answering again after a miss: the dock is present but inert (disabled
  // primary, no follow-up input and so no toggle). Asking Kala mid-re-answer
  // would be the only way to reach the answer key, which is exactly what the
  // retry is trying to withhold.
  const isReanswering = isCheckTakeover && hasAnsweredOnce && !hasGradedCheck;
  // Every dock primary carries an animated icon so the dock reads the same
  // as the workspace rail: arrow for "keep moving", check/popper for "done",
  // undo for "try again".
  const dockPrimary: ComposeDockPrimary | undefined = done
    ? { label: "Start again", onClick: restartLesson, icon: RotateCCWIcon }
      : !checkOpen
      ? {
          id: "tour-lesson-continue",
          label: "Continue",
          onClick: openCheck,
          icon: GraduationCapIcon,
        }
      : hasGradedCheck
        ? result?.advance
          ? {
              label: stepIndex + 1 >= total ? "Finish lesson" : "Next step",
              onClick: advanceStep,
              icon: stepIndex + 1 >= total ? PartyPopperIcon : ArrowRightIcon,
            }
          : { label: "Try again", onClick: retry, icon: RotateCCWIcon }
        : // Pre-grade after a miss. The dock stays mounted so the layout does
          // not jump and the student keeps a visible anchor, but the action is
          // deliberately inert: answering happens by picking a different
          // choice on the card, which auto-grades on pick. Without an `onAsk`
          // ComposeDock renders action mode, so this stays a disabled button
          // rather than falling through to the follow-up text input.
          {
            label: "Try again",
            onClick: retry,
            icon: RotateCCWIcon,
            disabled: true,
          };

  return (
    <StudySurface
      bar={
        <SessionBar
          title={data.title}
          progress={{
            current: done ? total : stepIndex + 1,
            total,
            label: "step",
            bloomLevel: current?.bloomLevel,
          }}
          onBack={goBack}
          backLabel="Choose another topic"
        />
      }
      dock={isCheckTakeover && !checkDockVisible ? undefined : (
        <ComposeDock
          primary={dockPrimary}
          onAsk={
            isReanswering
              ? undefined
              : isCheckTakeover
              ? askCheckFollowUp
              : !done
                ? askFollowUp
                : undefined
          }
          askPending={
            isReanswering
              ? false
              : isCheckTakeover
                ? checkFollowUp.isPending
                : followUp.isPending
          }
          placeholder={isCheckTakeover ? "Ask Kala about this check…" : "Ask Kala about this step…"}
        />
      )}
    >
      <AnimatePresence initial={false} mode="wait">
        {isCheckTakeover && current?.check ? (
          <motion.div
            key="check-takeover"
            initial={reduceMotion ? false : { opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0, scale: 0.98 }}
            transition={{ duration: reduceMotion ? 0 : 0.18 }}
            className="h-full min-h-0 flex-1 overflow-y-auto px-4 pb-8 pt-10 sm:pt-14"
          >
            <div id="tour-lesson-check" className="mx-auto w-full max-w-[800px]">
              <p className="mb-4 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Check yourself</p>
              <AnswerableCard
                prompt={current.check.prompt}
                choices={current.check.choices}
                selectedId={selected}
                onSelect={choose}
                isPending={submit.isPending}
                resultAnchorId="tour-lesson-check-feedback"
                result={
                  result
                    ? {
                        correct: result.correct,
                        explanation: result.explanation,
                        mastery: result.mastery,
                      }
                    : null
                }
                actions={
                  // Keep the label stable. The old behavior swapped the
                  // button into a "Thinking…" spinner, which read as "this
                  // button is loading" rather than "Kala is answering below"
                  // — the pending state now lives in the thread instead.
                  // Disabled once this kind has been answered: the button has
                  // nothing left to do, and leaving it live invited repeat
                  // taps that produced no request and no feedback.
                  !result ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openCheckThread("hint")}
                      disabled={checkAsk.isPending || answeredKinds.has("hint")}
                    >
                      <BrainIcon size={15} className="text-muted-foreground" aria-hidden />
                      Hint
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openCheckThread("explain")}
                      disabled={checkAsk.isPending || answeredKinds.has("explain")}
                    >
                      <BrainIcon size={15} className="text-muted-foreground" aria-hidden />
                      Explain
                    </Button>
                  )
                }
              />
              {checkThreadOpen ? (
                <div ref={checkThreadRef} className="mt-8 scroll-mt-4 border-t pt-6">
                  {/* One AssistantBlock for the whole thread: it renders
                      Kala's header while the answer is still loading and
                      keeps it once the answer lands. Rendering a separate
                      heading here plus AssistantBlock's own was what made
                      two "Kala" headers stack up. */}
                  <AssistantBlock
                    text={checkExplanation ?? undefined}
                    pending={checkAsk.isPending}
                    pendingLabel={
                      hintPending ? "Kala is preparing a hint…" : "Kala is preparing an explanation…"
                    }
                    // The graded explanation is reference text the student
                    // reads after answering, not a live reply — it should be
                    // there the moment it arrives, not type itself out.
                    animate={false}
                  />
                  {checkFollowUpTurns.map((turn, index) => (
                    <div key={`${turn.question}-${index}`} className="mt-5 space-y-3">
                      <UserBlock text={turn.question} />
                      <AssistantBlock text={turn.answer} />
                    </div>
                  ))}
                  {/* In-flight question: the student's turn and a pending Kala
                      reply appear the moment they hit send. */}
                  {pendingCheckFollowUp ? (
                    <div className="mt-5 space-y-3">
                      <UserBlock text={pendingCheckFollowUp} />
                      <AssistantBlock pending pendingLabel="Kala is thinking…" />
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="lesson-stream"
            initial={reduceMotion ? false : { opacity: 0.7 }}
            animate={{ opacity: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.14 }}
            className="h-full min-h-0 flex-1"
          >
            <StudyStream>
              {data.steps.slice(0, done ? total : stepIndex).map((step) => (
                <div key={step.id} className="space-y-3">
                  <TeachingBlock step={step} />
                  <div className="mr-auto flex w-full max-w-full items-center gap-2">
                    <span className="rounded-sm border border-brand-green/40 bg-brand-green/10 px-2.5 py-1 text-xs font-semibold text-brand-green">
                      Step complete ✓
                    </span>
                  </div>
                </div>
              ))}

              {current ? (
                <div className="space-y-3">
                  <TeachingBlock step={current} id="tour-lesson-explain" />
                  {followUpTurns.map((turn, index) => (
                    <div key={`${turn.question}-${index}`} className="space-y-3">
                      <UserBlock text={turn.question} />
                      <AssistantBlock text={turn.answer} />
                    </div>
                  ))}
                  {/* In-flight question: the student's turn and a pending
                      Kala reply appear the moment they hit send. */}
                  {pendingFollowUp ? (
                    <div className="space-y-3">
                      <UserBlock text={pendingFollowUp} />
                      <AssistantBlock pending pendingLabel="Kala is thinking…" />
                    </div>
                  ) : null}
                </div>
              ) : null}

              {done ? (
                <AssistantBlock
                  text={`**Lesson complete — nice work.**\n\nYou worked through all ${total} steps. The check answers fed your twin — keep the concepts fresh with spaced review.`}
                />
              ) : null}
            </StudyStream>
          </motion.div>
        )}
      </AnimatePresence>
    </StudySurface>
  );
}
