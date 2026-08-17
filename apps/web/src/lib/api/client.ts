// Minimal fetch client. Types are GENERATED from the backend OpenAPI schema
// (pnpm gen:api -> types.gen.ts). Do not hand-write API types.
const baseUrl = import.meta.env.VITE_API_BASE_URL as string;

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return (await res.json()) as T;
}
