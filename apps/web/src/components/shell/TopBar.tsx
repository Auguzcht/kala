import { type ReactNode } from "react";
import { useCourse } from "@/features/courses";
import { Skeleton } from "@/components/ui/skeleton";

// Shared top bar: `Kala / {course} / {section}` breadcrumb + right slot.
// Hairline bottom border, white chrome (mockup "App Top Bar").
export function TopBar({
  courseId,
  section,
  right,
}: {
  courseId: string;
  section: string;
  right?: ReactNode;
}) {
  const { data: course } = useCourse(courseId);

  return (
    <header className="flex h-12 items-center gap-2 border-b bg-card px-5">
      <span className="text-[13px] font-semibold text-muted-foreground/80">Kala</span>
      <span className="text-xs text-muted-foreground/50">/</span>
      {course ? (
        <span className="text-[13px] font-semibold text-foreground">{course.title}</span>
      ) : (
        <Skeleton className="h-3.5 w-40" />
      )}
      <span className="text-xs text-muted-foreground/50">/</span>
      <span className="text-[13px] font-semibold text-brand-orange">{section}</span>
      <div className="flex-1" />
      {right}
    </header>
  );
}
