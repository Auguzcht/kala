import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";
import { MasteryBand, BAND_LABELS } from "@/components/kala/mastery-band";
import type { MasteryBand as MasteryBandType } from "@/features/twin";

// The mastery-delta moment. Built for one specific gap: nothing in the
// product currently shows the twin actually moving. A student finishes a
// session and the mastery change happens off-screen — they'd have to
// navigate to Twin and remember what it looked like before. That is the
// entire "digital learning twin" thesis, and it had no moment.
//
// This renders once, right after a diagnostic (or any future bulk-graded
// session) completes: one row per skill touched, prior band -> posterior
// band, with a short staggered reveal so the movement reads as movement,
// not a static table. A skill with no prior evidence renders "No evidence
// yet -> <band>" rather than hiding the row or faking a 0.0 starting point.
//
// Each row also carries a small four-step mastery track with a marker that
// slides from the prior position to the posterior position as its row
// reveals — the text (kept, for accessibility and at-a-glance reading)
// says WHAT moved, the track shows WHERE it sits on the whole scale, which
// a single before/after label can't communicate on its own.
//
// Deliberately its own component, not folded into DiagnosticPanel: any
// future bulk-graded surface (a full lesson's comprehension checks, a
// multi-question practice set) can reuse this exact moment.

export type MasteryDeltaRow = {
  skillId: string;
  skillName: string;
  priorBand: MasteryBandType;
  posteriorBand: MasteryBandType;
};

const BAND_ORDER: Record<MasteryBandType, number> = {
  "no-evidence": 0,
  developing: 1,
  proficient: 2,
  mastered: 3,
};

const TRACK_STEPS: MasteryBandType[] = ["no-evidence", "developing", "proficient", "mastered"];

const STEP_FILL: Record<MasteryBandType, string> = {
  "no-evidence": "bg-muted-foreground/30",
  developing: "bg-band-developing",
  proficient: "bg-band-proficient",
  mastered: "bg-band-mastered",
};

function trackPosition(band: MasteryBandType): number {
  return (BAND_ORDER[band] / (TRACK_STEPS.length - 1)) * 100;
}

function MasteryTrack({
  priorBand,
  posteriorBand,
  animate: shouldAnimate,
}: {
  priorBand: MasteryBandType;
  posteriorBand: MasteryBandType;
  animate: boolean;
}) {
  const reduceMotion = useReducedMotion();
  const posteriorIndex = BAND_ORDER[posteriorBand];
  const advanced = posteriorIndex > BAND_ORDER[priorBand];

  return (
    <div
      className="relative flex h-1.5 w-20 shrink-0 items-center gap-[3px]"
      aria-hidden
    >
      {TRACK_STEPS.map((step, i) => (
        <span
          key={step}
          className={cn(
            "h-full flex-1 rounded-full transition-opacity duration-500",
            STEP_FILL[step],
            i <= posteriorIndex ? "opacity-100" : "opacity-30"
          )}
        />
      ))}
      <motion.span
        className={cn(
          "absolute top-1/2 size-2.5 -translate-y-1/2 rounded-full border-2 border-card shadow-sm",
          advanced ? "bg-brand-orange" : "bg-foreground/70"
        )}
        style={{ marginLeft: -5 }}
        initial={{ left: `${trackPosition(priorBand)}%` }}
        animate={{ left: `${trackPosition(shouldAnimate ? posteriorBand : priorBand)}%` }}
        transition={reduceMotion ? { duration: 0 } : { duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      />
    </div>
  );
}

export function MasteryDelta({
  rows,
  onRevealComplete,
}: {
  rows: MasteryDeltaRow[];
  /** Fires once every row has finished its staggered reveal — the natural
   * moment to follow up with something else (a closing dialog, a CTA),
   * rather than guessing a fixed timeout from outside this component. */
  onRevealComplete?: () => void;
}) {
  const [revealed, setRevealed] = useState(0);

  // Stagger the reveal so each skill's movement is legible on its own,
  // rather than every row appearing at once and reading as a static table.
  // Respect prefers-reduced-motion: reveal everything immediately.
  useEffect(() => {
    setRevealed(0);
    if (rows.length === 0) {
      onRevealComplete?.();
      return;
    }
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) {
      setRevealed(rows.length);
      onRevealComplete?.();
      return;
    }
    const timers = rows.map((_, i) =>
      window.setTimeout(() => setRevealed((n) => Math.max(n, i + 1)), i * 220)
    );
    // Fires after the last row's reveal timer AND its own track-slide
    // animation (700ms) have both had time to finish, not just the reveal.
    const completeTimer = window.setTimeout(
      () => onRevealComplete?.(),
      (rows.length - 1) * 220 + 700
    );
    return () => {
      timers.forEach(window.clearTimeout);
      window.clearTimeout(completeTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- onRevealComplete intentionally excluded: a new function identity each render must not restart the reveal.
  }, [rows]);

  if (rows.length === 0) return null;

  const moved = rows.filter((r) => BAND_ORDER[r.posteriorBand] > BAND_ORDER[r.priorBand]).length;

  return (
    <div className="border bg-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-[0.05em] text-brand-slate">
          Your twin just updated
        </span>
        {moved > 0 ? (
          <span className="text-xs font-semibold text-brand-orange">
            {moved} skill{moved === 1 ? "" : "s"} moved
          </span>
        ) : null}
      </div>
      <div className="divide-y divide-border">
        {rows.map((row, i) => {
          const isRevealed = i < revealed;
          const advanced = BAND_ORDER[row.posteriorBand] > BAND_ORDER[row.priorBand];
          return (
            <div
              key={row.skillId}
              className={cn(
                "flex items-center gap-3 py-2.5 transition-all duration-300",
                isRevealed ? "translate-x-0 opacity-100" : "-translate-x-1 opacity-0"
              )}
            >
              <span className="min-w-0 flex-1 truncate text-[13px] text-foreground">
                {row.skillName}
              </span>
              <MasteryTrack
                priorBand={row.priorBand}
                posteriorBand={row.posteriorBand}
                animate={isRevealed}
              />
              <span className="flex shrink-0 items-center gap-2">
                <span
                  className="text-[10.5px] text-muted-foreground"
                  title="Before this session"
                >
                  {BAND_LABELS[row.priorBand]}
                </span>
                <span aria-hidden className="text-muted-foreground/50">
                  →
                </span>
                <MasteryBand
                  band={row.posteriorBand}
                  className={advanced ? "ring-1 ring-brand-orange/40" : undefined}
                />
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
