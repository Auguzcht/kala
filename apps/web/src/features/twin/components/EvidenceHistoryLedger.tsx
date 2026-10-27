import { useQueryClient } from "@tanstack/react-query";
import { EvidenceLedger } from "@/components/kala/evidence-ledger";
import { Button } from "@/components/ui/button";
import { useEvidenceHistory } from "@/features/twin/hooks/use-evidence-history";
import type { EvidenceEvent } from "@/features/twin/schema/twin.schema";

/** Independent history feed; bounded charts and statistics keep their original data. */
export function EvidenceHistoryLedger({ courseId, targetId, fallbackEvents, fallbackLabel }: {
  courseId: string;
  targetId?: string;
  fallbackEvents: EvidenceEvent[];
  fallbackLabel: string;
}) {
  const history = useEvidenceHistory(courseId, targetId);
  const queryClient = useQueryClient();
  const active = history.allowed && !!history.data;
  const invalidCursor = history.error?.message.startsWith("API 422:") ?? false;
  const unavailable = !history.allowed || /^API (403|404):/.test(history.error?.message ?? "");
  const failedStaff = !!targetId && history.isError;
  function reload() {
    // Drop the whole chain so a rotated cursor cannot remain in a subsequent page.
    void queryClient.resetQueries({ queryKey: JSON.parse(history.scopeKey), exact: true });
  }
  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground" role="status">
        {unavailable ? "Activity unavailable" : failedStaff ? "Activity could not be loaded" : active ? `Showing ${history.events.length} of ${targetId ? "this learner's" : "your"} activity` : fallbackLabel}
      </p>
      {unavailable ? (
        <p role="alert" className="text-sm text-muted-foreground">Activity is unavailable for this course or learner.</p>
      ) : failedStaff ? null : (
        <EvidenceLedger key={history.scopeKey} events={active ? history.events : fallbackEvents}
          totalLabel={active ? "loaded events" : undefined}
          hasMore={active && history.hasNextPage && !invalidCursor}
          loadingMore={history.isFetching}
          onLoadMore={async () => {
            const result = await history.fetchNextPage();
            if (result.isError) throw result.error;
            return new Set(result.data?.pages.flatMap((page) => page.evidence.map((event) => event.id))).size;
          }} />
      )}
      {history.isError && !unavailable ? (
        <div className="flex flex-wrap items-center gap-2" role="alert">
          <p className="text-xs text-muted-foreground">
            {invalidCursor ? (targetId ? "Activity needs to be reloaded." : "Activity needs to be reloaded. Loaded rows remain visible.") : (targetId ? "Couldn't load the learner, try again" : "We could not load activity. Try again.")}
          </p>
          <Button variant="outline" disabled={history.isFetching} onClick={() => {
            if (invalidCursor) reload();
            else if (active && history.hasNextPage) void history.fetchNextPage();
            else void history.refetch();
          }}>{invalidCursor ? "Reload activity" : "Retry activity"}</Button>
        </div>
      ) : null}
    </div>
  );
}
