import { createFileRoute } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { FlashcardDeck } from "@/features/flashcards";

export const Route = createFileRoute("/course/flashcards")({
  component: FlashcardsPage,
});

function FlashcardsPage() {
  const courseId = useSession()?.courseId ?? "";
  return (
    <>
      <PageHeader
        eyebrow="Flashcards"
        title="Spaced recall"
        description="Recall first, then check yourself. Graded by Kala and scheduled so missed cards resurface sooner."
      />
      <FlashcardDeck courseId={courseId} />
    </>
  );
}
