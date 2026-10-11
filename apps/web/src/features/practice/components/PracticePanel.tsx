import { useEffect, useId, useRef, useState } from "react";
import { useReducedMotion } from "motion/react";
import { AnswerableCard } from "@/components/study/AnswerableCard";
import { AssistantBlock } from "@/components/study/AssistantBlock";
import { ComposeDock } from "@/components/study/ComposeDock";
import { SessionBar } from "@/components/study/SessionBar";
import { StudyStream } from "@/components/study/StudyStream";
import { StudySurface } from "@/components/study/StudySurface";
import { UserBlock } from "@/components/study/UserBlock";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { BookOpenIcon } from "@/components/ui/book-open";
import { CheckIcon } from "@/components/ui/check";
import { PartyPopperIcon } from "@/components/ui/party-popper";
import type { PartyPopperIconHandle } from "@/components/ui/party-popper";
import { MasteryBand, MasteryRing } from "@/components/kala";
import { usePracticeSet, usePracticeSetById, usePracticeSetResults, useSubmitPractice, useGenerateSet } from "@/features/practice/hooks/use-practice";
import { useBankStatus } from "@/features/bank";
import { celebrate } from "@/lib/celebrate";
import { useGamification } from "@/features/gamification";
import { useTutorAsk } from "@/features/tutor";
import { PracticeExplainMore } from "@/features/practice/components/PracticeExplainMore";
import type { PracticeSetResults, PracticeSubmitResult } from "@/features/practice/schema/practice.schema";

// Quick-practice loop, one skill per session (Stage 3 of the AI overhaul,
// docs/AI_OVERHAUL_TODO.md). `skillId` is a required prop now, not an
// internally-managed topic with an in-panel picker to switch it — that
// picker (first a Select, then a Sheet+Command rebuild) is what produced
// most of the race-condition scaffolding this file used to carry
// (keepPreviousData, isFetching gating everywhere, "Finding a question…"
// spinners for a mid-session swap). The choice of topic now happens once,
// on the landing page above this panel (routes/course/practice.tsx),
// before a session starts — the honest structure for "the quiz changes
// per topic" is choose-then-do, not do-while-being-able-to-switch. This
// panel only ever runs against ONE skill for its whole session, so none
// of that machinery is needed here anymore.
//
// The graded result stays on screen until the student clicks "Next item"
// — advancing is explicit, not automatic. The question + graded result
// render through the shared AnswerableCard (hover/selected states,
// disabled-during-pending fix, live mastery band + XP delta all live there,
// not in this file).
//
// Items arrive as a BATCH (one quiz set, POST /practice/{id}/set) rather than
// one generated per "Next item" click. The set is fetched once and the panel
// holds it, advancing `setIndex` locally — so moving to the next question is
// instant, with no per-question generation wait. A fresh set is only fetched
// when the batch is exhausted ("New set") or the topic changes.
// Grading is unchanged: each item is still submitted to /practice/submit and
// graded server-side against its stored answer key.

const SET_SIZE = 5;

type FollowUpTurn = { question: string; answer: string };

function masterySummary(mastery: { level: string; value: number | null }) {
  return `${mastery.level}${mastery.value == null ? "" : ` · ${Math.round(mastery.value * 100)}%`}`;
}

function masteryBandForLevel(level: string) {
  const normalized = level.trim().toLowerCase().replaceAll("_", "-").replaceAll(" ", "-");
  if (normalized === "mastered") return "mastered" as const;
  if (normalized === "proficient") return "proficient" as const;
  if (normalized === "developing") return "developing" as const;
  return "no-evidence" as const;
}

function PracticeRecap({
  results,
  onDone,
  onNewSet,
  isCreatingSet,
  onStudyThese,
}: {
  results: PracticeSetResults;
  onDone: () => void;
  onNewSet: () => void;
  isCreatingSet: boolean;
  onStudyThese?: () => void;
}) {
  const missed = results.questions.filter((question) => question.correct === false);
  const partyPopperRef = useRef<PartyPopperIconHandle | null>(null);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (reduceMotion === false) partyPopperRef.current?.startAnimation();
  }, [reduceMotion]);

  return (
    <StudySurface bar={<SessionBar title="Test results" />}>
      <StudyStream>
        <div className="overflow-hidden border bg-card shadow-sm">
          <header className="border-b bg-muted/30 px-5 py-5 sm:px-7 sm:py-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.08em] text-brand-slate">Test complete</p>
                <h2 className="mt-1 font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                  {results.score.correct}<span className="text-muted-foreground">/{results.score.total}</span>
                  {results.score.percent == null ? null : (
                    <span className="ml-2 align-middle font-mono text-lg font-medium text-muted-foreground">
                      {Math.round(results.score.percent)}%
                    </span>
                  )}
                </h2>
              </div>
              <div className="grid size-12 shrink-0 place-items-center border border-brand-gold/50 bg-brand-gold/15 text-brand-slate">
                <PartyPopperIcon ref={partyPopperRef} size={26} aria-hidden />
              </div>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
              <div className="flex items-center gap-3 border bg-card px-4 py-3">
                <span className="font-mono text-2xl font-semibold tabular-nums text-brand-orange">+{results.totalXp}</span>
                <span className="text-sm text-muted-foreground">XP earned this set</span>
              </div>
              <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 border bg-card px-4 py-3">
                <div className="min-w-0">
                  <p className="mb-1 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">Before</p>
                  <MasteryBand band={masteryBandForLevel(results.masteryBefore.level)} />
                  <p className="mt-1 text-xs text-muted-foreground">
                    {results.masteryBefore.value == null ? "No score yet" : `${Math.round(results.masteryBefore.value * 100)}%`}
                  </p>
                </div>
                <ArrowRightIcon size={18} className="text-brand-orange" aria-hidden />
                <div className="flex min-w-0 items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="mb-1 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">After</p>
                    <MasteryBand band={masteryBandForLevel(results.masteryAfter.level)} />
                    <p className="mt-1 text-xs text-muted-foreground">
                      {results.masteryAfter.value == null ? "No score yet" : `${Math.round(results.masteryAfter.value * 100)}%`}
                    </p>
                  </div>
                  <MasteryRing
                    estimate={results.masteryAfter.value}
                    size={42}
                    strokeWidth={4}
                    label={`Mastery after test: ${masterySummary(results.masteryAfter)}`}
                  />
                </div>
              </div>
            </div>
            <p className="sr-only">
              Mastery changed from {masterySummary(results.masteryBefore)} to {masterySummary(results.masteryAfter)}.
            </p>
          </header>

          <div className="space-y-5 p-5 sm:p-7">
            {missed.length ? (
              <section aria-labelledby="practice-missed-title" className="space-y-3">
                <div className="flex items-baseline justify-between gap-3">
                  <h3 id="practice-missed-title" className="font-display text-lg font-semibold text-foreground">
                    Questions to review
                  </h3>
                  <span className="font-mono text-xs text-muted-foreground">{missed.length} missed</span>
                </div>
                {missed.map((question, index) => (
                  <article key={question.itemId} className="space-y-2 border-l-2 border-brand-orange/60 bg-brand-orange/5 px-4 py-3">
                    <p className="text-sm font-semibold text-foreground">
                      <span className="mr-2 font-mono text-xs text-brand-slate">{String(index + 1).padStart(2, "0")}</span>
                      {question.prompt ?? "Question unavailable"}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Your answer: {question.studentAnswer?.text || "Answer not recorded"}
                    </p>
                    <p className="text-sm text-foreground">
                      Correct answer: {question.correctAnswer?.text ?? "Answer unavailable"}
                    </p>
                    {question.explanation ? (
                      <p className="border-t pt-2 text-sm leading-relaxed text-muted-foreground">{question.explanation}</p>
                    ) : null}
                  </article>
                ))}
              </section>
            ) : (
              <p className="border-l-2 border-brand-green bg-brand-green/5 px-4 py-3 text-sm text-foreground">
                Perfect set. You got every question right.
              </p>
            )}

            <div className="flex flex-wrap gap-2 border-t pt-4">
              <Button variant="orange" onClick={onDone}>
                <CheckIcon size={16} aria-hidden />
                Done
              </Button>
              <Button variant="outline" onClick={onNewSet} disabled={isCreatingSet}>
                <ArrowRightIcon size={16} aria-hidden />
                {isCreatingSet ? "Loading new set…" : "New set"}
              </Button>
              {onStudyThese ? (
                <Button variant="outline" onClick={onStudyThese}>
                  <BookOpenIcon size={16} aria-hidden />
                  Study these cards
                </Button>
              ) : null}
            </div>
          </div>
        </div>
      </StudyStream>
    </StudySurface>
  );
}

export function PracticePanel({
  courseId,
  skillId,
  setId,
  sessionId,
  includesRepeats,
  onExit,
  onSessionReady,
  onOpenSet,
  onStudySet,
}: {
  courseId: string;
  skillId: string;
  /** Run a SAVED set instead of generating a fresh one — the study->test
   * bridge handoff and the retake list both enter test mode this way. The set
   * is per-skill, so skillId still identifies the topic for the bar/copy. */
  setId?: string | null;
  sessionId?: string;
  includesRepeats?: boolean;
  onExit: () => void;
  onSessionReady?: (setId: string, sessionId: string) => void;
  onOpenSet?: (setId: string) => void;
  onStudySet?: (setId: string) => void;
}) {
  const replySessionId = useId();
  const usingSaved = Boolean(setId);
  const bank = useBankStatus(courseId, !usingSaved);
  const bankSkill = bank.data?.skills.find((entry) => entry.skillId === skillId);
  const bankStatus = bankSkill?.status ?? "waiting_content";
  const isBankCourse = bank.data?.bankServing === true;
  const bankNoMaterial = isBankCourse && bankStatus === "no_material";
  const bankUsable = !isBankCourse || bankSkill?.usable === true;
  const skillBuilding = ["waiting_content", "building", "error"].includes(bankStatus);
  const bankBuilding = isBankCourse && !bankNoMaterial && skillBuilding && !bankUsable;
  const bankBuildingUsable = isBankCourse && skillBuilding && bankUsable;
  // Both hooks are always called (Rules of Hooks), but only the active path is
  // enabled. A saved set must never also trigger the POST that creates a new
  // set when the test session mounts.
  const generatedQuery = usePracticeSet(courseId, skillId, SET_SIZE, {
    enabled: !usingSaved && bank.data !== undefined && bankUsable,
  });
  const savedQuery = usePracticeSetById(courseId, setId ?? null);
  const { isLoading, isError, isFetching, refetch } = usingSaved ? savedQuery : generatedQuery;
  const data = usingSaved ? savedQuery.data : generatedQuery.data;
  const preparingResponse = generatedQuery.data?.status === "preparing";
  const refetchGeneratedSet = generatedQuery.refetch;
  const submit = useSubmitPractice(courseId);
  const createNewSet = useGenerateSet(courseId);
  const gamification = useGamification(courseId);
  const followUp = useTutorAsk(courseId);
  const resultsQuery = usePracticeSetResults(courseId, data?.setId ?? setId ?? null);
  const results = resultsQuery.data;

  useEffect(() => {
    if (!usingSaved && preparingResponse && bankUsable) {
      void refetchGeneratedSet();
    }
  }, [usingSaved, preparingResponse, bankUsable, refetchGeneratedSet]);

  // Position within the fetched batch. Local state, not part of the query:
  // the set is immutable for the session, only the cursor over it moves.
  const [setIndex, setSetIndex] = useState(0);
  const [showRecap, setShowRecap] = useState(false);
  const [selectedChoice, setSelectedChoice] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<PracticeSubmitResult | null>(null);
  const [startedAt, setStartedAt] = useState(() => Date.now());
  const [fallbackSessionId] = useState(() => sessionId ?? crypto.randomUUID());
  const submitKeysRef = useRef(new Map<string, string>());
  const [streak, setStreak] = useState(0);
  const [gain, setGain] = useState<{ xp: number } | null>(null);
  const [bandTransition, setBandTransition] = useState<{ from: string; to: string } | null>(null);
  const [followUpTurns, setFollowUpTurns] = useState<FollowUpTurn[]>([]);
  const [pendingFollowUp, setPendingFollowUp] = useState<string | null>(null);

  const lastXpRef = useRef<number | null>(null);
  const prevEstimateRef = useRef<number | null>(null);

  // Reduced-motion is respected at the CALL SITE (celebrate() itself is a
  // plain side effect with no React dependency — see lib/celebrate.ts).
  const reduceMotion = useReducedMotion();
  // Guards the celebration to fire exactly once per set when the recap is
  // ready. A ref keeps rerenders and result refetches from repeating it.
  const celebratedSetRef = useRef<string | null>(null);

  // The gamification summary is derived from immutable evidence; when the
  // submit invalidates it, the refetched delta IS the real +XP for that
  // answer. Compare against the last known snapshot (null until the first
  // load lands — the first snapshot must never read as a gain).
  useEffect(() => {
    if (gamification.data == null) return;
    const prev = lastXpRef.current;
    lastXpRef.current = gamification.data.xp;
    if (prev !== null && gamification.data.xp > prev) {
      setGain({ xp: gamification.data.xp - prev });
    }
  }, [gamification.data]);

  const items = data?.items ?? [];
  const total = items.length;
  const item = items[setIndex] ?? null;
  const completeOnServer = Boolean(results && total > 0 && results.score.answered >= total);
  const recapVisible = showRecap || (completeOnServer && !lastResult && !resultsQuery.isFetching);

  // A brand-new set (new setId) restarts the cursor at its first item. This
  // is an effect on the incoming data, NOT done eagerly in advance(), so that
  // during the in-flight window the OLD set is still fully rendered (its last
  // graded result intact) instead of briefly flashing the old first card with
  // a stale index. Depends on setId, not the items array, so advancing within
  // a batch (which never changes setId) can't trigger a false reset.
  useEffect(() => {
    setSetIndex(0);
    setShowRecap(false);
  }, [data?.setId]);

  const restoredResultsSetRef = useRef<string | null>(null);
  useEffect(() => {
    if (!results || resultsQuery.isFetching || total === 0 || restoredResultsSetRef.current === results.setId) return;
    restoredResultsSetRef.current = results.setId;
    const nextIndex = results.questions.findIndex((question) => !question.answered);
    if (nextIndex >= 0) setSetIndex(nextIndex);
  }, [results, resultsQuery.isFetching, total]);

  const sessionReadyRef = useRef<string | null>(null);
  useEffect(() => {
    if (usingSaved || !data?.setId || sessionReadyRef.current === data.setId) return;
    sessionReadyRef.current = data.setId;
    onSessionReady?.(data.setId, fallbackSessionId);
  }, [usingSaved, data?.setId, fallbackSessionId, onSessionReady]);

  // Reset the per-question UI when the question changes (either a new set
  // fetched, or the cursor advanced to the next item). Keyed on the item id,
  // not the set, so advancing within a batch resets exactly like fetching a
  // new one did before — the student never sees the previous answer's state
  // bleed onto the next card.
  useEffect(() => {
    setSelectedChoice(null);
    setLastResult(null);
    setGain(null);
    setBandTransition(null);
    setFollowUpTurns([]);
    setPendingFollowUp(null);
    setStartedAt(Date.now());
  }, [item?.id]);

  // Celebrate when the results view is ready, not while the last question's
  // feedback is still on screen. The set key keeps refreshes and query updates
  // from firing the same celebration twice during this mount.
  useEffect(() => {
    if (!recapVisible || !completeOnServer || resultsQuery.isFetching || resultsQuery.isError || !results?.setId) return;
    const key = results.setId;
    if (celebratedSetRef.current === key) return;
    celebratedSetRef.current = key;
    if (!reduceMotion) celebrate();
  }, [recapVisible, completeOnServer, resultsQuery.isFetching, resultsQuery.isError, results?.setId, reduceMotion]);

  if (!usingSaved && bank.isLoading)
    return <LoadingPanel label="Checking question availability…" lines={4} />;
  if (!usingSaved && bank.isError)
    return (
      <EmptyState
        title="We could not check question availability"
        description="Reload this page to try again."
      />
    );
  if (!usingSaved && bankNoMaterial)
    return (
      <EmptyState
        title="No course material yet"
        description="This skill doesn&apos;t have course material yet."
      />
    );
  if (!usingSaved && bankBuilding)
    return (
      <LoadingPanel
        label={`Preparing questions (${bankSkill?.mcqReady ?? 0} of ${bankSkill?.mcqTarget ?? 0})`}
        lines={4}
      />
    );
  if (isLoading)
    return (
      <LoadingPanel
        label="Loading your practice set…"
        lines={4}
      />
    );
  if (isError)
    return (
      <EmptyState
        title="We could not load practice"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  if (data?.status === "generating")
    return (
      <LoadingPanel
        label={`Loading your set (${data.readyCount} of ${data.requestedSize} ready)`}
        lines={4}
      />
    );
  if (data?.status === "preparing")
    return (
      <LoadingPanel
        label={`Preparing questions (${bankSkill?.mcqReady ?? 0} of ${bankSkill?.mcqTarget ?? 0})`}
        lines={4}
      />
    );
  if (data?.status === "no_material")
    return (
      <EmptyState
        title="No course material yet"
        description="This skill doesn&apos;t have course material yet."
      />
    );
  if (data && (("available" in data && data.available === false) || data.status === "unavailable"))
    return (
      <EmptyState
        title="This set is no longer available"
        description="Choose another set to continue."
        action={<Button variant="outline" onClick={onExit}>Choose another test</Button>}
      />
    );
  if (data?.status === "failed")
    return (
      <EmptyState
        title="No questions are ready yet"
        description="Questions for this skill are still being prepared."
        action={<Button variant="outline" onClick={() => refetch()}>Try again</Button>}
      />
    );
  if (!item)
    return (
      <EmptyState
        title="Nothing to practice yet"
        description="No questions are available right now."
      />
    );

  if (recapVisible) {
    if (resultsQuery.isError) {
      return (
        <EmptyState
          title="We could not load your results"
          description="Your answers are saved. Try loading the recap again."
          action={<Button variant="outline" onClick={() => void resultsQuery.refetch()}>Retry</Button>}
        />
      );
    }
    if (!results || resultsQuery.isFetching) return <LoadingPanel label="Loading your results…" lines={4} />;
    return (
      <PracticeRecap
        results={results}
        onDone={onExit}
        onNewSet={() => createNewSet.mutate(
          { skillId, size: SET_SIZE },
          { onSuccess: (newSet) => newSet.setId && onOpenSet ? onOpenSet(newSet.setId) : onExit() }
        )}
        isCreatingSet={createNewSet.isPending}
        onStudyThese={onStudySet && results.questions.some((question) => question.correct === false)
          ? () => onStudySet(results.setId)
          : undefined}
      />
    );
  }

  // The last item in the batch: advancing past it opens the durable recap.
  const atSetEnd = setIndex + 1 >= total;

  function advance() {
    if (atSetEnd) {
      setShowRecap(true);
      void resultsQuery.refetch();
    } else {
      setSetIndex((i) => i + 1);
    }
  }

  function handleAnswer(choiceId: string) {
    setSelectedChoice(choiceId);
    const attemptSessionId = sessionId ?? fallbackSessionId;
    const attemptSetId = data?.setId ?? setId ?? "practice";
    const attemptKey = `${attemptSessionId}:${attemptSetId}:${item.id}`;
    let idempotencyKey = submitKeysRef.current.get(attemptKey);
    if (!idempotencyKey) {
      idempotencyKey = crypto.randomUUID();
      submitKeysRef.current.set(attemptKey, idempotencyKey);
    }
    submit.mutate(
      {
        itemId: item.id,
        choiceId,
        latencyMs: Date.now() - startedAt,
        setId: data?.setId,
        sessionId: attemptSessionId,
        idempotencyKey,
      },
      {
        onSuccess: (result) => {
          setLastResult(result);
          void resultsQuery.refetch();
          setStreak((s) => (result.correct ? s + 1 : 0));
          const prev = prevEstimateRef.current;
          prevEstimateRef.current = result.mastery;
          if (prev !== null) {
            setBandTransition({
              from: bandForLabel(prev),
              to: bandForLabel(result.mastery),
            });
          }
        },
      }
    );
  }

  function leaveSet() {
    if (window.confirm("Leave this set? Answers so far are saved.")) onExit();
  }

  function askAboutItem(question: string) {
    setPendingFollowUp(question);
    followUp.mutate(
      {
        question: [
          "You are Kala helping a student with one practice question.",
          "Before the question is graded, guide their reasoning without stating which option is correct. After grading, explain clearly if asked.",
          `Question: ${item.prompt}`,
          `Options: ${item.choices.map((choice) => `${choice.id}: ${choice.label}`).join(" | ")}`,
          lastResult ? `The student was ${lastResult.correct ? "correct" : "incorrect"}.` : "The student has not submitted an answer yet.",
          `Student question: ${question}`,
        ].join("\n\n"),
      },
      {
        onSuccess: (answer) => {
          setFollowUpTurns((turns) => [...turns, { question, answer: answer.answer }]);
          setPendingFollowUp(null);
        },
        onError: () => setPendingFollowUp(null),
      }
    );
  }

  return (
    <StudySurface
      bar={
        <SessionBar
          title="Quick practice"
          progress={{ current: setIndex + 1, total, label: total === 1 ? "question" : "questions" }}
          onBack={leaveSet}
          backLabel="Leave this set"
        />
      }
      dock={
        <ComposeDock
          // Match the Lessons contract: the dock is a visible, locked
          // advance action until server-side grading succeeds. Compose before
          // an answer would make it both look like a tutor and offer an easy
          // path around the practice beat.
          primary={{
            label: !lastResult
              ? "Choose an answer to continue"
              : isFetching
                ? "Loading a new set…"
                : atSetEnd
                  ? "Next"
                  : "Next question",
            onClick: () => {
              if (lastResult && !isFetching) advance();
            },
            disabled: !lastResult || isFetching,
            icon: ArrowRightIcon,
          }}
          onAsk={lastResult ? askAboutItem : undefined}
          askPending={followUp.isPending}
          placeholder="Ask Kala about this question…"
        />
      }
    >
      <StudyStream>
        {bankBuildingUsable ? (
          <p className="border-l-2 border-brand-orange/60 px-3 py-2 text-sm text-muted-foreground">
            More questions on the way.
          </p>
        ) : null}
        {includesRepeats ? (
          <div className="border border-brand-gold/40 bg-brand-gold/10 px-4 py-3 text-sm text-foreground">
            You&apos;ve seen every question for this skill. Here are the ones worth another look.
          </div>
        ) : null}
        <div id="tour-practice-card" className="border bg-card px-5 py-6 sm:px-6">
          <AnswerableCard
            prompt={item.prompt}
            choices={item.choices}
            selectedId={selectedChoice}
            onSelect={handleAnswer}
            choicesAnchorId="tour-practice-choices"
            resultAnchorId="tour-practice-feedback"
            result={
              lastResult
                ? {
                    correct: lastResult.correct,
                    explanation: lastResult.explanation,
                    mastery: lastResult.mastery,
                    correctChoiceId: lastResult.correctOptionId,
                  }
                : null
            }
            isPending={submit.isPending}
            meta={
              <>
                {bandTransition ? (
                  <span className="capitalize">
                    {bandTransition.from} → {bandTransition.to}
                  </span>
                ) : null}
                {streak > 1 ? <span>{streak} in a row</span> : null}
                {gain && gain.xp > 0 ? <span className="text-brand-green">+{gain.xp} XP</span> : null}
              </>
            }
          />
        </div>
        {lastResult && selectedChoice ? (
          <PracticeExplainMore
            courseId={courseId}
            sessionId={sessionId ?? fallbackSessionId}
            item={item}
            selectedChoiceId={selectedChoice}
            result={lastResult}
          />
        ) : null}

        {followUpTurns.map((turn, index) => (
          <div key={`${turn.question}-${index}`} className="space-y-3">
            <UserBlock text={turn.question} />
            <AssistantBlock
              text={turn.answer}
              animationKey={`${courseId}:${replySessionId}:${skillId}:${data?.setId ?? setId ?? "session"}:follow-up:${index}`}
            />
          </div>
        ))}
        {pendingFollowUp ? (
          <div className="space-y-3">
            <UserBlock text={pendingFollowUp} />
            <AssistantBlock pending pendingLabel="Kala is thinking…" />
          </div>
        ) : null}
      </StudyStream>
    </StudySurface>
  );
}

function bandForLabel(estimate: number | null): string {
  if (estimate === null) return "no evidence";
  if (estimate < 0.4) return "developing";
  if (estimate < 0.7) return "proficient";
  return "mastered";
}
