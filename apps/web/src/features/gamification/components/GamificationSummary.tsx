import { useEffect, useRef } from "react";
import { useReducedMotion } from "motion/react";
import { toast } from "sonner";
import { FlameIcon } from "@/components/ui/flame";
import type { FlameIconHandle } from "@/components/ui/flame";
import { SlidingNumber } from "@/components/motion/sliding-number";
import { useGamification } from "@/features/gamification/hooks/use-gamification";
import { cn } from "@/lib/utils";

// Compact instrument readout for the top bar: streak + total XP, in mono,
// derived from the twin's evidence log (never a client-side balance). The
// flame is gold only when the streak is alive — never color alone, the
// number is always next to it. Streak and XP digits roll on change
// (SlidingNumber, reduced-motion gated), and a badge earned while the
// student is anywhere in the workspace fires a toast — the badge is
// otherwise only visible in this bar's tooltip, so the toast is the moment
// it is actually felt.

export function GamificationSummary({
  courseId,
  className,
}: {
  courseId: string;
  className?: string;
}) {
  const { data, isLoading } = useGamification(courseId);
  const reduceMotion = useReducedMotion();

  const flameRef = useRef<FlameIconHandle | null>(null);
  const prevStreakRef = useRef<number | null>(null);
  useEffect(() => {
    const s = data?.streakDays ?? 0;
    if (prevStreakRef.current !== null && s > prevStreakRef.current) {
      flameRef.current?.startAnimation();
    }
    prevStreakRef.current = s;
  }, [data?.streakDays]);

  // A badge crossing is a real, cross-context achievement: it happens in
  // the top bar while the student is mid-practice or mid-lesson, so an
  // inline panel cannot announce it. The toast is the announcement.
  const prevBadgeCountRef = useRef<number | null>(null);
  useEffect(() => {
    const count = data?.badges.length ?? 0;
    if (prevBadgeCountRef.current !== null && count > prevBadgeCountRef.current) {
      const newest = data?.badges[count - 1];
      if (newest) {
        toast.success("Badge earned", {
          description: `${newest.label} · ${newest.tier}`,
        });
      }
    }
    prevBadgeCountRef.current = count;
  }, [data?.badges]);

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
      <div className="flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
        <FlameIcon
          ref={flameRef}
          size={14}
          className={alive ? "text-brand-gold" : "text-muted-foreground/50"}
          aria-hidden
        />
        {reduceMotion ? data.streakDays : <SlidingNumber value={data.streakDays} />}
      </div>
      <div className="flex items-center gap-1 font-mono text-xs text-foreground">
        {reduceMotion ? data.xp : <SlidingNumber value={data.xp} />}
        <span className="text-muted-foreground">XP</span>
      </div>
    </div>
  );
}

