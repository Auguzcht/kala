import type { ClockIcon } from "@/features/tutor/components/icons/clock";
import { useTutorIcon } from "@/features/tutor/hooks/use-tutor-icon";
import { DropdownMenuRadioItem } from "@/components/ui/dropdown-menu";
import type { ComponentProps } from "react";
import { DropdownMenuContent } from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

/** Open toward the right; Radix keeps the menu within narrow viewports. */
export function TutorHistoryMenuContent({
  className,
  ...props
}: ComponentProps<typeof DropdownMenuContent>) {
  return (
    <DropdownMenuContent
      side="bottom"
      align="start"
      sideOffset={8}
      collisionPadding={8}
      {...props}
      style={{ ...props.style, animation: "none", transition: "none" }}
      className={cn("min-w-48 rounded-xl p-2", className)}
    />
  );
}

export function TutorHistorySortItem({
  icon: Icon,
  children,
  ...props
}: ComponentProps<typeof DropdownMenuRadioItem> & { icon: typeof ClockIcon }) {
  const hover = useTutorIcon();
  return (
    <DropdownMenuRadioItem
      {...props}
      {...hover.events}
      className="gap-2 rounded-lg py-2"
    >
      <Icon
        ref={hover.ref}
        size={16}
        className="inline-flex"
        aria-hidden
        data-tutor-sort-icon
      />
      {children}
    </DropdownMenuRadioItem>
  );
}
