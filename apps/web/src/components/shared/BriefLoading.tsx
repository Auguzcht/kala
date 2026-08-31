import { cn } from "@/lib/utils";
import { Spinner } from "@/components/ui/spinner";

// Brief loading state: the hornbill, a spinner, and a title/subtitle pair.
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
    <div className={cn("flex flex-col items-center px-6 text-center", className)}>
      <img
        src="/Kala-Logo.png"
        alt="Kala"
        className="mb-5 size-16 rounded-xl object-contain"
      />
      <Spinner className="mb-5 size-6" />
      <div className="font-display text-[17px] font-semibold text-foreground">{title}</div>
      {subtitle ? (
        <div className="mt-1.5 text-[13px] text-muted-foreground">{subtitle}</div>
      ) : null}
    </div>
  );
}
