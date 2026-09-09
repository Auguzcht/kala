import { getSessionToken, clearSession } from "@/lib/auth/session";
import { router } from "@/app/router";

// Minimal fetch client. Types are GENERATED from the backend OpenAPI schema
// (pnpm gen:api -> types.gen.ts). Do not hand-write API types.
const baseUrl = import.meta.env.VITE_API_BASE_URL as string;

// A 401 means the session token is missing, expired, or otherwise rejected
// by the backend. Without this, every caller was left to fail into
// whatever loading/error state it happened to be in — the user just saw a
// dead panel with no way out. This is the ONE place that response gets
// turned into a real destination: clear the stale token so nothing retries
// with it, then send the user to /session-expired, which already has the
// re-launch flow built (routes/session-expired.tsx). Only navigate once per
// dead session — a burst of parallel requests all rejecting at once should
// not fire redirect() a dozen times in the same tick.
let redirecting = false;

function handleExpiredSession() {
  if (redirecting) return;
  redirecting = true;
  clearSession();
  // replace: true — a dead session has no legitimate "back" to return to.
  router
    .navigate({ to: "/session-expired", replace: true })
    .catch(() => {})
    .finally(() => {
      redirecting = false;
    });
}

export async function api<T>(
  path: string,
  init?: RequestInit,
  timeoutMs?: number
): Promise<T> {
  const token = getSessionToken();
  if (!token) {
    handleExpiredSession();
    throw new Error("No Kala session token. Open Kala from the LMS.");
  }

  // Opt-in request timeout: only callers that pass timeoutMs get one (the
  // long-running model calls — tutor, lesson generation, ingest, skill
  // proposal — legitimately take 20-30s and must stay untouched). A hung
  // call without a timeout would otherwise sit forever, which is exactly
  // what the launch-prefetch calls want to avoid.
  const controller = timeoutMs ? new AbortController() : undefined;
  const timer = timeoutMs ? setTimeout(() => controller!.abort(), timeoutMs) : undefined;
  try {
    const res = await fetch(`${baseUrl}${path}`, {
      ...init,
      signal: controller?.signal,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
        Authorization: `Bearer ${token}`,
      },
    });
    if (res.status === 401) {
      handleExpiredSession();
      throw new Error("Session expired");
    }
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
    return (await res.json()) as T;
  } finally {
    if (timer) clearTimeout(timer);
  }
}
