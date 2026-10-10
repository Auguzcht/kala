import { api } from "@/lib/api/client";
import { parseApiResponse } from "@/lib/api/parse-response";
import {
  flashcardDeckSchema,
  flashcardMembershipSchema,
  flashcardReviewResultSchema,
  type FlashcardDeck,
  type FlashcardMembership,
  type FlashcardReviewResult,
} from "@/features/flashcards/schema/flashcards.schema";

export async function fetchFlashcardDeck(
  courseId: string,
  limit = 10,
  skillId?: string,
  mode?: "review" | "all",
  offset = 0,
): Promise<FlashcardDeck> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (skillId) params.set("skill_id", skillId);
  if (mode) params.set("mode", mode);
  if (offset > 0) params.set("offset", String(offset));
  const data = await api<unknown>(`/flashcards/${courseId}/deck?${params.toString()}`);
  return parseApiResponse(flashcardDeckSchema, data, `/flashcards/${courseId}/deck`);
}

export async function fetchFlashcardMembership(
  courseId: string,
  skillId: string,
): Promise<FlashcardMembership> {
  const endpoint = `/flashcards/${courseId}/skills/${skillId}/cards`;
  try {
    const data = await api<unknown>(endpoint);
    return { ...parseApiResponse(flashcardMembershipSchema, data, endpoint), isFallback: false };
  } catch (error) {
    // Keep a safe path for API deployments that have not received the
    // membership route yet. Other failures must remain visible as errors.
    if (!(error instanceof Error) || !error.message.startsWith("API 404:")) throw error;

    const deck = await fetchFlashcardDeck(courseId, 50, skillId);
    const cards = deck.cards.map((card) => ({
      itemId: card.itemId,
      prompt: card.prompt,
      back: card.back,
      state: card.state,
      due: card.state === "due",
      dueAt: null,
    }));
    const counts = {
      new: cards.filter((card) => card.state === "new").length,
      learning: 0,
      slipping: 0,
      known: 0,
      dueToday: cards.filter((card) => card.due).length,
    };
    return {
      skillId,
      counts,
      cards,
      isFallback: true,
      fallbackTracked: deck.stats.tracked,
    };
  }
}

// Self-mark one studied card. `remembered` is the student's own call; the
// server advances the SRS schedule from it. There is no grading call and no
// reveal call — flipping happens client-side and is free.
export async function reviewFlashcard(
  courseId: string,
  args: {
    itemId: string;
    remembered: boolean;
    latencyMs: number;
    sessionId: string;
    idempotencyKey: string;
  }
): Promise<FlashcardReviewResult> {
  const data = await api<unknown>(`/flashcards/${courseId}/review`, {
    method: "POST",
    body: JSON.stringify({
      item_id: args.itemId,
      remembered: args.remembered,
      latency_ms: args.latencyMs,
      mode: "flashcard",
      session_id: args.sessionId,
      idempotency_key: args.idempotencyKey,
    }),
  });
  return parseApiResponse(flashcardReviewResultSchema, data, `/flashcards/${courseId}/review`);
}
