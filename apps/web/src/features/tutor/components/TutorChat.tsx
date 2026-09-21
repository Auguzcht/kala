import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { toast } from "sonner";
import { ComposeDock } from "@/components/study/ComposeDock";
import { SessionBar } from "@/components/study/SessionBar";
import { StudySurface } from "@/components/study/StudySurface";
import { StudyStream } from "@/components/study/StudyStream";
import { UserBlock } from "@/components/study/UserBlock";
import { AssistantBlock } from "@/components/study/AssistantBlock";
import { FollowUpChips } from "@/components/study/FollowUpChips";
import { EmptyState } from "@/components/shared/EmptyState";
import { Shimmer } from "@/components/ai-elements/shimmer";
import { Spinner } from "@/components/ui/spinner";
import { FileTextIcon } from "@/components/ui/file-text";
import { XIcon } from "@/components/ui/x";
import { useSession } from "@/lib/auth/AuthProvider";
import { cn } from "@/lib/utils";
import { PromptInputButton } from "@/components/ai-elements/prompt-input";
import { askTutor, createTutorConversation } from "@/features/tutor/api/tutor.api";
import {
  useTutorConversations,
  useTutorConversation,
  useUploadTutorAttachment,
  useDeleteTutorAttachment,
} from "@/features/tutor";
import type { TutorStyle, TutorAttachment } from "@/features/tutor";

// Tutor as a real, resumable chat (Stage 2 of the AI overhaul, see
// docs/AI_OVERHAUL_TODO.md). Migrated onto the shared StudySurface +
// SessionBar + ComposeDock shell per docs/ai-overhaul-v2/05_TUTOR_AND_
// HIERARCHY.md, WITH ONE DEVIATION from that doc: the conversation switcher
// no longer lives in SessionBar's right slot as a Select dropdown. It's now
// TutorSidebar, a persistent extension of the left icon rail (see
// components/shell/CourseShell.tsx / TutorSidebar.tsx) — the same
// always-visible chat-history treatment ChatGPT/Claude/Perplexity give
// theirs, rather than a dropdown buried in the session bar.
//
// That move changes where the "which conversation is active" state lives:
// it's the /course/tutor route's `conversation` search param now, not local
// component state, because TutorSidebar (rendered by CourseShell) and this
// component are siblings, not parent/child — a URL param is the one thing
// both can read and write without a new global store.
//
// The compose input is ALWAYS mounted, not gated behind picking or
// creating a conversation first — the student tour drives this surface by
// finding #tour-tutor-input, filling it, and calling requestSubmit() on
// it directly (see TourRunner.tsx), synchronously on arrival at this
// route, so the input existing only after some async setup would break
// it. Conversation creation instead happens transparently inside the
// send flow the first time a message actually goes out, exactly as
// before — only WHERE the resulting id is stored changed (the URL, not
// useState).
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
// attach, upload right away, show it as a chip. ComposeDock is a layout
// shell for this, not a new owner of upload state — the hidden <input>,
// its ref, and handleFileSelect all stay here, same as before.

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
  const navigate = useNavigate();
  const { conversation: activeId } = useSearch({ from: "/course/tutor" });
  const active = useTutorConversation(activeId ?? null);
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
  // The question currently being answered, held until the server's message
  // list actually contains it. Gating the optimistic turn on `isPending`
  // instead meant it vanished the instant the request resolved — before the
  // invalidated query had refetched — so the stream showed nothing, then
  // snapped both turns in at once. Holding it until the real row exists makes
  // the handoff seamless.
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
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

  // Distinguishes "the active id changed because TutorSidebar (or a
  // bookmarked link) pointed us somewhere else" from "the active id changed
  // because OUR OWN send/attach flow just created a conversation and set the
  // param itself" — only the former should drop an in-flight optimistic
  // turn; the latter is that turn's own conversation coming into existence.
  const selfNavigatedRef = useRef(false);
  useEffect(() => {
    if (selfNavigatedRef.current) {
      selfNavigatedRef.current = false;
      return;
    }
    setPendingQuestion(null);
    setLastQuestion(null);
  }, [activeId]);

  // Auto-resume the most recently active conversation once the list loads
  // — a returning student sees their history without an extra click. Same
  // query key TutorSidebar's own useTutorConversations call uses, so React
  // Query dedupes the network request; this hook call is a shared cache
  // subscription, not a second fetch, and (unlike a one-shot getQueryData
  // read) it correctly re-renders once the data actually arrives instead
  // of only checking once and giving up. Runs ONCE off the initial load
  // only, and only when the URL didn't already name a conversation — a
  // fresh "New chat" (search cleared) must not snap back to the old thread.
  const conversations = useTutorConversations(courseId);
  const autoResumedRef = useRef(false);
  useEffect(() => {
    if (autoResumedRef.current || activeId || conversations.isLoading) return;
    autoResumedRef.current = true;
    const mostRecent = conversations.data?.[0];
    if (mostRecent) {
      selfNavigatedRef.current = true;
      void navigate({
        to: "/course/tutor",
        search: { conversation: mostRecent.id },
        replace: true,
      });
    }
  }, [activeId, conversations.data, conversations.isLoading, navigate]);

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
      let id = activeId;
      if (!id) {
        const convo = await createTutorConversation(courseId);
        id = convo.id;
        selfNavigatedRef.current = true;
        void navigate({ to: "/course/tutor", search: { conversation: id }, replace: true });
      }
      const result = await askTutor(courseId, question, style, id);
      return { ...result, conversationId: id };
    },
    onSuccess: async (data, variables) => {
      setLastQuestion(variables.question);
      // Await the refetch BEFORE dropping the optimistic turn, so the
      // persisted row is on screen first and the swap is invisible.
      await queryClient.invalidateQueries({
        queryKey: ["tutor-conversation", data.conversationId],
      });
      queryClient.invalidateQueries({ queryKey: ["tutor-conversations", courseId] });
      setPendingQuestion(null);
    },
    onError: () => {
      setPendingQuestion(null);
      toast.error("Kala couldn't answer that", {
        description: "Check your connection and try again.",
      });
    },
  });

  function askQuestion(question: string, style: TutorStyle = "default") {
    if (!question.trim() || send.isPending) return;
    // The student's turn appears immediately, before the request is even
    // sent — this is the whole point of the optimistic turn.
    setPendingQuestion(question);
    send.mutate({ question, style });
  }

  // Same "create transparently on first use" shape as askQuestion — a
  // student attaching a file before ever typing anything still needs
  // somewhere for it to live.
  async function handleFileSelect(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // reset so picking the same file again still fires onChange
    if (!file) return;

    let id = activeId;
    if (!id) {
      try {
        const convo = await createTutorConversation(courseId);
        id = convo.id;
        selfNavigatedRef.current = true;
        void navigate({ to: "/course/tutor", search: { conversation: id }, replace: true });
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
    if (!activeId) return;
    setRemovingId(attachmentId);
    deleteAttachment.mutate(
      { conversationId: activeId, attachmentId },
      {
        onError: () => toast.error("Couldn't remove that file"),
        onSettled: () => setRemovingId(null),
      }
    );
  }

  const messages = active.data?.messages ?? [];
  const lastMessage = messages.at(-1);

  return (
    <StudySurface
      bar={<SessionBar title={active.data?.title ?? "Ask Kala"} />}
      dock={
        <ComposeDock
          inputId="tour-tutor-input"
          onAsk={askQuestion}
          askPending={send.isPending}
          placeholder="Ask about this course…"
          attachmentSlot={
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
          }
          attachmentChips={
            active.data?.attachments && active.data.attachments.length > 0
              ? active.data.attachments.map((a) => (
                  <AttachmentChip
                    key={a.id}
                    attachment={a}
                    removing={removingId === a.id}
                    onRemove={() => handleRemoveAttachment(a.id)}
                  />
                ))
              : undefined
          }
        />
      }
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.md,text/plain,text/markdown,application/pdf"
        className="hidden"
        onChange={handleFileSelect}
      />

      <StudyStream>
        {activeId && active.isLoading ? (
          <Shimmer>Loading conversation…</Shimmer>
        ) : activeId && active.isError ? (
          // A conversation id in the URL that no longer resolves. More
          // reachable since the active id moved into the search param: a
          // back-button, a bookmark, or a link into a chat that has since
          // been deleted all land here, where the old local-state version
          // could only ever name a conversation it had just created.
          //
          // Without this branch the empty-messages case falls through to the
          // NEW-CHAT prompt below, so a deleted thread renders as a clean
          // "ask anything" screen and the student types into a conversation
          // that 404s on send. The sidebar still lists every live thread, so
          // the useful next step is naming that rather than offering a retry.
          <EmptyState
            title="That chat isn't available"
            description="It may have been deleted. Pick another chat from the list on the left, or start a new one."
          />
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
                // Only the newest reply types itself out. Replaying the
                // reveal on every message would make opening an existing
                // thread look like the whole conversation is being
                // regenerated.
                animate={m.id === lastMessage?.id}
              />
            )
          )
        )}

        {pendingQuestion ? (
          <>
            {/* The student's own turn, present the moment they hit send.
                It stays until the persisted copy arrives (cleared in the
                mutation's onSuccess after the refetch resolves), so there
                is never a gap where the question disappears. */}
            <div id="tour-tutor-user-turn" className="mr-auto w-full max-w-full">
              <UserBlock text={pendingQuestion} initials={userInitials || undefined} />
            </div>
            <AssistantBlock
              id="tour-tutor-thinking"
              pending
              pendingLabel="Kala is thinking…"
            />
          </>
        ) : null}

        {!send.isPending && lastQuestion ? (
          <div className="mr-auto max-w-[88%]">
            <FollowUpChips onPick={(style) => askQuestion(lastQuestion, style)} />
          </div>
        ) : null}
      </StudyStream>
    </StudySurface>
  );
}
