import { Message, MessageContent } from "@/components/ai-elements/message";

// One lesson step's teaching content, rendered as an assistant message in
// the stream. Extracted from LessonChat's original inline TeachingMessage
// with the exact same structure and copy (summary, detail bullets, a
// misconception callout, a key-takeaway callout) — this is a component
// swap onto the shared Message/MessageContent primitives, not a rewrite of
// what it says or how it's organized.
//
// The assistant identity introduces a response above its content. This keeps
// Kala readable as a conversation partner without boxing an entire lesson
// into a second, competing surface.
export type TeachingStep = {
  summary: string;
  detailPoints: string[];
  misconception: string | null;
  keyTakeaway: string | null;
  bloomLevel: string | null;
};

export function TeachingBlock({
  step,
  id,
}: {
  step: TeachingStep;
  /** Tour anchor — passed through to the underlying bubble for the
   * CURRENT step only (#tour-lesson-explain). */
  id?: string;
}) {
  return (
    <div className="mr-auto w-full max-w-full">
      <div className="mb-2 flex items-center gap-2">
        <img src="/Kala-Logo.png" alt="" className="size-7 shrink-0 object-contain" />
        <span className="text-sm font-semibold text-foreground">Kala</span>
      </div>
      <Message from="assistant" className="min-w-0 w-full max-w-full">
        <MessageContent
          id={id}
          className="min-w-0 w-full space-y-3 px-1 text-sm leading-relaxed text-foreground"
        >
          <p className="font-medium text-foreground">{step.summary}</p>

          {step.detailPoints.length > 0 ? (
            <ul className="space-y-1.5 text-muted-foreground">
              {step.detailPoints.map((d, i) => (
                <li key={i} className="flex gap-2">
                  <span className="mt-1.5 size-1 shrink-0 rounded-full bg-brand-slate/50" />
                  <span className="leading-relaxed">{d}</span>
                </li>
              ))}
            </ul>
          ) : null}

          {step.misconception ? (
            <div className="border-l-2 border-destructive/60 pl-3">
              <p className="text-xs font-medium uppercase tracking-wide text-destructive">
                Common misconception
              </p>
              <p className="mt-0.5 text-muted-foreground">{step.misconception}</p>
            </div>
          ) : null}

          {step.keyTakeaway ? (
            <div className="border-l-2 border-brand-gold pl-3">
              <p className="text-xs font-medium uppercase tracking-wide text-brand-gold-foreground/70">
                Key takeaway
              </p>
              <p className="mt-0.5 font-medium text-foreground">{step.keyTakeaway}</p>
            </div>
          ) : null}
        </MessageContent>
      </Message>
    </div>
  );
}
