import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  askTutor,
  createTutorConversation,
  listTutorConversations,
  fetchTutorConversation,
  deleteTutorConversation,
} from "@/features/tutor/api/tutor.api";
import type { TutorStyle } from "@/features/tutor/schema/tutor.schema";

// Stateless per-turn ask: no conversation, no persistence, nothing kept
// after this call returns. Kept for any future one-off use (a quick ask
// with no thread to attach it to) — TutorChat itself no longer calls this
// directly as of Stage 2, it uses its own conversation-aware composite
// mutation instead (see TutorChat.tsx's `send`).
export function useAskTutor(courseId: string) {
  return useMutation({
    mutationFn: (question: string) => askTutor(courseId, question),
  });
}

// Same grounded ask with an explicit register for the follow-up chips
// (Hint = eli5 framing, Explain = detail framing). Used by surfaces that
// re-answer the same grounded context rather than a chat transcript —
// Lessons' Hint, Flashcards' Hint/Explain. Also unchanged by Stage 2, no
// conversationId here either, these stay one-off and unpersisted.
export function useTutorAsk(courseId: string) {
  return useMutation({
    mutationFn: (args: { question: string; style?: TutorStyle }) =>
      askTutor(courseId, args.question, args.style ?? "default"),
  });
}

// ---- Stage 2: persisted conversations (the freeform tutor surface) ----

export function useTutorConversations(courseId: string) {
  return useQuery({
    queryKey: ["tutor-conversations", courseId],
    queryFn: () => listTutorConversations(courseId),
  });
}

export function useTutorConversation(conversationId: string | null) {
  return useQuery({
    queryKey: ["tutor-conversation", conversationId],
    queryFn: () => fetchTutorConversation(conversationId as string),
    enabled: !!conversationId,
  });
}

export function useCreateTutorConversation(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (skillId?: string) => createTutorConversation(courseId, skillId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tutor-conversations", courseId] });
    },
  });
}

// Ask WITHIN a persisted conversation. Distinct from useAskTutor above —
// this one always carries a conversationId and invalidates both the
// specific thread and the list (title/updatedAt change on every message).
export function useAskInConversation(courseId: string, conversationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: { question: string; style?: TutorStyle }) =>
      askTutor(courseId, args.question, args.style ?? "default", conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tutor-conversation", conversationId] });
      queryClient.invalidateQueries({ queryKey: ["tutor-conversations", courseId] });
    },
  });
}

export function useDeleteTutorConversation(courseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) => deleteTutorConversation(conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tutor-conversations", courseId] });
    },
  });
}
