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
        title="Review key terms"
        description="Flip, then self-report recall. A lighter signal for your twin — not graded like practice."
      />
      <FlashcardDeck courseId={courseId} />
    </>
  );
}
