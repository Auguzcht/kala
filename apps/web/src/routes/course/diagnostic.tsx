import { createFileRoute } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { DiagnosticPanel } from "@/features/diagnostic";

export const Route = createFileRoute("/course/diagnostic")({
  component: DiagnosticPage,
});

function DiagnosticPage() {
  const courseId = useSession()?.courseId ?? "";
  return (
    <>
      <PageHeader
        eyebrow="Diagnostic"
        title="Build your baseline"
        description="One RAG-grounded question per skill, self-paced. Graded server-side — your answers set the starting estimate for your twin."
      />
      <DiagnosticPanel courseId={courseId} />
    </>
  );
}
