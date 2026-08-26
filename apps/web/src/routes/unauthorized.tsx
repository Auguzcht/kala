import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { SystemState } from "@/components/shared/SystemState";
import { Button } from "@/components/ui/button";

// Wrong role for this route (sitemap: /unauthorized). Instructor/admin
// surfaces land here until Phase 4 routes them properly.
export const Route = createFileRoute("/unauthorized")({
  component: Unauthorized,
});

function Unauthorized() {
  const navigate = useNavigate();
  return (
    <div className="grid min-h-dvh place-items-center bg-background">
      <SystemState
        icon={<span className="size-4 rounded-full" style={{ background: "var(--brand-orange)" }} />}
        iconClass="bg-brand-orange/10"
        title="This view isn't available for your role"
        body="Your account role doesn't have access to this page. If you think this is a mistake, ask your course admin to check your role."
        cta={
          <Button variant="orange" onClick={() => navigate({ to: "/" })}>
            Go to my home
          </Button>
        }
      />
    </div>
  );
}
