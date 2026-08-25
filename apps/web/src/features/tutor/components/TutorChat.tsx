import { useState, type FormEvent } from "react";
import { useAskTutor } from "@/features/tutor/hooks/use-tutor";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { TutorMessage } from "@/features/tutor/schema/tutor.schema";

// RAG-grounded tutor. Teaches and hints, never hands back raw answers to
// graded work (enforced server-side by the system prompt).
export function TutorChat({ courseId }: { courseId: string }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<TutorMessage[]>([]);
  const ask = useAskTutor(courseId);

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
    <Card>
      <CardHeader>
        <CardTitle>Ask Kala</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex max-h-96 flex-col gap-3 overflow-y-auto">
          {messages.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Ask a question about this course. Kala will teach and give hints, not hand you
              answers to graded work.
            </p>
          ) : (
            messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === "user"
                    ? "ml-auto max-w-[85%] rounded-xl bg-primary px-4 py-2 text-sm text-primary-foreground"
                    : "mr-auto max-w-[85%] rounded-xl bg-accent px-4 py-2 text-sm"
                }
              >
                {m.text}
              </div>
            ))
          )}
          {ask.isPending ? <p className="text-sm text-muted-foreground">Kala is thinking…</p> : null}
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            className="h-10 flex-1 rounded-md border border-input bg-background px-4 text-sm"
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
