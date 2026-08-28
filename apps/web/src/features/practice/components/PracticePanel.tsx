import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Flame, XCircle } from "lucide-react";
import { useNextPracticeItem, useSubmitPractice } from "@/features/practice/hooks/use-practice";
import { useGamification } from "@/features/gamification";
import { MasteryBand, bandFor } from "@/components/kala";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingPanel } from "@/components/shared/LoadingPanel";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { MasteryBand as Band } from "@/features/twin";
import type { PracticeSubmitResult } from "@/features/practice/schema/practice.schema";

// Quick-practice loop: one item at a time, targeted at the student's
// weakest skill. Answering advances automatically. The session strip shows
// movement (answers + streak rail); after each answer the graded result
// renders the REAL twin deltas — mastery band transition and the +XP gain
// computed from the gamification summary (derived from evidence, never a
// client balance).

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
  const [bandNow, setBandNow] = useState<Band | null>(null);
  const [bandTransition, setBandTransition] = useState<{ from: Band; to: Band } | null>(null);

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
      setGain({ xp: gamification.data.xp - prev, streakDays: gamification.data.streakDays });
    }
  }, [gamification.data]);

  useEffect(() => {
    setSelectedChoice(null);
    setLastResult(null);
    setGain(null);
    setBandNow(null);
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
          // Mastery band transition: compare against the previous answer's
          // estimate (null on the first answer — show just the current band).
          const prev = prevEstimateRef.current;
          prevEstimateRef.current = result.mastery;
          const to = bandFor(result.mastery).band;
          setBandNow(to);
          setBandTransition(prev === null ? null : { from: bandFor(prev).band, to });
        },
      }
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick practice</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Session movement: answers rail + streak. Not a fixed total — the
            loop has no end, so this shows momentum instead of progress. */}
        <div className="flex items-center gap-3">
          <div className="flex flex-1 gap-1" aria-hidden>
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
          <span
            className="flex items-center gap-1.5 font-mono text-xs text-muted-foreground"
            title="Correct answers in a row this session"
          >
            <Flame
              className={cn("size-3.5", streak > 0 ? "text-brand-gold" : "text-muted-foreground/50")}
              aria-hidden
            />
            {streak}
          </span>
          <span className="font-mono text-xs text-muted-foreground">{sessionAnswers} answered</span>
        </div>

        <div className="space-y-4">
          <p className="font-medium">{item.prompt}</p>
          <div className="flex flex-col gap-2">
            {item.choices.map((c) => (
              <Button
                key={c.id}
                variant={selectedChoice === c.id ? "orange" : "outline"}
                disabled={!!lastResult}
                onClick={() => handleAnswer(c.id)}
                className="h-auto justify-start whitespace-normal text-left transition-colors hover:border-brand-orange/40 hover:bg-accent/40"
              >
                {c.label}
              </Button>
            ))}
          </div>
        </div>

        {lastResult ? (
          <div className="space-y-3">
            <div className="flex items-start gap-2.5">
              {lastResult.correct ? (
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-brand-green" aria-hidden />
              ) : (
                <XCircle className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden />
              )}
              <div className="space-y-1">
                <p
                  className={cn(
                    "text-sm font-semibold",
                    lastResult.correct ? "text-brand-green" : "text-destructive"
                  )}
                >
                  {lastResult.correct ? "Correct." : "Not quite."}
                </p>
                {lastResult.explanation ? (
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {lastResult.explanation}
                  </p>
                ) : null}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t pt-2.5 font-mono text-xs text-muted-foreground">
              {bandNow ? (
                <span className="flex items-center gap-1.5">
                  mastery <MasteryBand band={bandNow} />
                </span>
              ) : null}
              {bandTransition ? (
                <span className="capitalize">
                  {bandTransition.from} → {bandTransition.to}
                </span>
              ) : null}
              {gain && gain.xp > 0 ? <span className="text-brand-green">+{gain.xp} XP</span> : null}
              {gain ? <span>{gain.streakDays}-day streak</span> : null}
            </div>

            <Button variant="orange" onClick={() => refetch()}>
              Next item
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
