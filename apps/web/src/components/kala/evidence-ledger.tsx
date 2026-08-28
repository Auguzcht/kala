import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { EvidenceEvent } from "@/features/twin";

// Evidence ledger — the append-only stream. Monospaced, nothing edits or
// deletes; each event slid in when it happened and stays. This is the
// research dataset made visible. Color is never the only signal: every row
// carries a type label + outcome word.
//
// Motion: new rows enter with a short slide-in (AnimatePresence + motion.li,
// initial=false so a page load doesn't animate the whole history — only rows
// that LAND after mount). Reduced motion sets the duration to zero,
// matching the mastery-ring reference implementation.

const TYPE_LABELS: Record<string, string> = {
  diagnostic: "Diagnostic",
  practice: "Practice",
  flashcard: "Flashcard",
  tutor: "Tutor",
};

// Per-type chip fill (fills only — text stays ink, per DESIGN.md color
// rules). The dot keeps carrying the outcome signal (green/red/gold/slate).
const TYPE_CHIP: Record<string, string> = {
  diagnostic: "bg-brand-slate/10",
  practice: "bg-brand-orange/10",
  flashcard: "bg-brand-gold/15",
  tutor: "bg-brand-slate/10",
};

function outcomeStyles(e: EvidenceEvent): { dot: string; word: string; wordClass: string } {
  if (e.type === "tutor") return { dot: "bg-brand-slate", word: "asked", wordClass: "text-muted-foreground" };
  if (e.type === "flashcard") return { dot: "bg-brand-gold", word: "recalled", wordClass: "text-muted-foreground" };
  if (e.correct) return { dot: "bg-brand-green", word: "correct", wordClass: "text-brand-green" };
  return { dot: "bg-destructive", word: "not quite", wordClass: "text-destructive" };
}

export function EvidenceLedger({ events, className }: { events: EvidenceEvent[]; className?: string }) {
  const reduceMotion = useReducedMotion();

  if (events.length === 0) {
    return (
      <div className={cn("rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground", className)}>
        No evidence yet. Your twin fills in as you practice — every answer,
        review, and question lands here, in order, and stays.
      </div>
    );
  }

  return (
    <ol className={cn("divide-y divide-border border rounded-md", className)} aria-label="Evidence ledger">
      <AnimatePresence initial={false}>
        {events.map((e) => {
          const { dot, word, wordClass } = outcomeStyles(e);
          return (
            <motion.li
              key={e.id}
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={reduceMotion ? { duration: 0 } : { duration: 0.25, ease: "easeOut" }}
              className="flex items-center gap-3 px-3 py-2 font-mono text-xs"
            >
              <span className={cn("size-1.5 shrink-0 rounded-full", dot)} aria-hidden />
              <span className={cn("w-20 shrink-0 rounded-sm px-1 py-0.5 text-center text-[10px] font-semibold", TYPE_CHIP[e.type] ?? "bg-muted")}>
                {TYPE_LABELS[e.type] ?? e.type}
              </span>
              <span className="min-w-0 flex-1 truncate text-foreground">{e.skillName}</span>
              <span className={cn("w-16 shrink-0 text-right", wordClass)}>{word}</span>
              <span className="w-14 shrink-0 text-right tabular-nums text-muted-foreground">
                {e.latencyMs != null ? `${(e.latencyMs / 1000).toFixed(1)}s` : "—"}
              </span>
              <span className="w-16 shrink-0 text-right text-muted-foreground/70">
                {formatRelativeTime(e.createdAt)}
              </span>
            </motion.li>
          );
        })}
      </AnimatePresence>
    </ol>
  );
}
