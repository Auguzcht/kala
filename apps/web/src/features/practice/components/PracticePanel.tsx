import { useEffect, useRef, useState } from "react";
import { StudySessionShell } from "@/components/study/StudySessionShell";
import { AnswerableCard } from "@/components/study/AnswerableCard";
import { TopicPicker, TOPIC_AUTO } from "@/components/study/TopicPicker";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useNextPracticeItem, useSubmitPractice } from "@/features/practice/hooks/use-practice";
import { useGamification } from "@/features/gamification";
import { useTwin } from "@/features/twin";
import type { PracticeSubmitResult } from "@/features/practice/schema/practice.schema";

// Quick-practice loop: one item at a time, defaulting to the student's
// weakest skill but overridable via the topic picker. The graded result
// stays on screen until the student clicks "Next item" — advancing is
// explicit, not automatic (an earlier version force-refetched on submit,
// which is what was wiping the result before it could be read). Shared
// chrome comes from StudySessionShell, including its own "N answered"
// progress readout, which is the ONE place session progress is shown now
// (a second, separately-animated segmented rail used to live in this file
// too; two progress indicators for the same number read as a bug, not a
// feature, and one of them visibly moved the instant an answer was
// picked, before the student had even read their result). The question +
// graded result render through the shared AnswerableCard (hover/selected
// states, disabled-during-pending fix, live mastery band +
// XP delta all live there now, not in this file).

export function PracticePanel({ courseId }: { courseId: string }) {
  const [selectedTopic, setSelectedTopic] = useState(TOPIC_AUTO);
  const activeSkillId = selectedTopic === TOPIC_AUTO ? undefined : selectedTopic;
  const { data, isLoading, isFetching, isError, refetch } = useNextPracticeItem(courseId, activeSkillId);
  const submit = useSubmitPractice(courseId);
  const gamification = useGamification(courseId);
  const twin = useTwin(courseId);

  const [selectedChoice, setSelectedChoice] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<PracticeSubmitResult | null>(null);
  const [startedAt, setStartedAt] = useState(() => Date.now());
  const [sessionAnswers, setSessionAnswers] = useState(0);
  const [streak, setStreak] = useState(0);
  const [gain, setGain] = useState<{ xp: number } | null>(null);
  const [bandTransition, setBandTransition] = useState<{ from: string; to: string } | null>(null);

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
    setStartedAt(Date.now());
  }, [data?.item?.id]);

  function handleTopicChange(topic: string) {
    setSelectedTopic(topic);
    // Switching topics reads as starting a focused sub-session, not a
    // continuation of the last one's momentum — reset the visible counters
    // so "3 answered" / a live streak don't carry an unrelated topic's
    // history into the new one. The actual mastery data (twin, XP) is
    // untouched, this only resets this panel's own session-local display.
    setSessionAnswers(0);
    setStreak(0);
  }

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
    >
      <Card id="tour-practice-card">
        <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="flex items-center gap-2.5">
            Quick practice
            {isFetching && !isLoading ? (
              <span className="flex items-center gap-1.5 text-xs font-normal text-muted-foreground">
                <Spinner className="size-3.5" /> Finding a question…
              </span>
            ) : null}
          </CardTitle>
          <TopicPicker
            skills={twin.data?.skills ?? []}
            value={selectedTopic}
            onChange={handleTopicChange}
            disabled={isLoading || isFetching || submit.isPending}
          />
        </CardHeader>
        <CardContent>
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
            isPending={submit.isPending || isFetching}
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
