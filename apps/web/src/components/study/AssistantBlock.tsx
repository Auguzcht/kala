import { Message, MessageContent } from "@/components/ai-elements/message";
import { MarkdownText } from "@/components/study/MarkdownText";
import { Shimmer } from "@/components/ai-elements/shimmer";

// A plain-text (well, markdown) assistant reply — Tutor's freeform answers,
// unlike TeachingBlock's structured lesson-step shape (summary/bullets/
// misconception/key-takeaway), are just a string from the model. Rendered
// through MarkdownText (Streamdown), so bold/bullets/code the model actually
// produces render as real markdown instead of a wall of plain text.
//
// This component owns Kala's identity header, including while an answer is
// still pending (`pending` with no `text` yet). That is deliberate: the header
// is the one thing that must be present the moment the student asks something,
// and it must never be rendered by both this component and its caller — that
// duplication is exactly what produced two stacked "Kala" headings. Callers
// that need a loading state render <AssistantBlock pending /> and get the
// header plus a placeholder, not a separate heading of their own.
export function AssistantBlock({
  text,
  id,
  animate = true,
  pending = false,
  pendingLabel = "Kala is thinking…",
}: {
  text?: string;
  id?: string;
  /** Reveal the answer as it arrives. On for replies to a student's question
   * (they just asked something and expect it to be written out); off for
   * reference text that should simply be present, e.g. a graded explanation. */
  animate?: boolean;
  /** Show the header with a "thinking" placeholder instead of an answer.
   * Used between asking and the answer arriving, so the conversation shows
   * Kala immediately rather than a bare spinner in the student's own layout. */
  pending?: boolean;
  pendingLabel?: string;
}) {
  const showPending = pending && !text;

  return (
    <div id={id} className="mr-auto w-full max-w-full">
      <div className="mb-2 flex items-center gap-2">
        <img src="/Kala-Logo.png" alt="" className="size-7 shrink-0 object-contain" />
        <span className="text-sm font-semibold text-foreground">Kala</span>
      </div>
      <Message from="assistant" className="min-w-0 w-full max-w-full">
        <MessageContent className="min-w-0 w-full px-1 text-sm leading-relaxed text-foreground">
          {showPending ? (
            <Shimmer className="text-sm">{pendingLabel}</Shimmer>
          ) : (
            <MarkdownText animate={animate}>{text ?? ""}</MarkdownText>
          )}
        </MessageContent>
      </Message>
    </div>
  );
}
