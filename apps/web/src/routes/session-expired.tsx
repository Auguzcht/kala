import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { SystemState } from "@/components/shared/SystemState";
import { Button } from "@/components/ui/button";

// Sessions time out after a period of inactivity (sitemap:
// /session-expired). Re-launch from the LMS to mint a fresh one.
export const Route = createFileRoute("/session-expired")({
  component: SessionExpired,
});

function SessionExpired() {
  const navigate = useNavigate();
  return (
    <div className="grid min-h-dvh place-items-center bg-background">
      <SystemState
        icon={<span className="size-4 rounded-[2px]" style={{ background: "var(--brand-slate)" }} />}
        iconClass="bg-brand-slate/10"
        title="Your session has expired"
        body="For your security, sessions time out after a period of inactivity. Re-launch from your course, or sign in again if you use a standalone account."
        cta={
          <Button variant="orange" onClick={() => navigate({ to: "/launch" })}>
            Re-launch
          </Button>
        }
      />
    </div>
  );
}
