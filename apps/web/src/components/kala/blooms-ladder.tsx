import { cn } from "@/lib/utils";
import type { TwinSkill } from "@/features/twin";

// Bloom's ladder — the six-rung axis made visible (the brief's recurring
// structure). Each rung shows how many skills sit at that level; the orange
// tick means at least one skill there has evidence. Used on the twin and
// later the heatmap and badges. Structure that carries real meaning.

const LEVELS = [
  "remember",
  "understand",
  "apply",
  "analyze",
  "evaluate",
  "create",
] as const;

export function BloomsLadder({ skills, className }: { skills: TwinSkill[]; className?: string }) {
  const byLevel = LEVELS.map((level) => {
    const at = skills.filter((s) => (s.bloomLevel ?? "").toLowerCase() === level);
    return { level, count: at.length, hasEvidence: at.some((s) => s.attempts > 0) };
  });

  return (
    <div className={cn("flex items-stretch gap-1", className)} aria-label="Bloom's taxonomy levels">
      {byLevel.map(({ level, count, hasEvidence }) => (
        <div
          key={level}
          className={cn(
            "flex flex-1 flex-col items-center gap-1 border px-1 py-2",
            hasEvidence ? "border-brand-orange/25 bg-brand-orange/5" : "border-border bg-card"
          )}
          title={`${level}${hasEvidence ? " — evidence recorded" : " — no evidence yet"}`}
        >
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              hasEvidence ? "bg-brand-orange" : "bg-border"
            )}
          />
          <span className="text-[9px] font-semibold uppercase tracking-wide text-muted-foreground">
            {level}
          </span>
          <span className="font-mono text-[10px] text-foreground">{count}</span>
        </div>
      ))}
    </div>
  );
}
