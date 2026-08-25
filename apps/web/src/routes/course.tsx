import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useSession } from "@/lib/auth/AuthProvider";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/EmptyState";
import { DiagnosticPanel } from "@/features/diagnostic";
import { PracticePanel } from "@/features/practice";
import { TutorChat } from "@/features/tutor";
import { FlashcardDeck } from "@/features/flashcards";

export const Route = createFileRoute("/course")({
  component: CourseHome,
});

const TABS = [
  { id: "diagnostic", label: "Diagnostic" },
  { id: "practice", label: "Practice" },
  { id: "tutor", label: "Ask Kala" },
  { id: "flashcards", label: "Flashcards" },
] as const;

type TabId = (typeof TABS)[number]["id"];

function CourseHome() {
  const session = useSession();
  const [tab, setTab] = useState<TabId>("diagnostic");

  if (!session?.courseId) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-16">
        <EmptyState
          title="No course in this session"
          description="Open Kala from inside a course in your LMS to start the diagnostic, practice, and tutor."
        />
      </div>
    );
  }

  const courseId = session.courseId;

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-6 py-10">
      <div>
        <p className="text-sm font-medium tracking-wide text-brand-slate">Your course</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-foreground">
          The learn loop
        </h1>
        <p className="mt-2 text-muted-foreground">
          Diagnose your baseline, practice your weakest skills, ask questions, and review with
          flashcards.
        </p>
      </div>

      <nav className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <Button
            key={t.id}
            variant={tab === t.id ? "orange" : "outline"}
            size="sm"
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </Button>
        ))}
      </nav>

      {tab === "diagnostic" ? <DiagnosticPanel courseId={courseId} /> : null}
      {tab === "practice" ? <PracticePanel courseId={courseId} /> : null}
      {tab === "tutor" ? <TutorChat courseId={courseId} /> : null}
      {tab === "flashcards" ? <FlashcardDeck courseId={courseId} /> : null}
    </div>
  );
}
