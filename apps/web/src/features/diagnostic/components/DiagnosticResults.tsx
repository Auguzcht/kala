import { useEffect, useRef } from "react";
import { useNavigate } from "@tanstack/react-router";
import { motion, useReducedMotion } from "motion/react";
import { MasteryDelta, type MasteryDeltaRow } from "@/components/kala";
import { Button } from "@/components/ui/button";
import { ChevronLeftIcon, type ChevronLeftIconHandle } from "@/components/ui/chevron-left";
import { ActivityIcon, type ActivityIconHandle } from "@/components/ui/activity";
import { useIconHover } from "@/hooks/use-icon-hover";
import { celebrateOnce } from "@/lib/celebrate";

export function DiagnosticResults({ rows, total, celebrationKey }: {
  rows: MasteryDeltaRow[];
  total: number;
  celebrationKey: string;
}) {
  const navigate = useNavigate();
  const reduced = useReducedMotion();
  const heading = useRef<HTMLHeadingElement>(null);
  const back = useIconHover<ChevronLeftIconHandle>();
  const twin = useIconHover<ActivityIconHandle>();
  useEffect(() => { heading.current?.focus({ preventScroll: true }); }, []);
  useEffect(() => {
    if (reduced === false) celebrateOnce(celebrationKey);
  }, [celebrationKey, reduced]);

  return (
    <div data-study-surface className="h-full min-h-0 overflow-y-auto px-4 py-6 sm:px-6">
      <motion.section
        data-diagnostic-results
        aria-labelledby="diagnostic-result-title"
        className="mx-auto w-full max-w-[800px] overflow-hidden border bg-card"
        initial={reduced ? false : { opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reduced ? 0 : 0.2 }}
      >
        <header className="border-b bg-muted/30 px-5 py-5 sm:px-7 sm:py-6">
          <p className="text-xs font-medium uppercase tracking-wide text-brand-slate">Diagnostic complete</p>
          <h1 ref={heading} tabIndex={-1} id="diagnostic-result-title" className="mt-1 font-display text-2xl font-semibold tracking-tight outline-none">Baseline set</h1>
          <p className="mt-2 text-sm text-muted-foreground">Kala has updated your twin using these answers. Practice builds from here.</p>
          <p className="mt-3 font-mono text-xs text-muted-foreground">{total} {total === 1 ? "question" : "questions"} answered</p>
        </header>
        <div className="space-y-5 p-5 sm:p-7">
          {rows.length ? <MasteryDelta rows={rows} /> : (
            <p className="text-sm text-muted-foreground">Your answers are saved. View your twin to explore your current skill profile.</p>
          )}
          <p className="text-sm text-muted-foreground">New diagnostics appear when another topic needs a baseline.</p>
          <div className="flex flex-wrap gap-2 border-t pt-4">
            <Button variant="orange" onClick={() => navigate({ to: "/course" })}
              onMouseEnter={reduced ? undefined : back.play} onMouseLeave={back.stop}
              onFocus={reduced ? undefined : back.play} onBlur={back.stop}>
              <ChevronLeftIcon ref={back.ref} size={16} aria-hidden /> Back to workspace
            </Button>
            <Button variant="outline" onClick={() => navigate({ to: "/course/twin" })}
              onMouseEnter={reduced ? undefined : twin.play} onMouseLeave={twin.stop}
              onFocus={reduced ? undefined : twin.play} onBlur={twin.stop}>
              <ActivityIcon ref={twin.ref} size={16} aria-hidden /> View your twin
            </Button>
          </div>
        </div>
      </motion.section>
    </div>
  );
}
