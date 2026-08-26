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
// twin and the instructor drill-down. Skills as axes; no-evidence skills
// sit at the center (honest, they fill in as practice happens).

const chartConfig = {
  mastery: { label: "Mastery", color: "var(--chart-3)" },
} satisfies ChartConfig;

export function MasteryRadar({ skills, className }: { skills: TwinSkill[]; className?: string }) {
  const data = skills.map((s) => ({ skill: s.name, mastery: s.estimate ?? 0 }));
  const noEvidence = skills.filter((s) => s.estimate === null);

  return (
    <div className={cn(className)}>
      <ChartContainer config={chartConfig} className="mx-auto aspect-square max-h-[300px]">
        <RadarChart data={data}>
          <PolarGrid stroke="var(--border)" />
          <PolarAngleAxis
            dataKey="skill"
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          />
          <Radar
            dataKey="mastery"
            stroke="var(--chart-3)"
            fill="var(--chart-3)"
            fillOpacity={0.35}
          />
          <ChartTooltip content={<ChartTooltipContent />} />
        </RadarChart>
      </ChartContainer>
      {noEvidence.length > 0 ? (
        <p className="mt-2 text-center text-xs text-muted-foreground">
          {noEvidence.length === 1
            ? "One skill has no evidence yet"
            : `${noEvidence.length} skills have no evidence yet`}{" "}
          — they sit at the center until they're practiced.
        </p>
      ) : null}
    </div>
  );
}
