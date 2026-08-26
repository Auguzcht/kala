import { createFileRoute, Navigate, Outlet } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { EmptyState } from "@/components/shared/EmptyState";
import { InstructorShell } from "@/components/shell/InstructorShell";

// /class is the instructor layout: top bar + first-launch tour. Role-guarded
// (students get the wrong-role state, per the sitemap).
export const Route = createFileRoute("/class")({
  component: ClassLayout,
});

function ClassLayout() {
  const session = useSession();

  if (!session) return <Navigate to="/launch" />;
  if (session.role === "student") return <Navigate to="/unauthorized" />;
  if (!session.courseId) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-16">
        <EmptyState
          title="No course in this session"
          description="Open Kala from inside a course in your LMS to see the class dashboard."
        />
      </div>
    );
  }

  return (
    <InstructorShell courseId={session.courseId} displayName={session.displayName}>
      <Outlet />
    </InstructorShell>
  );
}
