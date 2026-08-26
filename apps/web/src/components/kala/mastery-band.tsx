import { cn } from "@/lib/utils";
import type { MasteryBand } from "@/features/twin";

// Qualitative mastery band, neutral-to-gold. Red never enters this scale;
// it belongs to the at-risk axis (instructor surface, a different object).
// The numeric estimate stays secondary (hover/detail), never the headline.

export const BAND_LABELS: Record<MasteryBand, string> = {
  "no-evidence": "No evidence yet",
  developing: "Developing",
  proficient: "Proficient",
  mastered: "Mastered",
};

const BAND_STYLES: Record<MasteryBand, string> = {
  "no-evidence": "border-border bg-muted text-muted-foreground",
  developing: "border-band-developing bg-band-developing text-band-developing-fg",
  proficient: "border-band-proficient bg-band-proficient text-band-proficient-fg",
  mastered: "border-band-mastered bg-band-mastered text-band-mastered-fg",
};

export function MasteryBand({ band, className }: { band: MasteryBand; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded-sm border px-2 py-0.5 text-[10.5px] font-semibold",
        BAND_STYLES[band],
        className
      )}
      title={band === "no-evidence" ? undefined : "Estimate shown on hover in the full twin"}
    >
      {BAND_LABELS[band]}
    </span>
  );
}
