import { createFileRoute, Navigate, Outlet } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { EmptyState } from "@/components/shared/EmptyState";
import { CourseShell } from "@/components/shell/CourseShell";

// /course is a layout: the app shell (side rail + top bar) wraps every
// learn-loop page. Guards session + course scope before rendering.
export const Route = createFileRoute("/course")({
  component: CourseLayout,
});

function CourseLayout() {
  const session = useSession();

  if (!session) {
    // No minted session: back to the launch flow, which explains the
    // "open Kala from inside your course" state.
    return <Navigate to="/launch" />;
  }
  if (!session.courseId) {
    // Authenticated but not course-scoped (e.g. a standalone admin visiting
    // a course URL). Their surface lives elsewhere (Phase 4+).
    return (
      <div className="mx-auto max-w-2xl px-6 py-16">
        <EmptyState
          title="No course in this session"
          description="Open Kala from inside a course in your LMS to use the learn loop."
        />
      </div>
    );
  }

  return (
    <CourseShell courseId={session.courseId} displayName={session.displayName}>
      <Outlet />
    </CourseShell>
  );
}
