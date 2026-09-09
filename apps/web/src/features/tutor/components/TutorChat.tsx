import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { StudySessionShell } from "@/components/study/StudySessionShell";
import { StudyStream } from "@/components/study/StudyStream";
import { UserBlock } from "@/components/study/UserBlock";
import { AssistantBlock } from "@/components/study/AssistantBlock";
import { FollowUpChips } from "@/components/study/FollowUpChips";
import { CornerBrackets } from "@/components/kala";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Shimmer } from "@/components/ai-elements/shimmer";
import { useSession } from "@/lib/auth/AuthProvider";
import {
  PromptInput,
  PromptInputBody,
  PromptInputTextarea,
  PromptInputFooter,
  PromptInputSubmit,
} from "@/components/ai-elements/prompt-input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { askTutor, createTutorConversation } from "@/features/tutor/api/tutor.api";
import { useTutorConversations, useTutorConversation } from "@/features/tutor";
import type { TutorStyle } from "@/features/tutor";

// Tutor as a real, resumable chat (Stage 2 of the AI overhaul, see
// docs/AI_OVERHAUL_TODO.md). Previously this was a stateless single-turn
// box — every question independent, nothing kept on refresh. Now it's a
// stream of persisted turns, same StudyStream every other surface sits on,
// plus a conversation switcher and follow-up chips wired to the eli5/
// detail style hints that already existed server-side with nothing
// calling them.
//
// The compose input is ALWAYS mounted, not gated behind picking or
// creating a conversation first — the student tour drives this surface by
// finding #tour-tutor-input, filling it, and calling requestSubmit() on
// it directly (see TourRunner.tsx), synchronously on arrival at this
// route, so the input existing only after some async setup would break
// it. Conversation creation instead happens transparently inside the
// send flow the first time a message actually goes out.
//
// File uploads are Stage 4. PromptInput already ships full attachment
// support (drag-drop, paste, screenshot capture), it's just not surfaced
// here yet — the backend to receive and ground an upload doesn't exist,
// wiring the UI early would be a dead button.

export function TutorChat({ courseId }: { courseId: string }) {
  const session = useSession();
  const queryClient = useQueryClient();
  const conversations = useTutorConversations(courseId);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const active = useTutorConversation(conversationId);
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
  const userInitials = (session?.displayName ?? "")
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

  // Auto-resume the most recently active conversation once the list loads
  // — a returning student sees their history without an extra click. Runs
  // ONCE off the initial load only (the ref guard), not every time
  // conversationId happens to be null, otherwise clicking "New chat"
  // (which sets conversationId back to null) would immediately snap back
  // to the old thread instead of actually starting fresh.
  const autoResumedRef = useRef(false);
  useEffect(() => {
    if (autoResumedRef.current || conversations.isLoading) return;
    autoResumedRef.current = true;
    const mostRecent = conversations.data?.[0];
    if (mostRecent) setConversationId(mostRecent.id);
  }, [conversations.data, conversations.isLoading]);

  // One mutation covers both "create a conversation if this is the first
  // message" and "ask within it" — a single composite step, not two
  // separate hook calls coordinated by outer state. That coordination is
  // exactly where a stale-closure bug lives: if creation and asking were
  // two different useMutation objects, the ask mutation's closure could
  // still be holding the pre-creation (null) conversationId depending on
  // timing. Threading the resolved id through this mutation's OWN return
  // value instead of reading outer state in onSuccess avoids that.
  const send = useMutation({
    mutationFn: async ({ question, style }: { question: string; style: TutorStyle }) => {
      let id = conversationId;
      if (!id) {
        const convo = await createTutorConversation(courseId);
        id = convo.id;
        setConversationId(id);
      }
      const result = await askTutor(courseId, question, style, id);
      return { ...result, conversationId: id };
    },
    onSuccess: (data, variables) => {
      setLastQuestion(variables.question);
      queryClient.invalidateQueries({ queryKey: ["tutor-conversation", data.conversationId] });
      queryClient.invalidateQueries({ queryKey: ["tutor-conversations", courseId] });
    },
  });

  function startNewChat() {
    setConversationId(null);
    setLastQuestion(null);
  }

  function askQuestion(question: string, style: TutorStyle = "default") {
    if (!question.trim() || send.isPending) return;
    send.mutate({ question, style });
  }

  const messages = active.data?.messages ?? [];
  const lastMessage = messages.at(-1);

  return (
    <StudySessionShell
      right={
        conversations.data && conversations.data.length > 0 ? (
          <div className="flex items-center gap-2">
            <Select value={conversationId ?? undefined} onValueChange={setConversationId}>
              <SelectTrigger size="sm" className="w-[200px]">
                <SelectValue placeholder="Select a chat" />
              </SelectTrigger>
              <SelectContent>
                {conversations.data.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    <span className="truncate">{c.title ?? "Untitled chat"}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={startNewChat}>
              New chat
            </Button>
          </div>
        ) : null
      }
    >
      <div className="relative border bg-card">
        <CornerBrackets />
        <div className="flex items-center justify-between gap-3 border-b px-5 py-3">
          <span className="truncate text-sm font-semibold text-foreground">
            {active.data?.title ?? "Ask Kala"}
          </span>
        </div>

        <StudyStream>
          {conversationId && active.isLoading ? (
            <Shimmer>Loading conversation…</Shimmer>
          ) : messages.length === 0 ? (
            <EmptyState
              title="Ask anything about this course"
              description="Kala answers grounded in the actual course content, and never the answer to something graded."
            />
          ) : (
            messages.map((m) =>
              m.role === "user" ? (
                <UserBlock key={m.id} text={m.content} initials={userInitials || undefined} />
              ) : (
                <AssistantBlock
                  key={m.id}
                  text={m.content}
                  id={m.id === lastMessage?.id ? "tour-tutor-response" : undefined}
                />
              )
            )
          )}

          {send.isPending ? (
            <div id="tour-tutor-thinking" className="mr-auto flex max-w-[88%] items-start gap-2.5">
              <img src="/Kala-Logo.png" alt="Kala" className="mt-0.5 size-7 shrink-0 object-contain" />
              <div className="rounded-md border bg-card px-4 py-3.5">
                <Shimmer>Kala is thinking…</Shimmer>
              </div>
            </div>
          ) : null}

          {!send.isPending && lastQuestion ? (
            <div className="mr-auto max-w-[88%]">
              <FollowUpChips onPick={(style) => askQuestion(lastQuestion, style)} />
            </div>
          ) : null}
        </StudyStream>

        <div className="border-t p-3">
          <PromptInput
            id="tour-tutor-input"
            onSubmit={(message) => {
              askQuestion(message.text);
            }}
          >
            <PromptInputBody>
              <PromptInputTextarea placeholder="Ask about this course…" />
            </PromptInputBody>
            <PromptInputFooter>
              <PromptInputSubmit disabled={send.isPending} status={send.isPending ? "submitted" : undefined} />
            </PromptInputFooter>
          </PromptInput>
        </div>
      </div>
    </StudySessionShell>
  );
}
