import { Link, useLocation } from "@tanstack/react-router";
import { type ComponentType, type ReactNode } from "react";
import { ActivityIcon } from "@/components/ui/activity";
import { FileTextIcon } from "@/components/ui/file-text";
import { GraduationCapIcon } from "@/components/ui/graduation-cap";
import { LayersIcon } from "@/components/ui/layers";
import { LayoutGridIcon } from "@/components/ui/layout-grid";
import { MessageSquareIcon } from "@/components/ui/message-square";
import { ZapIcon } from "@/components/ui/zap";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { TopBar } from "@/components/shell/TopBar";
import { GamificationSummary } from "@/features/gamification";

// App shell for the course-scoped (LTI) surface. 56px icon side rail +
// 48px top bar, per the mockups ("App Side Rail", "App Top Bar"):
// hairline slate borders, white chrome, orange active accent.
// The shell is the instrument frame; pages render inside it.

// Animated lucide icons (lucide-animated): hover-triggered by default, so
// the rail icons draw on hover and on route activation — motion tied to the
// cursor and the active state, never looping.
type NavIcon = ComponentType<{ size?: number; className?: string }>;

const NAV: { to: string; label: string; icon: NavIcon; end?: boolean }[] = [
  { to: "/course", label: "Workspace", icon: LayoutGridIcon, end: true },
  { to: "/course/diagnostic", label: "Diagnostic", icon: FileTextIcon },
  { to: "/course/lessons", label: "Lessons", icon: GraduationCapIcon },
  { to: "/course/practice", label: "Practice", icon: ZapIcon },
  { to: "/course/flashcards", label: "Flashcards", icon: LayersIcon },
  { to: "/course/tutor", label: "Tutor", icon: MessageSquareIcon },
  { to: "/course/twin", label: "Twin", icon: ActivityIcon },
];

const SECTION_LABELS: Record<string, string> = {
  "/course": "Workspace",
  "/course/diagnostic": "Diagnostic",
  "/course/lessons": "Lessons",
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
            src="/Kala-Logo.png"
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
                  <Icon size={18} />
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
        <TopBar
          courseId={courseId}
          section={section}
          right={
            <div className="flex items-center gap-4">
              <GamificationSummary courseId={courseId} />
              <span className="font-mono text-xs text-muted-foreground">
                {initials(displayName) || section}
              </span>
            </div>
          }
        />

        <main className="mx-auto max-w-screen-2xl px-6 py-8 pb-24 lg:px-10">{children}</main>
      </div>
    </div>
  );
}
