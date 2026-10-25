import { useMemo } from "react";
import { TourRunner } from "@/components/shell/TourRunner";
import { createStudentTour, studentTourDismissKey, TOUR_STEPS } from "@/components/shell/student-tour";
import { useUI } from "@/stores/ui-store";

export function TourStepRunner() {
  const context = useUI((state) => state.tourContext);
  const steps = useMemo(() => context ? createStudentTour(context) : TOUR_STEPS, [context]);
  return <TourRunner steps={steps} dismissKey={studentTourDismissKey} />;
}
