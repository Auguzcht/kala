import { cn } from "@/lib/utils";

// Brief loading state: the static hornbill and one waiting line.
// Used on the /launch returning/reduced-motion path — no line animation,
// just the brand and a short beat. Deliberately no SVG and no motion
// involvement: a lightweight, reusable loading surface for wherever a quiet
// "one moment" is needed later. Titles come as props (not hardcoded) so the
// same component can carry different copy per surface.
export function BriefLoading({
  title,
  subtitle,
  className,
}: {
  title: string;
  subtitle?: string;
  className?: string;
}) {
  return (
    <div role="status" className={cn("flex flex-col items-center px-6 text-center", className)}>
      <img
        src="/Kala-Logo.png"
        alt="Kala"
        className="mb-5 size-16 rounded-xl object-contain"
      />
      <div className="font-display text-[17px] font-semibold text-foreground">{title}</div>
      <span className="sr-only">{subtitle}</span>
      <div aria-hidden className="mt-5 w-full max-w-xs space-y-2">
        <div className="h-3 w-full rounded-sm bg-muted" />
        <div className="h-3 w-2/3 rounded-sm bg-muted" />
      </div>
    </div>
  );
}
