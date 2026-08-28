import { motion, useReducedMotion } from "motion/react";
import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
} from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { cn } from "@/lib/utils";
import type { TwinSkill } from "@/features/twin";

// Mastery radar — the twin's signature shape, reused on the student's own
// twin and the instructor drill-down. Aggregated to the SIX Bloom-level
// nodes (Remember → Create, the same order as BloomsLadder): one spoke per
// skill stops being legible past ~8 skills (labels overlap and clip), while
// six stable nodes never reflow as skills are added. Per-skill detail lives
// in the Skills list below the radar. No-evidence skills sit at the center
// (honest, they fill in as practice happens).
//
// `pulseKey` drives the motion contract from DESIGN.md ("subtle pulse when
// an evidence event updates a node"): pass the evidence count (or latest
// event id) and the radar remounts with a soft fade when a new event lands;
// recharts also morphs the polygon to the new values. Reduced motion sets
// the transition to zero, matching the mastery-ring reference.

const BLOOM_ORDER = [
  "remember",
  "understand",
  "apply",
  "analyze",
  "evaluate",
  "create",
];

const chartConfig = {
  mastery: { label: "Avg mastery", color: "var(--chart-3)" },
} satisfies ChartConfig;

export function MasteryRadar({
  skills,
  className,
  pulseKey,
}: {
  skills: TwinSkill[];
  className?: string;
  pulseKey?: string | number;
}) {
  const reduceMotion = useReducedMotion();

  const buckets = new Map<string, { total: number; count: number }>();
  for (const s of skills) {
    const level = (s.bloomLevel ?? "other").toLowerCase();
    const b = buckets.get(level) ?? { total: 0, count: 0 };
    b.total += s.estimate ?? 0;
    b.count += 1;
    buckets.set(level, b);
  }
  const keys = BLOOM_ORDER.filter((k) => buckets.has(k));
  if (buckets.has("other")) keys.push("other");

  const data = keys.map((level) => {
    const b = buckets.get(level)!;
    return { level, mastery: b.total / b.count, count: b.count };
  });

  const noEvidence = skills.filter((s) => s.estimate === null).length;

  return (
    <motion.div
      key={pulseKey}
      initial={pulseKey === undefined ? false : { opacity: 0.65 }}
      animate={{ opacity: 1 }}
      transition={reduceMotion ? { duration: 0 } : { duration: 0.5 }}
      className={cn(className)}
    >
      <ChartContainer config={chartConfig} className="mx-auto aspect-square max-h-[300px]">
        <RadarChart data={data}>
          <PolarGrid stroke="var(--border)" />
          <PolarAngleAxis
            dataKey="level"
            tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
          />
          <Radar
            dataKey="mastery"
            stroke="var(--chart-3)"
            fill="var(--chart-3)"
            fillOpacity={0.35}
            isAnimationActive={!reduceMotion}
          />
          <ChartTooltip content={<ChartTooltipContent />} />
        </RadarChart>
      </ChartContainer>
      {noEvidence > 0 ? (
        <p className="mt-2 text-center text-xs text-muted-foreground">
          {noEvidence === 1
            ? "One skill has no evidence yet"
            : `${noEvidence} skills have no evidence yet`}{" "}
          — they sit at the center until they're practiced.
        </p>
      ) : null}
    </motion.div>
  );
}
