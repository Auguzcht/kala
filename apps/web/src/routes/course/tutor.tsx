import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { useSession } from "@/lib/auth/AuthProvider";
import { TutorChat } from "@/features/tutor";

// The active conversation lives in the URL now, not TutorChat's local
// state. TutorSidebar (rendered by CourseShell, a sibling of this route's
// component, not a parent/child of it) needs to read and set it too, and a
// search param is the one thing both can agree on without inventing new
// shared state. Same pattern as practice.tsx's bridge search params.
const tutorSearchSchema = z.object({
  conversation: z.string().optional(),
});

export const Route = createFileRoute("/course/tutor")({
  validateSearch: tutorSearchSchema,
  component: TutorPage,
});

function TutorPage() {
  const courseId = useSession()?.courseId ?? "";
  // PageHeader is gone per docs/ai-overhaul-v2/05_TUTOR_AND_HIERARCHY.md —
  // Tutor is a session now, its title lives in SessionBar, not a page
  // eyebrow.
  return <TutorChat courseId={courseId} />;
}
