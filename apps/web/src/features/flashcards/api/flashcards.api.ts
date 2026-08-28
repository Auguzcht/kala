import { api } from "@/lib/api/client";
import {
  flashcardDeckSchema,
  flashcardReviewResultSchema,
  flashcardRevealResultSchema,
  type FlashcardDeck,
  type FlashcardReviewResult,
  type FlashcardRevealResult,
} from "@/features/flashcards/schema/flashcards.schema";

export async function fetchFlashcardDeck(
  courseId: string,
  limit = 10
): Promise<FlashcardDeck> {
  const data = await api<unknown>(`/flashcards/${courseId}/deck?limit=${limit}`);
  return flashcardDeckSchema.parse(data);
}

export async function reviewFlashcard(
  courseId: string,
  args: { itemId: string; choiceId: string; latencyMs: number; hintsUsed: number }
): Promise<FlashcardReviewResult> {
  const data = await api<unknown>(`/flashcards/${courseId}/review`, {
    method: "POST",
    body: JSON.stringify({
      item_id: args.itemId,
      choice_id: args.choiceId,
      latency_ms: args.latencyMs,
      hints_used: args.hintsUsed,
    }),
  });
  return flashcardReviewResultSchema.parse(data);
}

// Pre-commit Show Answer: the server records the lapse before the key comes
// back, so a revealed card is terminal for this render — never follow up
// with a review call for the same item_id.
export async function revealFlashcard(
  courseId: string,
  args: { itemId: string; latencyMs: number }
): Promise<FlashcardRevealResult> {
  const data = await api<unknown>(`/flashcards/${courseId}/reveal`, {
    method: "POST",
    body: JSON.stringify({ item_id: args.itemId, latency_ms: args.latencyMs }),
  });
  return flashcardRevealResultSchema.parse(data);
}
