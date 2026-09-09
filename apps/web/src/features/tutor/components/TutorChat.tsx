import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { StudySessionShell } from "@/components/study/StudySessionShell";
import { StudyStream } from "@/components/study/StudyStream";
import { UserBlock } from "@/components/study/UserBlock";
import { AssistantBlock } from "@/components/study/AssistantBlock";
import { FollowUpChips } from "@/components/study/FollowUpChips";
import { CornerBrackets } from "@/components/kala";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Shimmer } from "@/components/ai-elements/shimmer";
import { Spinner } from "@/components/ui/spinner";
import { FileTextIcon } from "@/components/ui/file-text";
import { XIcon } from "@/components/ui/x";
import { useSession } from "@/lib/auth/AuthProvider";
import { cn } from "@/lib/utils";
import {
  PromptInput,
  PromptInputBody,
  PromptInputTextarea,
  PromptInputFooter,
  PromptInputTools,
  PromptInputButton,
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
import {
  useTutorConversations,
  useTutorConversation,
  useUploadTutorAttachment,
  useDeleteTutorAttachment,
} from "@/features/tutor";
import type { TutorStyle, TutorAttachment } from "@/features/tutor";

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
// Stage 4: private study-aid uploads. A student's own file (.txt, .md,
// .pdf, 5MB cap), scoped to exactly this conversation — never the shared
// RAG corpus (see migration 0011's own comment for why). Deliberately NOT
// wired through PromptInput's own built-in attachment staging (drag-drop,
// paste, multi-file compose-then-send) — that system stages files as
// blob-URLs meant to travel together with the next chat message, and
// round-tripping a real File back out of that just to upload it
// immediately and independently of any text message is more complexity
// than this needs. A plain file input covers the actual model here:
// attach, upload right away, show it as a chip.

function AttachmentChip({
  attachment,
  onRemove,
  removing,
}: {
  attachment: TutorAttachment;
  onRemove: () => void;
  removing: boolean;
}) {
  return (
    <span className="inline-flex max-w-[220px] items-center gap-1.5 rounded-full border bg-card px-2.5 py-1 text-xs">
      {attachment.status === "processing" ? (
        <Spinner className="size-3 shrink-0" />
      ) : (
        <FileTextIcon
          size={12}
          className={cn(
            "shrink-0",
            attachment.status === "failed" ? "text-destructive" : "text-muted-foreground"
          )}
        />
      )}
      <span className="truncate">{attachment.filename}</span>
      {attachment.status === "failed" ? (
        <span className="shrink-0 text-destructive">couldn't read</span>
      ) : null}
      <button
        type="button"
        onClick={onRemove}
        disabled={removing}
        aria-label={`Remove ${attachment.filename}`}
        className="shrink-0 text-muted-foreground hover:text-foreground disabled:opacity-50"
      >
        <XIcon size={12} />
      </button>
    </span>
  );
}

export function TutorChat({ courseId }: { courseId: string }) {
  const session = useSession();
  const queryClient = useQueryClient();
  const conversations = useTutorConversations(courseId);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const active = useTutorConversation(conversationId);
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uploadAttachment = useUploadTutorAttachment();
  const deleteAttachment = useDeleteTutorAttachment();
  const [removingId, setRemovingId] = useState<string | null>(null);
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
    onError: () => {
      toast.error("Kala couldn't answer that", {
        description: "Check your connection and try again.",
      });
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

  // Same "create transparently on first use" shape as askQuestion — a
  // student attaching a file before ever typing anything still needs
  // somewhere for it to live.
  async function handleFileSelect(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // reset so picking the same file again still fires onChange
    if (!file) return;

    let id = conversationId;
    if (!id) {
      try {
        const convo = await createTutorConversation(courseId);
        id = convo.id;
        setConversationId(id);
      } catch {
        toast.error("Couldn't start a chat for that file");
        return;
      }
    }
    uploadAttachment.mutate(
      { conversationId: id, file },
      {
        onError: () => {
          toast.error("Couldn't attach that file", {
            description: "Only .txt, .md, and .pdf under 5MB are supported.",
          });
        },
      }
    );
  }

  function handleRemoveAttachment(attachmentId: string) {
    if (!conversationId) return;
    setRemovingId(attachmentId);
    deleteAttachment.mutate(
      { conversationId, attachmentId },
      {
        onError: () => toast.error("Couldn't remove that file"),
        onSettled: () => setRemovingId(null),
      }
    );
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
          {active.data?.attachments && active.data.attachments.length > 0 ? (
            <div className="mb-2.5 flex flex-wrap gap-2">
              {active.data.attachments.map((a) => (
                <AttachmentChip
                  key={a.id}
                  attachment={a}
                  removing={removingId === a.id}
                  onRemove={() => handleRemoveAttachment(a.id)}
                />
              ))}
            </div>
          ) : null}

          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.md,text/plain,text/markdown,application/pdf"
            className="hidden"
            onChange={handleFileSelect}
          />

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
              <PromptInputTools>
                <PromptInputButton
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadAttachment.isPending}
                  aria-label="Attach a file"
                >
                  {uploadAttachment.isPending ? (
                    <Spinner className="size-3.5" />
                  ) : (
                    <FileTextIcon size={15} />
                  )}
                </PromptInputButton>
              </PromptInputTools>
              <PromptInputSubmit disabled={send.isPending} status={send.isPending ? "submitted" : undefined} />
            </PromptInputFooter>
          </PromptInput>
        </div>
      </div>
    </StudySessionShell>
  );
}
