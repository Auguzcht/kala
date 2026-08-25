import { z } from "zod";

export const flashcardSchema = z.object({
  id: z.string(),
  skillId: z.string(),
  front: z.string(),
  back: z.string(),
});

export const flashcardDeckSchema = z.object({
  courseId: z.string(),
  cards: z.array(flashcardSchema),
});

export type Flashcard = z.infer<typeof flashcardSchema>;
export type FlashcardDeck = z.infer<typeof flashcardDeckSchema>;
