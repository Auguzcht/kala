import { api } from "@/lib/api/client";
import { parseApiResponse } from "@/lib/api/parse-response";
import {
  practiceSavedSetSchema,
  practiceSetListSchema,
  practiceSetSchema,
  practiceSubmitResultSchema,
  practiceSetResultsSchema,
  practiceRetakeResponseSchema,
  type PracticeSavedSet,
  type PracticeSet,
  type PracticeSetList,
  type PracticeSubmitResult,
  type PracticeSetResults,
  type PracticeRetakeResponse,
} from "@/features/practice/schema/practice.schema";

// Enqueue a batch of N items for one skill, grouped under a quiz_sets row.
// The 202 response is followed by GET /sets/{set_id} polling in the hook.
export async function fetchPracticeSet(
  courseId: string,
  args: { skillId?: string; size?: number } = {}
): Promise<PracticeSet> {
  const params = new URLSearchParams();
  if (args.skillId) params.set("skill_id", args.skillId);
  if (args.size) params.set("size", String(args.size));
  const query = params.toString() ? `?${params.toString()}` : "";
  const data = await api<unknown>(
    `/practice/${courseId}/set${query}`,
    { method: "POST" },
    15_000
  );
  return parseApiResponse(practiceSetSchema, data, `/practice/${courseId}/set`);
}

// Load a saved set by id, so test mode can run it instead of generating.
export async function fetchPracticeSetById(
  courseId: string,
  setId: string
): Promise<PracticeSavedSet> {
  const data = await api<unknown>(`/practice/${courseId}/sets/${setId}`);
  return parseApiResponse(practiceSavedSetSchema, data, `/practice/${courseId}/sets/${setId}`);
}

export async function fetchPracticeSetResults(
  courseId: string,
  setId: string,
  attemptId?: string,
): Promise<PracticeSetResults> {
  const query = attemptId ? `?attemptId=${encodeURIComponent(attemptId)}` : "";
  const endpoint = `/practice/${courseId}/sets/${setId}/results${query}`;
  const data = await api<unknown>(endpoint);
  return parseApiResponse(practiceSetResultsSchema, data, endpoint);
}

export async function startRetake(courseId: string, setId: string): Promise<PracticeRetakeResponse> {
  const endpoint = `/practice/${courseId}/sets/${setId}/retake`;
  const data = await api<unknown>(endpoint, { method: "POST" });
  return parseApiResponse(practiceRetakeResponseSchema, data, endpoint);
}

// The retake list for a skill (or the whole course when skillId is omitted).
export async function fetchPracticeSets(
  courseId: string,
  skillId?: string
): Promise<PracticeSetList> {
  const query = skillId ? `?skill_id=${encodeURIComponent(skillId)}` : "";
  const data = await api<unknown>(`/practice/${courseId}/sets${query}`);
  return parseApiResponse(practiceSetListSchema, data, `/practice/${courseId}/sets`);
}

export async function submitPracticeAttempt(
  courseId: string,
  args: {
    itemId: string;
    choiceId: string;
    latencyMs: number;
    setId?: string | null;
    attemptId?: string;
    sessionId: string;
    idempotencyKey: string;
  }
): Promise<PracticeSubmitResult> {
  const data = await api<unknown>(`/practice/${courseId}/submit`, {
    method: "POST",
    body: JSON.stringify({
      item_id: args.itemId,
      choice_id: args.choiceId,
      latency_ms: args.latencyMs,
      ...(args.setId ? { set_id: args.setId } : {}),
      ...(args.attemptId ? { attempt_id: args.attemptId } : {}),
      session_id: args.sessionId,
      idempotency_key: args.idempotencyKey,
    }),
  });
  return parseApiResponse(practiceSubmitResultSchema, data, `/practice/${courseId}/submit`);
}
