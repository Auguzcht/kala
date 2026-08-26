import { createContext, useContext, useState, type ReactNode } from "react";
import { loadStoredSession, type Session } from "@/lib/auth/session";

// Thin session context. The launch flow captures the token (see /launch),
// but AuthProvider boots BEFORE that capture runs — so it must be able to
// update once the launch resolves, or every post-launch layout would see a
// stale `null` and bounce back to /launch (the stuck-spinner ping-pong).
// Supabase owns the token; this context only exposes it. Do not store
// server data here.
const AuthContext = createContext<{
  session: Session | null;
  setSession: (session: Session | null) => void;
} | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Hydrate from whatever /launch already stored in a previous visit; the
  // setSession path updates it the moment a fresh launch resolves.
  const [session, setSession] = useState<Session | null>(() => loadStoredSession());
  return (
    <AuthContext.Provider value={{ session, setSession }}>{children}</AuthContext.Provider>
  );
}

export function useSession(): Session | null {
  return useContext(AuthContext)?.session ?? null;
}

export function useSetSession() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useSetSession must be used within AuthProvider");
  return ctx.setSession;
}
