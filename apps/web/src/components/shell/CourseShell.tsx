import { Link, useLocation } from "@tanstack/react-router";
import {
  ClipboardList,
  Layers,
  LayoutGrid,
  MessagesSquare,
  Radar,
  Target,
  type LucideIcon,
} from "lucide-react";
import { type ReactNode } from "react";
import { useCourse } from "@/features/courses";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Skeleton } from "@/components/ui/skeleton";

// App shell for the course-scoped (LTI) surface. 56px icon side rail +
// 48px top bar, per the mockups ("App Side Rail", "App Top Bar"):
// hairline slate borders, white chrome, orange active accent.
// The shell is the instrument frame; pages render inside it.

const NAV: { to: string; label: string; icon: LucideIcon; end?: boolean }[] = [
  { to: "/course", label: "Workspace", icon: LayoutGrid, end: true },
  { to: "/course/diagnostic", label: "Diagnostic", icon: ClipboardList },
  { to: "/course/practice", label: "Practice", icon: Target },
  { to: "/course/flashcards", label: "Flashcards", icon: Layers },
  { to: "/course/tutor", label: "Tutor", icon: MessagesSquare },
  { to: "/course/twin", label: "Twin", icon: Radar },
];

const SECTION_LABELS: Record<string, string> = {
  "/course": "Workspace",
  "/course/diagnostic": "Diagnostic",
  "/course/practice": "Practice",
  "/course/flashcards": "Flashcards",
  "/course/tutor": "Tutor",
  "/course/twin": "Twin",
};

function initials(name?: string): string {
  if (!name) return "";
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();
}

export function CourseShell({
  courseId,
  displayName,
  children,
}: {
  courseId: string;
  displayName?: string;
  children: ReactNode;
}) {
  const { data: course } = useCourse(courseId);
  const { pathname } = useLocation();
  const section = SECTION_LABELS[pathname] ?? SECTION_LABELS["/course"];

  return (
    <div className="min-h-dvh bg-background">
      {/* Side rail */}
      <nav
        aria-label="Course"
        className="fixed inset-y-0 left-0 z-20 flex w-14 flex-col items-center border-r bg-card px-0 py-4"
      >
        <Link to="/course" className="mb-5">
          <img
            src="/assets/kala-mark.png"
            alt="Kala"
            className="h-6 w-6 object-contain"
          />
        </Link>
        <div className="flex flex-1 flex-col gap-1.5">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <Tooltip key={to}>
              <TooltipTrigger asChild>
                <Link
                  to={to}
                  activeOptions={{ exact: end }}
                  activeProps={{
                    className:
                      "flex h-9 w-9 items-center justify-center border-l-2 border-brand-orange bg-brand-orange/10 text-brand-orange",
                  }}
                  inactiveProps={{
                    className:
                      "flex h-9 w-9 items-center justify-center border-l-2 border-transparent text-muted-foreground/70 hover:bg-accent hover:text-foreground",
                  }}
                  aria-label={label}
                >
                  <Icon className="size-4.5" />
                </Link>
              </TooltipTrigger>
              <TooltipContent side="right">{label}</TooltipContent>
            </Tooltip>
          ))}
        </div>
        <div
          className="grid size-7 place-items-center rounded-full bg-brand-slate text-[10px] font-semibold text-background"
          title={displayName}
        >
          {initials(displayName)}
        </div>
      </nav>

      {/* Content column */}
      <div className="pl-14">
        {/* Top bar */}
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
          <span className="font-mono text-xs text-muted-foreground">
            {initials(displayName) || section}
          </span>
        </header>

        <main className="mx-auto max-w-5xl px-6 py-8 pb-24">{children}</main>
      </div>
    </div>
  );
}
