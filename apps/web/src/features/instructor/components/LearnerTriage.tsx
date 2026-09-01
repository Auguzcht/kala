import { useState } from "react";
import { useAtRisk, useLearnerRecord } from "@/features/instructor";
import { DecisionCenter } from "@/features/instructor/components/DecisionCenter";
import { LearnerStanding } from "@/features/instructor/components/LearnerStanding";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/EmptyState";

// The triage surface — what the roster sheet shows, deliberately NOT the
// full LearnerRecord.
//
// The teacher's task when they click a roster row is: "who is this, where
// do they stand, and what do I decide for them right now" — then move on
// to the next row. A right-hand sheet is the right container for that
// because the roster stays underneath, so the sheet shows exactly the
// triage material: the standing block (identity, flag reason, the four
// comparison numbers) and the decision gate. Nothing else.
//
// The full record (LearnerRecord) answers a different task — "what is this
// learner's full picture" — and it keeps the mastery instruments and the
// activity history that need width. The sheet links out to it for the
// deep read; it does not try to be a shrunken version of it.

export function LearnerTriage({
  courseId,
  userId,
}: {
  courseId: string;
  userId: string;
}) {
  const record = useLearnerRecord(courseId, userId);
  const atRisk = useAtRisk(courseId);
  const [deidentified, setDeidentified] = useState(false);

  if (record.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-56 w-full" />
      </div>
    );
  }

  if (record.isError || !record.data) {
    return (
      <EmptyState
        title="We could not load this learner's record"
        description="Check your connection and try again."
        action={
          <Button variant="outline" onClick={() => record.refetch()}>
            Retry
          </Button>
        }
      />
    );
  }

  const r = record.data;
  const name = deidentified ? r.pseudonym : r.displayName;
  const flag = atRisk.data?.flags.find((f) => f.userId === userId);

  return (
    <div className="space-y-5">
      <LearnerStanding
        userId={userId}
        record={r}
        flag={flag}
        deidentified={deidentified}
        onDeidentifiedChange={setDeidentified}
      />
      {/* The one thing a teacher does in triage: decide. */}
      <DecisionCenter courseId={courseId} userId={userId} learnerName={name} />
    </div>
  );
}
