import { getSessionToken } from "@/lib/auth/session";

// Minimal fetch client. Types are GENERATED from the backend OpenAPI schema
// (pnpm gen:api -> types.gen.ts). Do not hand-write API types.
// Vercel mounts the api service at /api/api (same origin, see root vercel.json);
// the fallback keeps the deployed SPA working without a build-time env var,
// while .env.local still overrides it for local dev.
const baseUrl = (import.meta.env.VITE_API_BASE_URL as string) || "/api/api";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getSessionToken();
  if (!token) {
    throw new Error("No Kala session token. Open Kala from the LMS.");
  }

  const res = await fetch(`${baseUrl}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return (await res.json()) as T;
}
