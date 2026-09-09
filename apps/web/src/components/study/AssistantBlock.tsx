import { Message, MessageContent, MessageResponse } from "@/components/ai-elements/message";
import { cn } from "@/lib/utils";

// Markdown element typography for free-text assistant answers. The model
// answers in markdown (bold, lists, code) and Streamdown renders real
// elements — without this recipe those land on raw browser defaults
// (lists cramped, code invisible against the card, links unstyled). This
// is the same deliberate recipe the original inline TutorChat bubble
// carried; restored here when AssistantBlock replaced it. Keep it as one
// shared constant so every stream surface that renders free-text markdown
// reuses the same typography instead of drifting.
const MD_RECIPE =
  "[&_p]:my-1.5 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 " +
  "[&_ul]:my-1.5 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-1.5 [&_ol]:list-decimal [&_ol]:pl-5 " +
  "[&_li]:my-0.5 [&_code]:rounded-sm [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 " +
  "[&_pre]:my-1.5 [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-muted [&_pre]:p-3 " +
  "[&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_a]:text-brand-orange [&_a]:underline " +
  "[&_h1]:text-base [&_h2]:text-base [&_h3]:text-[13.5px] [&_blockquote]:border-l-2 " +
  "[&_blockquote]:border-border [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground";

// A plain-text (well, markdown) assistant reply — Tutor's freeform answers,
// unlike TeachingBlock's structured lesson-step shape (summary/bullets/
// misconception/key-takeaway), are just a string from the model. Rendered
// through MessageResponse (Streamdown), so bold/bullets/code the model
// actually produces render as real markdown instead of a wall of plain text.
export function AssistantBlock({ text, id }: { text: string; id?: string }) {
  return (
    <div id={id} className="mr-auto flex max-w-[88%] items-start gap-2.5">
      <img src="/Kala-Logo.png" alt="Kala" className="mt-0.5 size-7 shrink-0 object-contain" />
      <Message from="assistant" className="min-w-0 max-w-full">
        <MessageContent
          className={cn(
            "min-w-0 rounded-md border bg-card px-4 py-3.5 text-sm leading-relaxed text-foreground",
            MD_RECIPE
          )}
        >
          <MessageResponse>{text}</MessageResponse>
        </MessageContent>
      </Message>
    </div>
  );
}
