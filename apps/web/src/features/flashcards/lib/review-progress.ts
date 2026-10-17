import { z } from "zod";

const progressSchema = z.object({
  sessionId: z.string(),
  queue: z.array(z.string()).min(1),
  index: z.number().int().nonnegative(),
  ratings: z.record(z.string(), z.boolean()),
  posted: z.array(z.string()),
  pending: z.object({ itemId: z.string(), remembered: z.boolean(), key: z.string() }).nullable(),
});
export type ReviewProgress = z.infer<typeof progressSchema>;

// Tab-scoped, user/attempt/item-scoped, and IDs only. Storage can be blocked;
// review still works in memory. Never restore unconfirmed optimistic progress.
export function readReviewProgress(key: string | null): ReviewProgress | null {
  if (!key) return null;
  try {
    const parsed = progressSchema.safeParse(JSON.parse(sessionStorage.getItem(key) ?? "null"));
    if (!parsed.success || parsed.data.index >= parsed.data.queue.length) return null;
    return parsed.data;
  } catch { return null; }
}
export function writeReviewProgress(key: string | null, progress: ReviewProgress | null) {
  if (!key) return;
  try {
    if (progress) sessionStorage.setItem(key, JSON.stringify(progress));
    else sessionStorage.removeItem(key);
  } catch { /* Keep the current session usable without browser storage. */ }
}
