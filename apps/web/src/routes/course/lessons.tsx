import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { LessonChat } from "@/features/lessons";
import { TopicLanding } from "@/components/study/TopicLanding";
import { useTwin } from "@/features/twin";

export const Route = createFileRoute("/course/lessons")({
  component: LessonsPage,
});

function LessonsPage() {
  const courseId = useSession()?.courseId ?? "";
  const { data: twin, isLoading } = useTwin(courseId);
  const [skillId, setSkillId] = useState<string | null>(null);

  if (skillId) {
    return (
      <LessonChat
        courseId={courseId}
        skillId={skillId}
        onExit={() => setSkillId(null)}
      />
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Lessons"
        title="Choose a topic"
      />
      <TopicLanding
        isLoading={isLoading}
        skills={twin?.skills ?? []}
        onChoose={setSkillId}
        gridId="tour-lessons-picker"
        firstCardId="tour-lessons-first-card"
      />
    </>
  );
}
