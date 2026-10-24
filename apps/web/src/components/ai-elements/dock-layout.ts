/** Shared visual contract for Tutor and Study/Test/Flashcard composers.
 * Keep behavior and attachment ownership in their respective consumers. */
export const dockLayout = {
  form: "[&_[data-slot=input-group]]:h-auto [&_[data-slot=input-group]]:min-h-12 [&_[data-slot=input-group]]:flex-col [&_[data-slot=input-group]]:justify-center [&_[data-slot=input-group]]:bg-background [&_[data-slot=input-group]]:border-input [&_[data-slot=input-group]]:shadow-sm [&_[data-slot=input-group]]:px-1.5",
  pill: "[&_[data-slot=input-group]]:rounded-[calc(var(--radius-xl)*2)]",
  row: "flex w-full items-center",
  // 24px line + symmetric 10px padding = 44px, centered in the 48px dock.
  // Explicit leading prevents desktop text-sm from shortening the line box.
  textarea: "min-h-11 max-h-32 py-2.5 leading-6",
  control: "shrink-0 rounded-full",
  // Overlap the stream by one collapsed dock, so text can pass behind the pill.
  // The stream reserves pb-24 for the last message and places its scroll button above it.
  footer:
    "pointer-events-none relative z-10 -mt-16 bg-gradient-to-t from-background via-background/95 to-background/0 px-4 pb-4",
  content: "pointer-events-auto",
} as const;
