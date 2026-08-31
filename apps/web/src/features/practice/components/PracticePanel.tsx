import { useEffect, useRef, useState } from "react";
import { FlameIcon } from "@/components/ui/flame";
import type { FlameIconHandle } from "@/components/ui/flame";
import { StudySessionShell } from "@/components/study/StudySessionShell";
import { AnswerableCard } from "@/components/study/AnswerableCard";
import { GamificationSummary } from "@/features/gamification";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { useNextPracticeItem, useSubmitPractice } from "@/features/practice/hooks/use-practice";
import { useGamification } from "@/features/gamification";
import { cn } from "@/lib/utils";
import type { PracticeSubmitResult } from "@/features/practice/schema/practice.schema";

// Quick-practice loop: one item at a time, targeted at the student's
// weakest skill. Answering advances automatically. Shared chrome comes from
// StudySessionShell; the question + graded result render through the shared
// AnswerableCard (hover/selected states, disabled-during-pending fix, live
// mastery band + XP delta all live there now, not in this file).

export function PracticePanel({ courseId }: { courseId: string }) {
  const { data, isLoading, isError, refetch } = useNextPracticeItem(courseId);
  const submit = useSubmitPractice(courseId);
  const gamification = useGamification(courseId);

  const [selectedChoice, setSelectedChoice] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<PracticeSubmitResult | null>(null);
  const [startedAt, setStartedAt] = useState(() => Date.now());
  const [sessionAnswers, setSessionAnswers] = useState(0);
  const [streak, setStreak] = useState(0);
  const [gain, setGain] = useState<{ xp: number; streakDays: number } | null>(null);
  const [bandTransition, setBandTransition] = useState<{ from: string; to: string } | null>(null);

  const lastXpRef = useRef<number | null>(null);
  const prevEstimateRef = useRef<number | null>(null);
  const prevStreakRef = useRef(streak);

  // Streak went UP -> the flame draws once (real state change, not hover).
  useEffect(() => {
    if (streak > prevStreakRef.current) {
      flameRef.current?.startAnimation();
    }
    prevStreakRef.current = streak;
  }, [streak]);
  const flameRef = useRef<FlameIconHandle | null>(null);

  // The gamification summary is derived from immutable evidence; when the
  // submit invalidates it, the refetched delta IS the real +XP for that
  // answer. Compare against the last known snapshot (null until the first
  // load lands — the first snapshot must never read as a gain).
  useEffect(() => {
    if (gamification.data == null) return;
    const prev = lastXpRef.current;
    lastXpRef.current = gamification.data.xp;
    if (prev !== null && gamification.data.xp > prev) {
      setGain({ xp: gamification.data.xp - prev, streakDays: gamification.data.streakDays });
    }
  }, [gamification.data]);

  useEffect(() => {
    setSelectedChoice(null);
    setLastResult(null);
    setGain(null);
    setBandTransition(null);
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
        description="Skills for this course haven't been set up yet."
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

  return (
    <StudySessionShell
      progress={{ current: sessionAnswers, total: 0, label: "answered" }}
      right={
        <span id="tour-practice-streak">
          <GamificationSummary courseId={courseId} />
        </span>
      }
    >
      <Card id="tour-practice-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            Quick practice
            <span
              className="flex items-center gap-1.5 font-mono text-xs font-normal text-muted-foreground"
              title="Correct answers in a row this session"
            >
              <FlameIcon
                ref={flameRef}
                size={16}
                className={streak > 0 ? "text-brand-gold" : "text-muted-foreground/50"}
                aria-hidden
              />
              {streak}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* Session momentum: an 8-segment rail, not a fixed total — the
              loop has no end, so this shows movement instead of progress. */}
          <div className="mb-5 flex gap-1" aria-hidden>
            {Array.from({ length: 8 }).map((_, i) => (
              <span
                key={i}
                className={cn(
                  "h-1 flex-1 rounded-full transition-colors",
                  i < sessionAnswers % 8 ? "bg-brand-orange" : "bg-muted"
                )}
              />
            ))}
          </div>

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
                {gain && gain.xp > 0 ? <span className="text-brand-green">+{gain.xp} XP</span> : null}
                {gain ? <span>{gain.streakDays}-day streak</span> : null}
              </>
            }
          />

          {lastResult ? (
            <div className="mt-4">
              <Button variant="orange" onClick={() => refetch()}>
                Next item
              </Button>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </StudySessionShell>
  );
}

function bandForLabel(estimate: number | null): string {
  if (estimate === null) return "no evidence";
  if (estimate < 0.4) return "developing";
  if (estimate < 0.7) return "proficient";
  return "mastered";
}
