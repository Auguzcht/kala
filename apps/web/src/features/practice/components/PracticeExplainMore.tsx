import { useId, useState } from "react";
import { toast } from "sonner";
import { AssistantBlock } from "@/components/study/AssistantBlock";
import { SparklesIcon } from "@/components/ui/sparkles";
import { useTutorAsk } from "@/features/tutor";
import type { PracticeItem, PracticeSubmitResult } from "@/features/practice/schema/practice.schema";

export function PracticeExplainMore({
  courseId,
  sessionId,
  item,
  selectedChoiceId,
  result,
}: {
  courseId: string;
  sessionId: string;
  item: PracticeItem;
  selectedChoiceId: string;
  result: PracticeSubmitResult;
}) {
  const explain = useTutorAsk(courseId);
  const replyId = useId();
  const [reply, setReply] = useState<string | null>(null);
  const [animationKey, setAnimationKey] = useState<string | undefined>();
  const [requestNumber, setRequestNumber] = useState(0);

  function askForExplanation() {
    const correctOptionId = result.correctOptionId ?? (result.correct ? selectedChoiceId : null);
    const studentAnswer = item.choices.find((choice) => choice.id === selectedChoiceId)?.label ?? "Unavailable";
    const correctAnswer = result.correctAnswerText ??
      item.choices.find((choice) => choice.id === correctOptionId)?.label ??
      (result.correct ? studentAnswer : "Unavailable");
    const nextRequest = requestNumber + 1;
    setRequestNumber(nextRequest);
    setReply(null);
    setAnimationKey(`${courseId}:${sessionId}:${item.id}:explain:${replyId}:${nextRequest}`);
    explain.mutate(
      {
        question: [
          "Explain the feedback for this graded practice question.",
          `Question: ${item.prompt}`,
          `Options: ${item.choices.map((choice) => `${choice.id}: ${choice.label}`).join(" | ")}`,
          `Student's answer: ${studentAnswer}`,
          `Correct answer: ${correctAnswer}`,
          `Stored explanation: ${result.explanation}`,
        ].join("\n\n"),
        style: "detail",
      },
      {
        onSuccess: (response) => setReply(response.answer),
        onError: () => toast.error("Could not load an explanation. Try again."),
      }
    );
  }

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={askForExplanation}
        disabled={explain.isPending}
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:text-foreground disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <SparklesIcon size={14} aria-hidden />
        {explain.isPending ? "Thinking…" : "Explain more"}
      </button>
      {reply || explain.isPending ? (
        <AssistantBlock
          text={reply ?? undefined}
          pending={explain.isPending}
          pendingLabel="Kala is thinking…"
          animationKey={animationKey}
        />
      ) : null}
    </div>
  );
}
