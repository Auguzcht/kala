import { api } from "@/lib/api/client";
import {
  flashcardDeckSchema,
  flashcardReviewResultSchema,
  type FlashcardDeck,
  type FlashcardReviewResult,
} from "@/features/flashcards/schema/flashcards.schema";

export async function fetchFlashcardDeck(
  courseId: string,
  limit = 10,
  skillId?: string
): Promise<FlashcardDeck> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (skillId) params.set("skill_id", skillId);
  const data = await api<unknown>(`/flashcards/${courseId}/deck?${params.toString()}`);
  return flashcardDeckSchema.parse(data);
}

// Self-mark one studied card. `remembered` is the student's own call; the
// server advances the SRS schedule from it. There is no grading call and no
// reveal call — flipping happens client-side and is free.
export async function reviewFlashcard(
  courseId: string,
  args: { itemId: string; remembered: boolean; latencyMs: number }
): Promise<FlashcardReviewResult> {
  const data = await api<unknown>(`/flashcards/${courseId}/review`, {
    method: "POST",
    body: JSON.stringify({
      item_id: args.itemId,
      remembered: args.remembered,
      latency_ms: args.latencyMs,
    }),
  });
  return flashcardReviewResultSchema.parse(data);
}
