import { motion, useReducedMotion } from "motion/react";
import { SlidingNumber } from "@/components/motion/sliding-number";
import { cn } from "@/lib/utils";

// MasteryRing — the continuous 0-to-1 mastery estimate as a ring that fills,
// never a flat bar (brief: "mastery rings that fill and animate on update").
// Bands run neutral-to-gold: red is reserved for the at-risk axis, a
// different object, so it never appears here.
//
// `estimate` is 0..1. `band` maps the estimate to a qualitative label for
// screen readers; the numeric value stays secondary (hover title). The
// center digit rolls when the estimate changes (SlidingNumber) — the
// movement IS the mastery update; reduced motion renders the plain number.

export type MasteryBand = "no-evidence" | "developing" | "proficient" | "mastered";

export function bandFor(estimate: number | null): { band: MasteryBand; label: string } {
  if (estimate === null) return { band: "no-evidence", label: "No evidence yet" };
  if (estimate < 0.4) return { band: "developing", label: "Developing" };
  if (estimate < 0.7) return { band: "proficient", label: "Proficient" };
  return { band: "mastered", label: "Mastered" };
}

const bandColor: Record<MasteryBand, string> = {
  "no-evidence": "var(--border)",
  developing: "var(--brand-gold)",
  proficient: "var(--brand-gold)",
  mastered: "var(--brand-gold)",
};

type MasteryRingProps = {
  estimate: number | null;
  size?: number;
  strokeWidth?: number;
  className?: string;
  label?: string;
};

export function MasteryRing({
  estimate,
  size = 56,
  strokeWidth = 5,
  className,
  label,
}: MasteryRingProps) {
  const reduceMotion = useReducedMotion();
  const { band, label: bandLabel } = bandFor(estimate);
  const r = (size - strokeWidth) / 2;
  const c = 2 * Math.PI * r;
  const filled = estimate === null ? 0 : Math.max(0, Math.min(1, estimate));
  const color = estimate === null ? bandColor["no-evidence"] : bandColor[band];

  return (
    <div
      className={cn("relative inline-grid place-items-center", className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={label ?? `${bandLabel}${estimate === null ? "" : `, ${Math.round(filled * 100)} percent`}`}
      title={estimate === null ? bandLabel : `${bandLabel} · ${Math.round(filled * 100)}%`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth={strokeWidth}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={false}
          animate={{ strokeDashoffset: c * (1 - filled) }}
          transition={reduceMotion ? { duration: 0 } : { duration: 0.6, ease: [0.32, 0.72, 0, 1] }}
        />
      </svg>
      <div className="absolute font-mono text-xs font-medium tabular-nums text-foreground">
        {estimate === null ? "—" : reduceMotion ? `${Math.round(filled * 100)}` : <SlidingNumber value={Math.round(filled * 100)} />}
      </div>
    </div>
  );
}
