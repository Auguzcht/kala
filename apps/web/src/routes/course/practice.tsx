import { createFileRoute } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { PracticePanel } from "@/features/practice";

export const Route = createFileRoute("/course/practice")({
  component: PracticePage,
});

function PracticePage() {
  const courseId = useSession()?.courseId ?? "";
  return (
    <>
      <PageHeader
        eyebrow="Practice"
        title="Quick practice"
        description="One item at a time, targeted at your weakest skill. Answer and the loop advances automatically."
      />
      <PracticePanel courseId={courseId} />
    </>
  );
}
