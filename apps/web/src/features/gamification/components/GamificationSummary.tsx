import { useEffect, useRef } from "react";
import { FlameIcon } from "@/components/ui/flame";
import type { FlameIconHandle } from "@/components/ui/flame";
import { useGamification } from "@/features/gamification/hooks/use-gamification";
import { cn } from "@/lib/utils";

// Compact instrument readout for the top bar: streak + total XP, in mono,
// derived from the twin's evidence log (never a client-side balance). The
// flame is gold only when the streak is alive — never color alone, the
// number is always next to it.

export function GamificationSummary({
  courseId,
  className,
}: {
  courseId: string;
  className?: string;
}) {
  const { data, isLoading } = useGamification(courseId);

  const flameRef = useRef<FlameIconHandle | null>(null);
  const prevStreakRef = useRef<number | null>(null);
  useEffect(() => {
    const s = data?.streakDays ?? 0;
    if (prevStreakRef.current !== null && s > prevStreakRef.current) {
      flameRef.current?.startAnimation();
    }
    prevStreakRef.current = s;
  }, [data?.streakDays]);

  if (isLoading || !data) return null;
  const alive = data.streakDays > 0;

  return (
    <div
      className={cn("flex items-center gap-3", className)}
      title={
        data.badges.length > 0
          ? `${data.attempts} attempts · ${data.correct} correct · ${data.badges.length} badges`
          : `${data.attempts} attempts · ${data.correct} correct`
      }
    >
      <span className="flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
        <FlameIcon
          ref={flameRef}
          size={14}
          className={alive ? "text-brand-gold" : "text-muted-foreground/50"}
          aria-hidden
        />
        {data.streakDays}
      </span>
      <span className="font-mono text-xs text-foreground">{data.xp} XP</span>
    </div>
  );
}
