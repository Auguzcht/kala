import { createFileRoute } from "@tanstack/react-router";
import { SystemState } from "@/components/shared/SystemState";

// Sessions time out after a period of inactivity (sitemap:
// /session-expired). Re-launch from the LMS to mint a fresh one.
export const Route = createFileRoute("/session-expired")({
  component: SessionExpired,
});

function SessionExpired() {
  return (
    <div className="grid min-h-dvh place-items-center bg-background">
      <SystemState
        icon={<span className="size-4 rounded-[2px]" style={{ background: "var(--brand-slate)" }} />}
        iconClass="bg-brand-slate/10"
        title="Your session has expired"
        body="Your session ended. Go back to your Blackboard course and open Kala again."
      />
    </div>
  );
}
