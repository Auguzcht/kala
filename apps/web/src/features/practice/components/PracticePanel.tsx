import { useEffect, useRef, useState } from "react";
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
import { useNextPracticeItem, useSubmitPractice } from "@/features/practice/hooks/use-practice";
import { useGamification } from "@/features/gamification";
import { useTutorAsk } from "@/features/tutor";
import type { PracticeSubmitResult } from "@/features/practice/schema/practice.schema";

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
// — advancing is explicit, not automatic (an earlier version force-
// refetched on submit, which is what was wiping the result before it
// could be read). The question + graded result render through the shared
// AnswerableCard (hover/selected states, disabled-during-pending fix,
// live mastery band + XP delta all live there, not in this file).

type FollowUpTurn = { question: string; answer: string };

export function PracticePanel({
  courseId,
  skillId,
  onExit,
}: {
  courseId: string;
  skillId: string;
  onExit: () => void;
}) {
  const { data, isLoading, isError, isFetching, refetch } = useNextPracticeItem(courseId, skillId);
  const submit = useSubmitPractice(courseId);
  const gamification = useGamification(courseId);
  const followUp = useTutorAsk(courseId);

  const [selectedChoice, setSelectedChoice] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<PracticeSubmitResult | null>(null);
  const [startedAt, setStartedAt] = useState(() => Date.now());
  const [sessionAnswers, setSessionAnswers] = useState(0);
  const [streak, setStreak] = useState(0);
  const [gain, setGain] = useState<{ xp: number } | null>(null);
  const [bandTransition, setBandTransition] = useState<{ from: string; to: string } | null>(null);
  const [followUpTurns, setFollowUpTurns] = useState<FollowUpTurn[]>([]);
  const [pendingFollowUp, setPendingFollowUp] = useState<string | null>(null);

  const lastXpRef = useRef<number | null>(null);
  const prevEstimateRef = useRef<number | null>(null);

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

  useEffect(() => {
    setSelectedChoice(null);
    setLastResult(null);
    setGain(null);
    setBandTransition(null);
    setFollowUpTurns([]);
    setPendingFollowUp(null);
    setStartedAt(Date.now());
  }, [data?.item?.id]);

  if (isLoading)
    return <LoadingPanel label="Finding your next item…" lines={4} />;
  if (isError)
    return (
      <EmptyState
        title="We could not load practice"
        description="Check your connection and try again."
        action={<Button variant="outline" onClick={() => refetch()}>Retry</Button>}
      />
    );
  if (!data?.item)
    return (
      <EmptyState
        title="Nothing to practice yet"
        description="This skill isn't set up for practice yet."
      />
    );

  const item = data.item;

  function handleAnswer(choiceId: string) {
    setSelectedChoice(choiceId);
    submit.mutate(
      { itemId: item.id, choiceId, latencyMs: Date.now() - startedAt },
      {
        onSuccess: (result) => {
          setLastResult(result);
          setSessionAnswers((n) => n + 1);
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
          progress={{ current: sessionAnswers, total: 0, label: "answered" }}
          onBack={onExit}
          backLabel="Choose another topic"
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
                ? "Finding your next question…"
                : "Next item",
            onClick: () => {
              if (lastResult && !isFetching) refetch();
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

        {followUpTurns.map((turn, index) => (
          <div key={`${turn.question}-${index}`} className="space-y-3">
            <UserBlock text={turn.question} />
            <AssistantBlock text={turn.answer} />
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
