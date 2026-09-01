import { type ReactNode } from "react";
import { useCourse } from "@/features/courses";
import { Skeleton } from "@/components/ui/skeleton";

// Shared top bar: `Kala / {course} / {section}[ / {subsection}]` breadcrumb
// + right slot. Hairline bottom border, white chrome (mockup "App Top Bar").
//
// `subsection` exists for routes nested under a shell's own layout route
// (the shell renders once for /class AND /class/student/$uid via <Outlet/>,
// so `section` alone can't tell them apart). Pass it when the shell can
// resolve a more specific label — a learner's name on their record page,
// for instance — so the crumb actually changes as the person navigates
// instead of reading "Instructor dashboard" everywhere under /class.
export function TopBar({
  courseId,
  section,
  subsection,
  right,
}: {
  courseId: string;
  section: string;
  subsection?: string;
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
      <span
        className={
          subsection
            ? "text-[13px] font-semibold text-muted-foreground"
            : "text-[13px] font-semibold text-brand-orange"
        }
      >
        {section}
      </span>
      {subsection ? (
        <>
          <span className="text-xs text-muted-foreground/50">/</span>
          <span className="max-w-56 truncate text-[13px] font-semibold text-brand-orange">
            {subsection}
          </span>
        </>
      ) : null}
      <div className="flex-1" />
      {right}
    </header>
  );
}
