import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

// System states (per the mockup "System States"): launch-failed,
// unauthorized, session-expired, not-found. Each is an icon circle +
// title + body + one CTA. Direction, not apology.
export function SystemState({
  icon,
  iconClass,
  title,
  body,
  cta,
  className,
}: {
  icon: ReactNode;
  iconClass: string;
  title: string;
  body: string;
  cta?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mx-auto w-full max-w-md px-6", className)}>
      <div className="border bg-card px-8 py-12 text-center">
        <div className={cn("mx-auto mb-5 grid size-12 place-items-center", iconClass)}>
          {icon}
        </div>
        <h1 className="font-display text-lg font-semibold text-foreground">{title}</h1>
        <p className="mx-auto mt-2.5 max-w-sm text-[13px] leading-relaxed text-muted-foreground">
          {body}
        </p>
        {cta ? <div className="mt-6">{cta}</div> : null}
      </div>
    </div>
  );
}
