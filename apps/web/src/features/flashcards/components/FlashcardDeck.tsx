import { useState } from "react";
import { useFlashcardDeck, useReviewFlashcard } from "@/features/flashcards/hooks/use-flashcards";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";

// Self-paced review: flip to see the back, then self-report recall. Not
// graded like diagnostic/practice, it's a lighter-weight tracer signal.
export function FlashcardDeck({ courseId }: { courseId: string }) {
  const { data, isLoading, isError } = useFlashcardDeck(courseId);
  const review = useReviewFlashcard(courseId);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [startedAt, setStartedAt] = useState(() => Date.now());

  if (isLoading) return <p className="text-muted-foreground">Building your deck…</p>;
  if (isError)
    return (
      <EmptyState
        title="We could not load flashcards"
        description="Check your connection and try again."
        action={<Button variant="outline">Retry</Button>}
      />
    );
  if (!data || data.cards.length === 0)
    return (
      <EmptyState
        title="No flashcards yet"
        description="Course content hasn't been ingested for this course yet."
      />
    );

  if (index >= data.cards.length) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <p className="font-medium">Deck complete.</p>
          <p className="mt-1 text-sm text-muted-foreground">Come back any time for another round.</p>
        </CardContent>
      </Card>
    );
  }

  const card = data.cards[index];

  function handleReview(knewIt: boolean) {
    review.mutate({ itemId: card.id, knewIt, latencyMs: Date.now() - startedAt });
    setIndex((i) => i + 1);
    setFlipped(false);
    setStartedAt(Date.now());
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Flashcards ({index + 1}/{data.cards.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <button
          type="button"
          onClick={() => setFlipped((f) => !f)}
          className="flex min-h-40 w-full items-center justify-center rounded-md border px-6 py-8 text-center text-lg font-medium"
        >
          {flipped ? card.back : card.front}
        </button>
        <p className="text-center text-xs text-muted-foreground">Tap the card to flip it</p>

        {flipped ? (
          <div className="flex justify-center gap-3">
            <Button variant="outline" onClick={() => handleReview(false)}>
              Didn't know it
            </Button>
            <Button variant="orange" onClick={() => handleReview(true)}>
              Knew it
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
