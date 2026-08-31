import { getSessionToken } from "@/lib/auth/session";

// Minimal fetch client. Types are GENERATED from the backend OpenAPI schema
// (pnpm gen:api -> types.gen.ts). Do not hand-write API types.
const baseUrl = import.meta.env.VITE_API_BASE_URL as string;

export async function api<T>(
  path: string,
  init?: RequestInit,
  timeoutMs?: number
): Promise<T> {
  const token = getSessionToken();
  if (!token) {
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
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
    return (await res.json()) as T;
  } finally {
    if (timer) clearTimeout(timer);
  }
}
