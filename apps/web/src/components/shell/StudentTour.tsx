import { useMemo } from "react";
import { TourRunner } from "@/components/shell/TourRunner";
import { createStudentTour, studentTourDismissKey } from "@/components/shell/student-tour";
import { useUI } from "@/stores/ui-store";

export function TourStepRunner() {
  const context = useUI((state) => state.tourContext);
  const steps = useMemo(() => context ? createStudentTour(context) : [], [context]);
  return <TourRunner steps={steps} dismissKey={studentTourDismissKey} />;
}
