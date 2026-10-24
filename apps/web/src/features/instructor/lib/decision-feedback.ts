// INSTR-REQ-001/002: start the real request now, retain visible feedback on
// fast responses, and never release a slow request before it actually ends.
export async function withDecisionFeedback<T>(request: () => Promise<T>): Promise<T> {
  const startedAt = Date.now();
  try {
    return await request();
  } finally {
    const remaining = 350 - (Date.now() - startedAt);
    if (remaining > 0) await new Promise<void>((resolve) => setTimeout(resolve, remaining));
  }
}
