import type { FlashcardCard } from "@/features/flashcards/schema/flashcards.schema";

export type CardMemoryState = Exclude<FlashcardCard["state"], "due">;

type CardStatePresentation = {
  label: string;
  className: string;
};

const CARD_STATE_PRESENTATION: Record<CardMemoryState, CardStatePresentation> = {
  new: {
    label: "New",
    className: "border-border bg-muted text-muted-foreground",
  },
  learning: {
    label: "Learning",
    className: "border-brand-slate/40 bg-brand-slate/10 text-brand-slate",
  },
  slipping: {
    label: "Slipping",
    className: "border-brand-orange/40 bg-brand-orange/10 text-foreground",
  },
  known: {
    label: "Known",
    className: "border-brand-green/40 bg-brand-green/10 text-brand-green",
  },
};

export function cardStatePresentation(state: CardMemoryState): CardStatePresentation {
  return CARD_STATE_PRESENTATION[state];
}
