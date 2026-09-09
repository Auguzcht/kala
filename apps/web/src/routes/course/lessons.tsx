import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useSession } from "@/lib/auth/AuthProvider";
import { PageHeader } from "@/components/shell/PageHeader";
import { LessonChat } from "@/features/lessons";
import { TopicLanding } from "@/components/study/TopicLanding";
import { useTwin } from "@/features/twin";
import { Button } from "@/components/ui/button";
import { ChevronLeftIcon } from "@/components/ui/chevron-left";

export const Route = createFileRoute("/course/lessons")({
  component: LessonsPage,
});

function LessonsPage() {
  const courseId = useSession()?.courseId ?? "";
  const { data: twin, isLoading } = useTwin(courseId);
  const [skillId, setSkillId] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        eyebrow="Guided lessons"
        title="Work through it, step by step"
        description="Kala walks you through one skill at a time — explain, check, advance. Lessons are written once and replayed, so every pass is consistent."
      />
      {skillId ? (
        <div className="space-y-4">
          <Button variant="outline" size="sm" onClick={() => setSkillId(null)}>
            <ChevronLeftIcon size={14} /> Choose another topic
          </Button>
          <LessonChat courseId={courseId} skillId={skillId} />
        </div>
      ) : (
        <TopicLanding
          isLoading={isLoading}
          skills={twin?.skills ?? []}
          onChoose={setSkillId}
          caption="guided walkthrough with checks"
          gridId="tour-lessons-picker"
          firstCardId="tour-lessons-first-card"
        />
      )}
    </>
  );
}
