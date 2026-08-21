import { createClient } from "@supabase/supabase-js";
import { getSessionToken } from "@/lib/auth/session";

const url = import.meta.env.VITE_SUPABASE_URL as string;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

export function getSupabase() {
  const token = getSessionToken();

  return createClient(url, anonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: token
      ? { headers: { Authorization: `Bearer ${token}` } }
      : undefined,
  });
}
