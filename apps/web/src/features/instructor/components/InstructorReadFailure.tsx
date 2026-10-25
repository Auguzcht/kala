import { Link } from "@tanstack/react-router";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";

/** INSTR-REQ-011: classify only the shared client's status prefix; never show its body. */
function isUnavailableRead(error: unknown): boolean {
  return error instanceof Error && /^API (403|404):/.test(error.message);
}

export function InstructorReadFailure({ error, retry, learner = false }: {
  error: unknown;
  retry: () => unknown;
  learner?: boolean;
}) {
  const unavailable = isUnavailableRead(error);
  return (
    <div role="alert" className="w-full min-w-0">
      <EmptyState
        title={unavailable ? learner ? "Learner unavailable" : "This class isn't available to you"
          : learner ? "Couldn't load the learner, try again" : "Couldn't load the class, try again"}
        description={unavailable
          ? learner ? "This learner or course is unavailable. Return to your class to choose an available learner."
            : "Open an available class from your LMS."
          : "Check your connection and try again."}
        action={unavailable ? learner ? (
          <Button variant="outline" asChild><Link to="/class">Back to class</Link></Button>
        ) : undefined : <Button variant="outline" onClick={() => { void retry(); }}>Retry</Button>}
      />
    </div>
  );
}
