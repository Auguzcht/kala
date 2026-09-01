import { TourRunner } from "@/components/shell/TourRunner";
import {
  INSTRUCTOR_TOUR_STEPS,
  instructorTourDismissKey,
} from "@/components/shell/instructor-tour";

// Instructor-side tour, mirroring the student side: same shared runner,
// instructor config + dismissal key in instructor-tour.ts. InstructorShell
// mounts this once; the runner survives route changes because the shell
// stays mounted around the /class routes (overview AND the learner record).

export function InstructorTourRunner() {
  return <TourRunner steps={INSTRUCTOR_TOUR_STEPS} dismissKey={instructorTourDismissKey} />;
}
