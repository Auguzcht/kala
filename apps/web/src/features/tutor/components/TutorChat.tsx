import { useEffect, useRef, useState } from "react";
import { TutorComposer } from "@/features/tutor/components/TutorComposer";
import { TutorWelcome } from "@/features/tutor/components/TutorWelcome";
import { pickGreeting, validateTutorFile, createConversationResolver } from "@/features/tutor/lib/presentation";
import { dockLayout } from "@/components/ai-elements/dock-layout";
import { useCourse } from "@/features/courses";
import { cn } from "@/lib/utils";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { toast } from "sonner";
import { StudyStream } from "@/components/study/StudyStream";
import { UserBlock } from "@/components/study/UserBlock";
import { AssistantBlock } from "@/components/study/AssistantBlock";
import { FollowUpChips } from "@/components/study/FollowUpChips";
import { Button } from "@/components/ui/button";
import { Shimmer } from "@/components/ai-elements/shimmer";
import { useSession } from "@/lib/auth/AuthProvider";
import { apiErrorReason } from "@/lib/api-error";
import { askTutor, createTutorConversation } from "@/features/tutor/api/tutor.api";
import {
  useTutorConversations,
  useTutorConversation,
  useUploadTutorAttachment,
  useDeleteTutorAttachment,
} from "@/features/tutor";
import type { TutorFileUploadResult } from "@/features/tutor/lib/attachments";
import type { TutorStyle, TutorConversationDetail } from "@/features/tutor";

type UnconfirmedTurn = {
  id: number;
  conversationId: string;
  question: string;
  answer: string;
  previousMessageIds: string[];
};

function hasSavedTurn(messages: TutorConversationDetail["messages"], turn: Omit<UnconfirmedTurn, "id">) {
  const previousIds = new Set(turn.previousMessageIds);
  // Bulk-inserted messages can share a timestamp; matching must not depend
  // on their relative order when the refetch sorts only by created_at.
  const newMessages = messages.filter((message) => !previousIds.has(message.id));
  return newMessages.some((message) => message.role === "user" && message.content === turn.question)
    && newMessages.some((message) => message.role === "assistant" && message.content === turn.answer);
}

// URL search state is shared with the shell sidebar. Saved data stays in Query;
// only in-flight and unconfirmed turns are retained locally.
export function TutorChat({ courseId }: { courseId: string }) {
  const session = useSession();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  // The shell renders while router matches are transitioning, so strict useSearch({ from })
  // requires the route to already be in the router's resolved match array,
  // which raced and crashed during real navigations. strict: false doesn't
  // have that requirement.
  const search = useSearch({ strict: false });
  const activeId =
    typeof search === "object" && search !== null && "conversation" in search
      ? (search as { conversation?: string }).conversation
      : undefined;
  const active = useTutorConversation(activeId ?? null);
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
  // The in-flight turn, held until the server's message list actually
  // contains it — gating on `isPending` instead meant it vanished the
  // instant the request resolved, before the invalidated query had
  // refetched, so the stream showed nothing then snapped both turns in at
  // once. Holding it until the real row exists makes the handoff seamless.
  //
  // On failure this does NOT clear to null the way it used to. It used to:
  // a toast fired and the student's question just vanished, with no way to
  // recover it short of retyping the whole thing. Now a failed turn stays
  // visible with an inline retry action — the toast is a secondary signal,
  // not the only record that anything happened.
  const [pendingTurn, setPendingTurn] = useState<
    { status: "asking" | "failed"; question: string; style: TutorStyle; message?: string } | null
  >(null);
  // Only returned answers missing from a successful refetch (or with a
  // failed refetch) live here. Stored conversation data stays in Query.
  const [unconfirmedTurns, setUnconfirmedTurns] = useState<UnconfirmedTurn[]>([]);
  const localTurnId = useRef(0);
  const dropTarget = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const uploadsInFlight = useRef(0);
  const [hasTyped, setHasTyped] = useState(false);
  const [greetingDate] = useState(() => new Date());
  const course = useCourse(courseId);
  const resolveConversation = useRef(createConversationResolver());
  const epoch = useRef(0);
  const [waitingLong, setWaitingLong] = useState(false);
  const askingSince = useRef(0);
  const uploadAttachment = useUploadTutorAttachment();
  const deleteAttachment = useDeleteTutorAttachment();
  const [removingId, setRemovingId] = useState<string | null>(null);
  const userInitials = (session?.displayName ?? "")
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

  // Our own lazy creation preserves the draft and in-flight turn.
  const selfNavigatedRef = useRef(false);
  useEffect(() => {
    if (selfNavigatedRef.current) {
      selfNavigatedRef.current = false;
      return;
    }
    epoch.current += 1;
    resolveConversation.current = createConversationResolver();
    setHasTyped(false);
    uploadsInFlight.current = 0;
    setUploading(false);
    setPendingTurn(null);
    setUnconfirmedTurns([]);
    setLastQuestion(null);
  }, [activeId]);

  // Resume once on entry; a later explicit New chat must stay empty.
  const conversations = useTutorConversations(courseId);
  const autoResumedRef = useRef(false);
  useEffect(() => {
    if (autoResumedRef.current || conversations.isLoading) return;
    autoResumedRef.current = true;
    if (activeId) return;
    const mostRecent = [...(conversations.data ?? [])].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))[0];
    if (mostRecent) {
      selfNavigatedRef.current = true;
      void navigate({
        to: "/course/tutor",
        search: { conversation: mostRecent.id },
        replace: true,
      });
    }
  }, [activeId, conversations.data, conversations.isLoading, navigate]);

  async function ensureConversation() {
    return resolveConversation.current(activeId, async () => {
      const origin = epoch.current;
      const conversation = await createTutorConversation(courseId);
      if (origin !== epoch.current) throw new Error("Chat changed before creation finished. Please try again.");
      selfNavigatedRef.current = true;
      void navigate({ to: "/course/tutor", search: { conversation: conversation.id }, replace: true });
      void queryClient.invalidateQueries({ queryKey: ["tutor-conversations", courseId] });
      return conversation.id;
    });
  }

  const send = useMutation({
    mutationFn: async ({ question, style }: { question: string; style: TutorStyle; origin: number }) => {
      const id = await ensureConversation();
      const previousMessageIds = queryClient.getQueryData<TutorConversationDetail>(
        ["tutor-conversation", id],
      )?.messages.map((message) => message.id) ?? [];
      const result = await askTutor(courseId, question, style, id);
      return { ...result, conversationId: id, previousMessageIds };
    },
    onSuccess: async (data, variables) => {
      if (variables.origin !== epoch.current) return;
      setLastQuestion(variables.question);
      // Preserve the normal saved-response handoff. A failed/missing save
      // must not discard an answer already returned by the tutor.
      let saved = false;
      try {
        await queryClient.invalidateQueries({
          queryKey: ["tutor-conversation", data.conversationId],
        }, { throwOnError: true });
        const refreshed = queryClient.getQueryData<TutorConversationDetail>(
          ["tutor-conversation", data.conversationId],
        );
        saved = hasSavedTurn(refreshed?.messages ?? [], { ...data, question: variables.question });
      } catch {
        // Keep the returned answer when the conversation refetch fails.
      }
      if (!saved) {
        const turn = {
          id: ++localTurnId.current,
          conversationId: data.conversationId,
          question: variables.question,
          answer: data.answer,
          previousMessageIds: data.previousMessageIds,
        };
        setUnconfirmedTurns((turns) => [...turns, turn]);
      }
      queryClient.invalidateQueries({ queryKey: ["tutor-conversations", courseId] });
      setPendingTurn(null);
    },
    onError: (error, variables) => {
      if (variables.origin !== epoch.current) return;
      // Keep the question and the server's retry message visible together.
      const message = apiErrorReason(error) ?? "Check your connection and try again.";
      setPendingTurn({ status: "failed", question: variables.question, style: variables.style, message });
      toast.error("Kala couldn't answer that", { description: message });
    },
  });

  function askQuestion(question: string, style: TutorStyle = "default") {
    if (!question.trim() || send.isPending || uploadsInFlight.current > 0) return;
    setHasTyped(true);
    // The student's turn appears immediately, before the request is even
    // sent — this is the whole point of the optimistic turn.
    askingSince.current = Date.now();
    setPendingTurn({ status: "asking", question, style });
    send.mutate({ question, style, origin: epoch.current });
  }

  function retryLastTurn() {
    if (!pendingTurn || send.isPending) return;
    const { question, style } = pendingTurn;
    askingSince.current = Date.now();
    setPendingTurn({ status: "asking", question, style });
    send.mutate({ question, style, origin: epoch.current });
  }

  async function handleFiles(files: File[]): Promise<TutorFileUploadResult> {
    const result: TutorFileUploadResult = { uploaded: [], failed: [] };
    if (!files.length) return result;
    const origin = epoch.current;
    let conversationId: string | undefined;
    uploadsInFlight.current += 1;
    setUploading(true);
    try {
      for (const file of files) {
        if (origin !== epoch.current) {
          result.failed.push(file);
          continue;
        }
        const reason = validateTutorFile(file);
        if (reason) {
          toast.error("Couldn't attach that file", { description: reason });
          result.failed.push(file);
          continue;
        }
        try {
          conversationId ??= await ensureConversation();
          if (origin !== epoch.current) {
            result.failed.push(file);
            continue;
          }
          const attachment = await uploadAttachment.mutateAsync({
            conversationId,
            file,
          });
          result.uploaded.push({ file, attachment });
          if (attachment.status === "failed")
            toast.error("Couldn't read that file", {
              description: "Remove it and try another file.",
            });
        } catch (error) {
          result.failed.push(file);
          if (origin === epoch.current)
            toast.error("Couldn't attach that file", {
              description: apiErrorReason(error) ?? "Please try again.",
            });
        }
      }
      return result;
    } finally {
      if (origin === epoch.current) {
        uploadsInFlight.current -= 1;
        setUploading(uploadsInFlight.current > 0);
      }
    }
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
  const localTurns = unconfirmedTurns.filter(
    (turn) => turn.conversationId === activeId && !hasSavedTurn(messages, turn),
  );

  const asking = pendingTurn?.status === "asking";
  useEffect(() => {
    const elapsed = asking ? Date.now() - askingSince.current : 0;
    setWaitingLong(asking && elapsed >= 8000);
    if (!asking) return;
    const timer = window.setTimeout(() => setWaitingLong(true), Math.max(0, 8000 - elapsed));
    return () => window.clearTimeout(timer);
  }, [asking, activeId]);
  const empty = !active.isLoading && !active.isError && messages.length === 0 && localTurns.length === 0 && !pendingTurn;

  return (
    <div data-study-surface ref={dropTarget} className="relative flex h-full min-h-0 flex-col">
      <div className={cn("flex min-h-0 flex-1 flex-col", empty && "grid grid-rows-[1fr_auto_1fr] overflow-y-auto after:content-['']")}>
      {empty ? <TutorWelcome greeting={pickGreeting(greetingDate, courseId, course.data?.title)} idle={!hasTyped} /> : <StudyStream>
        {activeId && active.isLoading ? <Shimmer>Loading conversation…</Shimmer> : null}
        {active.isError ? <div role="alert" className="space-y-2 text-sm"><p>This chat could not be loaded. Please try again.</p><Button variant="outline" onClick={() => void active.refetch()}>Retry</Button></div> : null}
        {messages.map((m) => m.role === "user" ? (
          <UserBlock key={m.id} text={m.content} initials={userInitials || undefined} />
        ) : (
          <AssistantBlock key={m.id} text={m.content} id={m.id === lastMessage?.id ? "tour-tutor-response" : undefined}
            animate={m.id === lastMessage?.id} animationKey={m.id === lastMessage?.id ? `${courseId}:tutor:${m.id}` : undefined} />
        ))}

        {localTurns.map((turn, index) => (
          <div key={turn.id} className="mr-auto w-full max-w-full">
            <UserBlock text={turn.question} initials={userInitials || undefined} />
            <AssistantBlock
              text={turn.answer}
              id={index === localTurns.length - 1 ? "tour-tutor-response" : undefined}
            />
            <p className="text-sm text-muted-foreground">This answer may not have been saved.</p>
          </div>
        ))}

        {pendingTurn ? (
          <>
            {/* The student's own turn, present the moment they hit send.
                It stays until the persisted copy arrives (cleared in the
                mutation's onSuccess after the refetch resolves) OR the
                request fails, in which case it stays visible with a retry
                action rather than disappearing. */}
            <div id="tour-tutor-user-turn" className="mr-auto w-full max-w-full">
              <UserBlock text={pendingTurn.question} initials={userInitials || undefined} />
            </div>
            {pendingTurn.status === "asking" ? (
              <AssistantBlock
                id="tour-tutor-thinking"
                pending
                pendingLabel={waitingLong ? "Still working on it" : "Thinking"}
              />
            ) : (
              <div className="mr-auto flex w-full max-w-full items-center gap-3 border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                <span className="flex-1">{pendingTurn.message ?? "Kala couldn't answer that."}</span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={retryLastTurn}
                  disabled={send.isPending}
                >
                  Retry
                </Button>
              </div>
            )}
          </>
        ) : null}

        {!send.isPending && lastQuestion ? (
          <div className="mr-auto w-full">
            <FollowUpChips onPick={(style) => askQuestion(lastQuestion, style)} />
          </div>
        ) : null}
      </StudyStream>}
      <div className={cn("shrink-0", empty ? "px-4" : dockLayout.footer)}>
        <div className={cn("mx-auto w-full max-w-[800px]", dockLayout.content)}>
          <TutorComposer key={`${courseId}:${epoch.current}`} dropTarget={dropTarget} onDragChange={setDragging}
            attachments={active.data?.attachments ?? []} onFiles={handleFiles}
            onRemove={handleRemoveAttachment} removingId={removingId} onAsk={askQuestion}
            onTyping={() => setHasTyped(true)} pending={send.isPending} uploading={uploading} />
        </div>
      </div>
      </div>
      {dragging ? <div aria-live="polite" className="pointer-events-none absolute inset-2 z-20 flex items-center justify-center rounded-xl border-2 border-dashed border-primary bg-background/95 p-6 text-center"><p className="font-display text-lg font-medium">Drop files to attach</p></div> : null}
    </div>
  );
}
