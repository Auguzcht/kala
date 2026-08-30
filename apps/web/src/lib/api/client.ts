import { getSessionToken } from "@/lib/auth/session";

// Minimal fetch client. Types are GENERATED from the backend OpenAPI schema
// (pnpm gen:api -> types.gen.ts). Do not hand-write API types.
const baseUrl = import.meta.env.VITE_API_BASE_URL as string;

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
