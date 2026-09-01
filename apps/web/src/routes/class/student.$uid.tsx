import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, useReducedMotion } from "motion/react";
import { useSession } from "@/lib/auth/AuthProvider";
import { LearnerRecord } from "@/features/instructor";
import { ChevronLeftIcon } from "@/components/ui/chevron-left";

export const Route = createFileRoute("/class/student/$uid")({
  component: LearnerRecordPage,
});

// Full-width, bookmarkable read of one learner. Deliberately NOT the
// roster sheet: the sheet is triage (standing + decide, LearnerTriage);
// this page is the deep dive — the mastery instruments and activity
// history that need width. The two containers share LearnerStanding, so
// the header can never drift between them.
//
// The entrance is a short rise-and-fade so the drill-down reads as
// intentional rather than a hard swap; reduced motion skips it entirely.

function LearnerRecordPage() {
  const { uid } = Route.useParams();
  const courseId = useSession()?.courseId ?? "";
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
    >
      <Link
        to="/class"
        className="mb-5 inline-flex items-center gap-1 text-xs font-semibold text-brand-orange hover:underline"
      >
        <ChevronLeftIcon size={14} /> Back to class overview
      </Link>
      <LearnerRecord courseId={courseId} userId={uid} />
    </motion.div>
  );
}
