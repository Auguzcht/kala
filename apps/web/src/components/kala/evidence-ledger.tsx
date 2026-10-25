import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { cn, formatRelativeTime } from "@/lib/utils";
import { pageWindow } from "@/lib/pagination";
import {
  Pagination, PaginationContent, PaginationItem, PaginationLink,
  PaginationPrevious, PaginationNext,
} from "@/components/ui/pagination";
import type { EvidenceEvent } from "@/features/twin";

// Evidence ledger — a paged window of the append-only stream. Monospaced,
// nothing edits or deletes an event when its presentation page changes. This is the
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
const PAGE_SIZE = 10;

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

export function EvidenceLedger({ events, className, totalLabel = "recent events" }: {
  events: EvidenceEvent[]; className?: string; totalLabel?: string;
}) {
  const reduceMotion = useReducedMotion();
  const [page, setPage] = useState(0);
  const pages = Math.max(1, Math.ceil(events.length / PAGE_SIZE));
  const safePage = Math.min(page, pages - 1);
  const visible = events.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);
  useEffect(() => { setPage((current) => Math.min(current, pages - 1)); }, [pages]);

  if (events.length === 0) {
    return (
      <div className={cn("rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground", className)}>
        No evidence yet. Your recent answers, reviews and questions will
        appear here, newest first.
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      <ol className="divide-y divide-border rounded-md border" aria-label="Evidence ledger">
        <AnimatePresence key={safePage} initial={false}>
          {visible.map((e) => {
            const { dot, word, wordClass } = outcomeStyles(e);
            return (
              <motion.li
                key={e.id}
                initial={reduceMotion ? false : { opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={reduceMotion ? { duration: 0 } : { duration: 0.25, ease: "easeOut" }}
                className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 px-3 py-2 font-mono text-xs sm:flex"
              >
                <span className="flex items-center gap-3">
                  <span className={cn("size-1.5 shrink-0 rounded-full", dot)} aria-hidden />
                  <span className={cn("w-20 shrink-0 rounded-sm px-1 py-0.5 text-center text-[10px] font-semibold", TYPE_CHIP[e.type] ?? "bg-muted")}>
                    {TYPE_LABELS[e.type] ?? e.type}
                  </span>
                </span>
                <span className="col-span-2 row-start-2 min-w-0 break-words text-foreground sm:flex-1 sm:truncate" title={e.skillName}>{e.skillName}</span>
                <span className={cn("col-start-2 row-start-1 shrink-0 whitespace-nowrap text-right sm:w-20", wordClass)}>{word}</span>
                <span className="row-start-3 shrink-0 tabular-nums text-muted-foreground sm:w-14 sm:text-right" aria-label={e.latencyMs != null ? `Response time ${(e.latencyMs / 1000).toFixed(1)} seconds` : "Response time unavailable"}>
                  {e.latencyMs != null ? `${(e.latencyMs / 1000).toFixed(1)}s` : "—"}
                </span>
                <span className="col-start-2 row-start-3 w-16 shrink-0 text-right text-muted-foreground/70">
                  {formatRelativeTime(e.createdAt)}
                </span>
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ol>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p role="status" className="font-mono text-[11px] text-muted-foreground">
          {safePage * PAGE_SIZE + 1}–{Math.min(events.length, (safePage + 1) * PAGE_SIZE)} of {events.length} {totalLabel}
        </p>
        {pages > 1 ? (
          <Pagination aria-label={`Evidence pages, page ${safePage + 1} of ${pages}`}>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious href="#" aria-disabled={safePage === 0} tabIndex={safePage === 0 ? -1 : undefined}
                  onClick={(event) => { event.preventDefault(); setPage(Math.max(0, safePage - 1)); }}
                  className={safePage === 0 ? "pointer-events-none opacity-40" : undefined} />
              </PaginationItem>
              {pageWindow(safePage, pages).map((item, i) => item === null ? (
                <PaginationItem key={`gap-${i}`} className="hidden sm:list-item"><span className="px-0.5 font-mono text-xs text-muted-foreground">…</span></PaginationItem>
              ) : (
                <PaginationItem key={item} className={item !== safePage ? "hidden sm:list-item" : undefined}>
                  <PaginationLink href="#" aria-label={`Page ${item + 1}`} isActive={item === safePage}
                    onClick={(event) => { event.preventDefault(); setPage(item); }}>{item + 1}</PaginationLink>
                </PaginationItem>
              ))}
              <PaginationItem>
                <PaginationNext href="#" aria-disabled={safePage >= pages - 1} tabIndex={safePage >= pages - 1 ? -1 : undefined}
                  onClick={(event) => { event.preventDefault(); setPage(Math.min(pages - 1, safePage + 1)); }}
                  className={safePage >= pages - 1 ? "pointer-events-none opacity-40" : undefined} />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        ) : null}
      </div>
    </div>
  );
}
