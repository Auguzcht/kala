import { useState } from "react";
import { CheckIcon } from "lucide-react";
import { CompassIcon } from "@/components/ui/compass";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { MasteryBand } from "@/components/kala";
import type { TwinSkill } from "@/features/twin";

// Shared topic picker for Practice and Flashcards. Both surfaces used to
// only ever generate against an algorithmic pick (weakest skill for
// practice, due-first for flashcards), with no way for the student to just
// say "I want to work on THIS one" — the auto pick is still the default and
// still the recommended path, this only adds the option to override it.
//
// A Sheet + searchable Command list, not a Select dropdown (the first cut
// used one, and it broke down exactly as you'd expect once skill names got
// long: the panel overflowed its trigger, and Radix's SelectValue mirrored
// the same cramped name+badge row into the closed trigger). This reuses
// the exact drawer pattern already established for the instructor's
// LearnerSheet — same Sheet/SheetHeader shape, same "boxed" feel — plus a
// real search input, so a course with dozens of skills stays usable
// instead of a scroll-forever dropdown.
//
// AUTO is a sentinel, not an empty string: cmdk/Command items need a real
// value to filter and select on, and the caller passes `undefined` as the
// actual skillId to the API whenever this value is chosen, so "auto" never
// leaks past this component.
export const TOPIC_AUTO = "auto";

export function TopicPicker({
  skills,
  value,
  onChange,
  disabled,
  autoLabel = "Weakest skill (recommended)",
}: {
  skills: TwinSkill[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  autoLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const selectedLabel =
    value === TOPIC_AUTO ? autoLabel : (skills.find((s) => s.skillId === value)?.name ?? autoLabel);

  function choose(next: string) {
    onChange(next);
    setOpen(false);
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={disabled}
          className="max-w-[220px] justify-start gap-2"
        >
          <CompassIcon size={14} className="shrink-0 text-muted-foreground" aria-hidden />
          <span className="min-w-0 flex-1 truncate text-left font-normal">{selectedLabel}</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full gap-0 p-0 sm:max-w-md" aria-describedby={undefined}>
        <SheetHeader className="border-b px-6 py-4">
          <SheetTitle className="font-display text-base">Choose a topic</SheetTitle>
          <SheetDescription className="text-xs">
            Defaults to the recommended pick, search or scroll to work on something specific
            instead.
          </SheetDescription>
        </SheetHeader>
        <Command className="flex-1 rounded-none bg-transparent">
          <CommandInput placeholder="Search topics…" />
          <CommandList className="max-h-[calc(100dvh-9rem)]">
            <CommandEmpty>No topics match.</CommandEmpty>
            <CommandGroup>
              <CommandItem value={autoLabel} onSelect={() => choose(TOPIC_AUTO)} className="py-2.5">
                <CompassIcon size={14} className="shrink-0 text-brand-orange" aria-hidden />
                <span className="min-w-0 flex-1 truncate">{autoLabel}</span>
                {value === TOPIC_AUTO ? (
                  <CheckIcon className="size-4 shrink-0 text-brand-orange" aria-hidden />
                ) : null}
              </CommandItem>
              {skills.map((s) => (
                <CommandItem
                  key={s.skillId}
                  value={s.name}
                  onSelect={() => choose(s.skillId)}
                  className="py-2.5"
                >
                  <span className="min-w-0 flex-1 truncate">{s.name}</span>
                  <MasteryBand band={s.band} className="shrink-0" />
                  {value === s.skillId ? (
                    <CheckIcon className="size-4 shrink-0 text-brand-orange" aria-hidden />
                  ) : null}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </SheetContent>
    </Sheet>
  );
}
