import { createClient } from "@supabase/supabase-js";

// Public anon client only. The backend mints a Supabase-compatible session
// JWT after LTI validation (see docs/stack.md, decision 5). RLS enforces
// tenant isolation on every row via institution_id.
const url = import.meta.env.VITE_SUPABASE_URL as string;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

export const supabase = createClient(url, anonKey, {
  auth: { persistSession: true, autoRefreshToken: true },
});
