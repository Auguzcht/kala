import { z } from "zod";

// The session comes from the LTI launch, not a password login.
// The backend validates the launch and returns these claims.
export const sessionSchema = z.object({
  userId: z.string(),
  institutionId: z.string(), // tenant, resolved from LTI iss + deployment_id
  role: z.enum(["student", "instructor", "admin"]),
  courseId: z.string().optional(),
  displayName: z.string().optional(),
});

export type Session = z.infer<typeof sessionSchema>;

const STORAGE_KEY = "kala.session_token";

/** Decode the session JWT's claims without verifying the signature. The
 * backend already verified the LTI launch before minting this token, the
 * frontend just needs to read it, never trust a token it didn't get
 * straight from the backend's own /launch redirect. The payload is
 * base64url (JWT standard, `-`/`_`), which atob() cannot decode —
 * normalize it to standard base64 first (PyJWT emits base64url). */
function decodeClaims(token: string): Session | null {
  try {
    const segment = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(segment));
    return sessionSchema.parse({
      userId: payload.sub,
      institutionId: payload.institution_id,
      role: payload.app_role,
      courseId: payload.course_id ?? undefined,
      displayName: payload.display_name ?? undefined,
    });
  } catch {
    return null;
  }
}

/** BACKEND.md step 5: the backend redirects to /launch#token=...&course=....
 * Read it once, store it, then scrub the fragment so it doesn't linger in
 * browser history. */
export function captureLaunchToken(): Session | null {
  const hash = window.location.hash;
  const match = hash.match(/token=([^&]+)/);
  if (!match) return null;

  const token = decodeURIComponent(match[1]);
  const session = decodeClaims(token);
  if (!session) return null;

  sessionStorage.setItem(STORAGE_KEY, token);
  window.history.replaceState(null, "", window.location.pathname);
  return session;
}

export function loadStoredSession(): Session | null {
  const token = sessionStorage.getItem(STORAGE_KEY);
  return token ? decodeClaims(token) : null;
}

export function getSessionToken(): string | null {
  return sessionStorage.getItem(STORAGE_KEY);
}

export function clearSession(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}

