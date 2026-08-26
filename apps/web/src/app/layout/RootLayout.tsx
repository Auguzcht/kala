import { type ReactNode } from "react";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

// Root chrome: providers + toast surface only. Page chrome lives in the
// layouts — the course shell (side rail + top bar) for /course/*, and
// the launch/system-state surfaces for the public paths.
export function RootLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh bg-background text-foreground">
      <TooltipProvider>
        {children}
        <Toaster position="bottom-right" />
      </TooltipProvider>
    </div>
  );
}
