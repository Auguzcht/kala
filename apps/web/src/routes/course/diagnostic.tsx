import { createFileRoute } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { DiagnosticPanel } from "@/features/diagnostic";

export const Route = createFileRoute("/course/diagnostic")({
  component: DiagnosticPage,
});

function DiagnosticPage() {
  const courseId = useSession()?.courseId ?? "";
  return <DiagnosticPanel courseId={courseId} />;
}
