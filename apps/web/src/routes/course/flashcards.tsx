import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { TopicLanding } from "@/components/study/TopicLanding";
import { FlashcardDeck } from "@/features/flashcards";
import { useFlashcardDeck } from "@/features/flashcards/hooks/use-flashcards";
import { useTwin } from "@/features/twin";
import { Button } from "@/components/ui/button";
import { ChevronLeftIcon } from "@/components/ui/chevron-left";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { ZapIcon } from "@/components/ui/zap";

export const Route = createFileRoute("/course/flashcards")({
  component: FlashcardsPage,
});

function FlashcardsPage() {
  const courseId = useSession()?.courseId ?? "";
  const { data: twin, isLoading } = useTwin(courseId);
  // limit=0: a cheap peek at stats.due for the recommended card, without
  // triggering the deck's top-up generation (which only runs when the
  // fetched card count is below the requested limit — 0 is never below 0).
  const { data: peek } = useFlashcardDeck(courseId, 0);
  const [session, setSession] = useState<{ skillId?: string } | null>(null);

  return (
    <>
      <PageHeader
        eyebrow="Flashcards"
        title="Spaced recall"
        description="Recall first, then check yourself. Review what's due across everything, or drill one topic below."
      />
      {session ? (
        <div className="space-y-4">
          <Button variant="outline" size="sm" onClick={() => setSession(null)}>
            <ChevronLeftIcon size={14} /> Choose another topic
          </Button>
          <FlashcardDeck courseId={courseId} skillId={session.skillId} />
        </div>
      ) : (
        <TopicLanding
          isLoading={isLoading}
          skills={twin?.skills ?? []}
          onChoose={(skillId) => setSession({ skillId })}
          caption="spaced recall card"
          gridId="tour-flashcards-picker"
          recommended={
            <button
              id="tour-flashcards-recommended"
              type="button"
              onClick={() => setSession({})}
              className="flex w-full items-center justify-between gap-4 bg-primary px-6 py-5 text-left transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <div className="min-w-0">
                <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-brand-gold">
                  <ZapIcon size={12} /> Recommended
                </p>
                <p className="mt-1.5 truncate font-display text-lg font-semibold text-primary-foreground">
                  {peek
                    ? peek.stats.due > 0
                      ? `${peek.stats.due} due for review`
                      : "Nothing due — review fresh cards"
                    : "Review what's due"}
                </p>
                <p className="mt-1 text-[13px] text-primary-foreground/70">
                  Across every topic, whatever's due now — missed cards resurface sooner.
                </p>
              </div>
              <ArrowRightIcon size={18} className="shrink-0 text-primary-foreground/70" />
            </button>
          }
        />
      )}
    </>
  );
}
