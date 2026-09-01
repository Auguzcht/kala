import { Link } from "@tanstack/react-router";
import { LearnerTriage } from "@/features/instructor/components/LearnerTriage";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { ArrowRightIcon } from "@/components/ui/arrow-right";

// Sheet, not a page navigation, for the roster drill-down — and a sheet
// with a deliberately different job than the full record page.
//
// The reason it's a sheet at all: the teacher is triaging a class, and
// they will open three or four learners in a row. A route change throws
// away the roster scroll position, the filter, and the search each time,
// so a teacher pays a re-orientation cost per learner. A right-hand sheet
// keeps the roster underneath, so closing it returns them exactly where
// they were, and the cohort stays visible as context for the individual.
//
// What the sheet shows is triage-only (LearnerTriage): standing and the
// decision gate. The mastery instruments and activity history that need
// width live on the full record (/class/student/$uid, LearnerRecord) —
// bookmarkable, shareable, and the deep read when the sheet feels
// cramped. The link below is the escape hatch between the two tasks, not
// a duplicate of content that's already on screen.

export function LearnerSheet({
  courseId,
  userId,
  open,
  onOpenChange,
}: {
  courseId: string;
  userId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full gap-0 p-0 sm:max-w-2xl lg:max-w-3xl"
        aria-describedby={undefined}
      >
        <SheetHeader className="border-b px-6 py-4">
          <SheetTitle className="font-display text-base">Learner record</SheetTitle>
          <SheetDescription className="text-xs">
            Standing at a glance, and the decisions only you can make. Open the full record for
            mastery and activity history.
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100dvh-5.5rem)]">
          <div className="px-6 py-5">
            {userId ? (
              <>
                <LearnerTriage courseId={courseId} userId={userId} />
                <div className="mt-6 border-t pt-4">
                  <Button variant="outline" size="sm" asChild>
                    <Link to="/class/student/$uid" params={{ uid: userId }}>
                      Open full record <ArrowRightIcon size={14} />
                    </Link>
                  </Button>
                </div>
              </>
            ) : null}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
