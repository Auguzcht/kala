/**
 * Extract a human-readable reason from a thrown API error.
 *
 * The api client throws `new Error("API 502: {\"detail\":\"...\"}")` for a
 * non-2xx response, because FastAPI returns the useful sentence in a `detail`
 * field rather than on a typed field. Without this, every surface had to
 * either re-implement the parse or — worse — replace the server's specific
 * message with a generic "try again", which is actively wrong advice for a
 * permanent condition like "this skill has no course material yet". Retrying
 * that will never help, and telling a student to retry it wastes their time
 * while hiding a setup problem from whoever could fix it.
 *
 * Returns null when the error carries no usable detail, so callers can fall
 * back to their own generic copy.
 */
export function apiErrorReason(err: unknown): string | null {
  const raw = err instanceof Error ? err.message : typeof err === "string" ? err : "";
  const match = raw.match(/\{"detail":"(.*?)"\}/s);
  if (!match) return null;
  // The detail arrives JSON-escaped inside the message string; unescape the
  // common sequences so quotes and newlines read correctly in the UI.
  return match[1].replace(/\\"/g, '"').replace(/\\n/g, " ").trim() || null;
}
