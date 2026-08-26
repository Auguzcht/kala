import { cn, formatRelativeTime } from "@/lib/utils";
import type { EvidenceEvent } from "@/features/twin";

// Evidence ledger — the append-only stream. Monospaced, nothing edits or
// deletes; each event slid in when it happened and stays. This is the
// research dataset made visible. Color is never the only signal: every
// row carries a type label + outcome word.

const TYPE_LABELS: Record<string, string> = {
  diagnostic: "Diagnostic",
  practice: "Practice",
  flashcard: "Flashcard",
  tutor: "Tutor",
};

function outcomeStyles(e: EvidenceEvent): { dot: string; word: string; wordClass: string } {
  if (e.type === "tutor") return { dot: "bg-brand-slate", word: "asked", wordClass: "text-muted-foreground" };
  if (e.type === "flashcard") return { dot: "bg-brand-gold", word: "recalled", wordClass: "text-muted-foreground" };
  if (e.correct) return { dot: "bg-brand-green", word: "correct", wordClass: "text-brand-green" };
  return { dot: "bg-destructive", word: "not quite", wordClass: "text-destructive" };
}

export function EvidenceLedger({ events, className }: { events: EvidenceEvent[]; className?: string }) {
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
      {events.map((e) => {
        const { dot, word, wordClass } = outcomeStyles(e);
        return (
          <li key={e.id} className="flex items-center gap-3 px-3 py-2 font-mono text-xs">
            <span className={cn("size-1.5 shrink-0 rounded-full", dot)} aria-hidden />
            <span className="w-20 shrink-0 text-muted-foreground">
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
          </li>
        );
      })}
    </ol>
  );
}
