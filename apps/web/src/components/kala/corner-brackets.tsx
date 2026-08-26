import { cn } from "@/lib/utils";

// Corner brackets — the signature `[ ]` tick on key panels, echoing the
// hornbill's angular crest (design brief, section 4). Sparingly: data
// panels the instructor/student must read precisely. Absolutely positioned
// over a `relative` panel.

export function CornerBrackets({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("pointer-events-none absolute inset-0", className)}
    >
      <span className="absolute -left-px -top-px size-4 border-l-2 border-t-2 border-brand-orange" />
      <span className="absolute -right-px -top-px size-4 border-r-2 border-t-2 border-brand-orange" />
    </div>
  );
}
