import { type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { AuthProvider } from "@/lib/auth/AuthProvider";

// Server state -> TanStack Query. Auth -> AuthProvider (session).
// Ephemeral UI state -> Zustand (see src/stores). Never mix these.
const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    // Kala has no dark mode today, forcedTheme pins next-themes to "light"
    // so components that read useTheme() (currently just the sonner
    // Toaster) get a real, defined value instead of resolving off an
    // unconfigured default. If dark mode gets built later, swap
    // forcedTheme for defaultTheme + enableSystem.
    <ThemeProvider attribute="class" forcedTheme="light">
      <QueryClientProvider client={queryClient}>
        <AuthProvider>{children}</AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
