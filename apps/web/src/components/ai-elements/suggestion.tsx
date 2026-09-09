"use client";

import type { ComponentProps } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

// Not part of the five ai-elements files already vendored in this repo —
// confirmed absent (grep turned up nothing) before writing this, per the
// TODO doc's own flag that Suggestion wasn't verified installed the way
// the other five were. Hand-written to match the standard AI Elements
// Suggestion API (the `npx ai-elements add suggestion` shape): a
// horizontally-scrolling row of pill buttons, each carrying its own
// suggestion string. No new dependency, built entirely on the existing
// Button/ScrollArea primitives already in this repo.
//
// This is the follow-up chip row (Gizmo's "Explain like I'm 5 / Ask a
// question / More detail"), which maps onto the tutor style hints that
// already exist server-side (`_STYLE_HINTS` in routers/tutor.py:
// default/eli5/detail) but that nothing in the UI currently calls.

export type SuggestionsProps = ComponentProps<typeof ScrollArea>;

export const Suggestions = ({ className, children, ...props }: SuggestionsProps) => (
  <ScrollArea className={cn("w-full", className)} {...props}>
    <div className="flex w-max flex-nowrap items-center gap-2 pb-2">{children}</div>
    <ScrollBar orientation="horizontal" />
  </ScrollArea>
);

export type SuggestionProps = Omit<ComponentProps<typeof Button>, "onClick"> & {
  suggestion: string;
  onClick?: (suggestion: string) => void;
};

export const Suggestion = ({
  suggestion,
  onClick,
  className,
  variant = "outline",
  size = "sm",
  children,
  ...props
}: SuggestionProps) => (
  <Button
    className={cn("shrink-0 rounded-full px-4", className)}
    onClick={() => onClick?.(suggestion)}
    size={size}
    type="button"
    variant={variant}
    {...props}
  >
    {children ?? suggestion}
  </Button>
);
