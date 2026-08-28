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
        description="One question per topic, at your own pace. This builds your starting point — you'll see it improve as you practice."
      />
      <DiagnosticPanel courseId={courseId} />
    </>
  );
}
