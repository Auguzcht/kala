import { type ReactNode } from "react";
import { KalaMark } from "@/components/brand/KalaMark";

export function RootLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="flex items-center gap-2 border-b px-6 py-4">
        <KalaMark className="h-6 w-6" />
        <span className="font-semibold tracking-tight">Kala</span>
      </header>
      <main>{children}</main>
    </div>
  );
}
