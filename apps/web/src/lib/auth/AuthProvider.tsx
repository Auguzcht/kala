import { createContext, useContext, useState, type ReactNode } from "react";
import { loadStoredSession, type Session } from "@/lib/auth/session";

// Thin, read-only access to the current session. Supabase owns the token;
// this context only exposes it for convenience. Do not store server data here.
const AuthContext = createContext<Session | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Hydrate once from whatever the /launch route already captured and
  // stored. This provider never mints or captures tokens itself, it just
  // reads what's there.
  const [session] = useState<Session | null>(() => loadStoredSession());
  return <AuthContext.Provider value={session}>{children}</AuthContext.Provider>;
}

export function useSession(): Session | null {
  return useContext(AuthContext);
}
