import { createContext, useContext, type ReactNode } from "react";
import type { Session } from "@/lib/auth/session";

// Thin, read-only access to the current session. Supabase owns the token;
// this context only exposes it for convenience. Do not store server data here.
const AuthContext = createContext<Session | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // TODO: hydrate the session from the backend after LTI launch.
  const session: Session | null = null;
  return <AuthContext.Provider value={session}>{children}</AuthContext.Provider>;
}

export function useSession(): Session | null {
  return useContext(AuthContext);
}
