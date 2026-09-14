// The student's own message in a stream. Student turns remain intentionally
// quiet: a small right-aligned bubble is enough to establish ownership, while
// Kala's named header introduces the response that follows.
export function UserBlock({
  text,
}: {
  text: string;
  /** Kept for callers that supply session initials; student turns no longer show an avatar. */
  initials?: string;
}) {
  // `w-fit max-w-[85%] ml-auto` is the load-bearing combination: w-fit makes
  // the wrapper shrink to the message so short turns are short bubbles, the
  // max-width caps long ones, and ml-auto pushes the whole thing right. Without
  // w-fit the wrapper is a normal block, so it always filled the full 85% and
  // every message looked the same fixed width regardless of how long it was.
  return (
    <div className="ml-auto w-fit max-w-[85%]">
      {/* The student's turn keeps the conversational radius — the dock and
          this bubble are the same voice, so they share rounded-full. A
          wrapped multi-line message still just gets a taller stadium, which
          reads correctly (round-full never clips or distorts text). */}
      <div className="min-w-0 whitespace-pre-wrap rounded-3xl bg-secondary px-4 py-2.5 text-sm leading-relaxed text-secondary-foreground">
        {text}
      </div>
    </div>
  );
}
