import { createFileRoute } from "@tanstack/react-router";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { TwinView } from "@/features/twin";

export const Route = createFileRoute("/course/twin")({
  component: TwinPage,
});

function TwinPage() {
  const courseId = useSession()?.courseId ?? "";
  return (
    <>
      <PageHeader
        eyebrow="Twin"
        title="Your twin"
        description="A live model of your mastery across this course, built from every diagnostic answer, practice attempt, review, and question you've made."
      />
      <TwinView courseId={courseId} />
    </>
  );
}
