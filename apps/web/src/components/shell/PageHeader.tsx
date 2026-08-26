import { cn } from "@/lib/utils";

// Page heading: small uppercase eyebrow + large Space Grotesk title + a
// short supporting line. Left-aligned, one clear job per screen.
export function PageHeader({
  eyebrow,
  title,
  description,
  className,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  className?: string;
}) {
  return (
    <div className={cn("mb-8", className)}>
      {eyebrow ? (
        <p className="text-xs font-medium uppercase tracking-[0.06em] text-brand-slate">
          {eyebrow}
        </p>
      ) : null}
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
      {description ? (
        <p className="mt-2 max-w-xl text-sm text-muted-foreground">{description}</p>
      ) : null}
    </div>
  );
}
