import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function PrimaryAdvance({
  label,
  onClick,
  disabled,
  icon,
  id,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  icon?: ReactNode;
  id?: string;
}) {
  return (
    <button
      type="button"
      id={id}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center gap-2 rounded-full bg-brand-orange px-5 py-2.5",
        "text-sm font-semibold text-brand-orange-foreground",
        "transition-opacity hover:opacity-90 disabled:opacity-40",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      )}
    >
      {icon}
      {label}
    </button>
  );
}
