import { useEffect, useRef, useState, type FormEvent } from "react";
import { Streamdown } from "streamdown";
import { UserIcon } from "lucide-react";
import { SendIcon } from "@/components/ui/send";
import { useSession } from "@/lib/auth/AuthProvider";
import { StudySessionShell } from "@/components/study/StudySessionShell";
import { GamificationSummary } from "@/features/gamification";
import { useAskTutor } from "@/features/tutor/hooks/use-tutor";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CornerBrackets } from "@/components/kala";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import type { TutorMessage } from "@/features/tutor/schema/tutor.schema";

// RAG-grounded tutor. Teaches and hints, never hands back raw answers to
// graded work (enforced server-side by the system prompt). The hornbill is
// the guide (DESIGN.md signature element #7): it sits beside every answer,
// and it's what the "thinking" beat is made of.

// Markdown rendering for assistant answers: the model answers in
// markdown (bold, lists, code), and raw ** asterisks read as a rendering
// bug. Streamdown is the installed markdown renderer (already a
// dependency, mode="static"). The user's own messages stay plain text.
//
// The user avatar mirrors the assistant's: initials chip from the session
// display name (the shell's own pattern), falling back to a user glyph.
// The hornbill stays on the assistant side (DESIGN.md signature #7).
const MD_BUBBLE =
  "min-w-0 rounded-md border bg-card px-4 py-2.5 text-sm leading-relaxed text-foreground " +
  "[&_p]:my-1.5 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 " +
  "[&_ul]:my-1.5 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-1.5 [&_ol]:list-decimal [&_ol]:pl-5 " +
  "[&_li]:my-0.5 [&_code]:rounded-sm [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 " +
  "[&_pre]:my-1.5 [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-muted [&_pre]:p-3 " +
  "[&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_a]:text-brand-orange [&_a]:underline " +
  "[&_h1]:text-base [&_h2]:text-base [&_h3]:text-[13.5px] [&_blockquote]:border-l-2 " +
  "[&_blockquote]:border-border [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground";

export function TutorChat({ courseId }: { courseId: string }) {
  const session = useSession();
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<TutorMessage[]>([]);
  const ask = useAskTutor(courseId);
  const scrollRef = useRef<HTMLDivElement>(null);
  const userInitials = (session?.displayName ?? "")
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, ask.isPending]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = question.trim();
    if (!text || ask.isPending) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setQuestion("");
    ask.mutate(text, {
      onSuccess: (result) => {
        setMessages((m) => [...m, { role: "assistant", text: result.answer }]);
      },
    });
  }

  return (
    <StudySessionShell right={<GamificationSummary courseId={courseId} />}>
      <Card className="relative">
      <CornerBrackets />
      <CardHeader>
        <CardTitle>Ask Kala</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div
          ref={scrollRef}
          className="flex max-h-96 flex-col gap-4 overflow-y-auto pr-1"
        >
          {messages.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <img
                src="/Kala-Logo.png"
                alt=""
                className="size-14 object-contain opacity-80"
              />
              <p className="max-w-sm text-sm text-muted-foreground">
                Ask a question about this course. Kala will teach and give hints — not hand you
                answers to graded work.
              </p>
            </div>
          ) : (
            messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="ml-auto flex max-w-[85%] items-start gap-2.5">
                  <div className="rounded-md bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground">
                    <p className="whitespace-pre-wrap">{m.text}</p>
                  </div>
                  <span
                    className="grid size-7 shrink-0 place-items-center rounded-full bg-brand-slate text-[10px] font-bold text-background"
                    title={session?.displayName ?? "You"}
                    aria-hidden
                  >
                    {userInitials || <UserIcon size={12} />}
                  </span>
                </div>
              ) : (
                <div key={i} className="mr-auto flex max-w-[85%] items-start gap-2.5">
                  <img
                    src="/Kala-Logo.png"
                    alt="Kala"
                    className="mt-0.5 size-7 shrink-0 object-contain"
                  />
                  <div
                    id={i === messages.length - 1 ? "tour-tutor-response" : undefined}
                    className={MD_BUBBLE}
                  >
                    <Streamdown mode="static">{m.text}</Streamdown>
                  </div>
                </div>
              )
            )
          )}
          {ask.isPending ? (
            <div id="tour-tutor-thinking" className="mr-auto flex items-start gap-2.5">
              <img
                src="/Kala-Logo.png"
                alt=""
                className={cn(
                  "mt-0.5 size-7 shrink-0 object-contain opacity-80 motion-safe:animate-pulse"
                )}
              />
              <p className="flex items-center gap-2 rounded-md border bg-card px-4 py-2.5 text-sm text-muted-foreground">
                <Spinner className="size-3.5" />
                Kala is thinking…
              </p>
            </div>
          ) : null}
        </div>

        <form id="tour-tutor-input" onSubmit={handleSubmit} className="flex gap-2">
          <input
            className="h-10 flex-1 rounded-md border border-input bg-background px-4 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about this course…"
          />
          <Button type="submit" variant="orange" disabled={ask.isPending || !question.trim()}>
            {ask.isPending ? <Spinner className="size-4" /> : <SendIcon size={16} aria-hidden />}
            Ask
          </Button>
        </form>
      </CardContent>
    </Card>
    </StudySessionShell>
  );
}
