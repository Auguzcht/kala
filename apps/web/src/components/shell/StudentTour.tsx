import { TourRunner } from "@/components/shell/TourRunner";
import { TOUR_STEPS, studentTourDismissKey } from "@/components/shell/student-tour";

// Student-side tour. The actual runner is shared (TourRunner); the student
// config and dismissal key live in student-tour.ts. CourseShell mounts this
// once and the runner survives route changes because the shell stays
// mounted around the /course routes.

export function TourStepRunner() {
  return <TourRunner steps={TOUR_STEPS} dismissKey={studentTourDismissKey} />;
}
