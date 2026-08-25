import { type ReactNode } from "react";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

// Root chrome: compact hornbill mark (real brand asset, see public/assets)
// + wordmark. Instrument header: hairline border, generous whitespace.
export function RootLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh bg-background text-foreground">
      <TooltipProvider>
        <header className="flex items-center gap-2.5 border-b bg-card px-6 py-3.5">
          <img
            src="/assets/kala-mark.png"
            alt="Kala"
            className="h-8 w-auto object-contain"
          />
          <span className="font-display text-lg font-semibold tracking-tight">Kala</span>
        </header>
        <main>{children}</main>
        <Toaster position="bottom-right" />
      </TooltipProvider>
    </div>
  );
}
