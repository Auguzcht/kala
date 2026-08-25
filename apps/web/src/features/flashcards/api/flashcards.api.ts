import { api } from "@/lib/api/client";
import { flashcardDeckSchema, type FlashcardDeck } from "@/features/flashcards/schema/flashcards.schema";

export async function fetchFlashcardDeck(courseId: string, limit = 5): Promise<FlashcardDeck> {
  const data = await api<unknown>(`/flashcards/${courseId}/deck?limit=${limit}`);
  return flashcardDeckSchema.parse(data);
}

export async function reviewFlashcard(
  courseId: string,
  args: { itemId: string; knewIt: boolean; latencyMs: number }
): Promise<void> {
  await api<unknown>(`/flashcards/${courseId}/review`, {
    method: "POST",
    body: JSON.stringify({
      item_id: args.itemId,
      knew_it: args.knewIt,
      latency_ms: args.latencyMs,
    }),
  });
}
