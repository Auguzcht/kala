import { createFileRoute } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { TutorChat } from "@/features/tutor";

export const Route = createFileRoute("/course/tutor")({
  component: TutorPage,
});

function TutorPage() {
  const courseId = useSession()?.courseId ?? "";
  return (
    <>
      <PageHeader
        eyebrow="Tutor"
        title="Ask Kala"
        description="Grounded in your course content. Kala teaches and gives hints — it never hands back answers to graded work."
      />
      <TutorChat courseId={courseId} />
    </>
  );
}
