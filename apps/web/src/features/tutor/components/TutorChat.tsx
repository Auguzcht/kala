import { useEffect, useRef, useState, type FormEvent } from "react";
import { useAskTutor } from "@/features/tutor/hooks/use-tutor";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CornerBrackets } from "@/components/kala";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { TutorMessage } from "@/features/tutor/schema/tutor.schema";

// RAG-grounded tutor. Teaches and hints, never hands back raw answers to
// graded work (enforced server-side by the system prompt). The hornbill is
// the guide (DESIGN.md signature element #7): it sits beside every answer,
// and it's what the "thinking" beat is made of.

export function TutorChat({ courseId }: { courseId: string }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<TutorMessage[]>([]);
  const ask = useAskTutor(courseId);
  const scrollRef = useRef<HTMLDivElement>(null);

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
                src="/assets/kala-mark.png"
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
                <div key={i} className="ml-auto max-w-[85%]">
                  <div className="rounded-md bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground">
                    {m.text}
                  </div>
                </div>
              ) : (
                <div key={i} className="mr-auto flex max-w-[85%] items-start gap-2.5">
                  <img
                    src="/assets/kala-mark.png"
                    alt="Kala"
                    className="mt-0.5 size-7 shrink-0 object-contain"
                  />
                  <div className="min-w-0 rounded-md border bg-card px-4 py-2.5 text-sm leading-relaxed text-foreground">
                    <p className="whitespace-pre-wrap">{m.text}</p>
                  </div>
                </div>
              )
            )
          )}
          {ask.isPending ? (
            <div className="mr-auto flex items-start gap-2.5">
              <img
                src="/assets/kala-mark.png"
                alt=""
                className={cn(
                  "mt-0.5 size-7 shrink-0 object-contain opacity-80 motion-safe:animate-pulse"
                )}
              />
              <p className="rounded-md border bg-card px-4 py-2.5 text-sm text-muted-foreground">
                Kala is thinking…
              </p>
            </div>
          ) : null}
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            className="h-10 flex-1 rounded-md border border-input bg-background px-4 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about this course…"
          />
          <Button type="submit" variant="orange" disabled={ask.isPending || !question.trim()}>
            Ask
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
