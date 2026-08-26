import { createFileRoute, Link } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { StudentDrillDown } from "@/features/instructor";

export const Route = createFileRoute("/class/student/$uid")({
  component: StudentDrillDownPage,
});

function StudentDrillDownPage() {
  const { uid } = Route.useParams();
  const courseId = useSession()?.courseId ?? "";

  return (
    <>
      <Link
        to="/class"
        className="mb-5 inline-block text-xs font-semibold text-brand-orange hover:underline"
      >
        ← Back to class dashboard
      </Link>
      <StudentDrillDown courseId={courseId} userId={uid} />
    </>
  );
}
