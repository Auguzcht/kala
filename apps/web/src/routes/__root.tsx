import { createRootRoute, Link, Outlet, type ErrorComponentProps } from "@tanstack/react-router";
import { useEffect } from "react";
import { RootLayout } from "@/app/layout/RootLayout";
import { SystemState } from "@/components/shared/SystemState";
import { Button } from "@/components/ui/button";

export const Route = createRootRoute({
  component: () => (
    <RootLayout>
      <Outlet />
    </RootLayout>
  ),
  notFoundComponent: NotFound,
  errorComponent: RootError,
});

function RootError({ error }: ErrorComponentProps) {
  useEffect(() => {
    if (import.meta.env.DEV) console.error("Route error", error);
  }, [error]);

  return (
    <div className="grid min-h-dvh place-items-center bg-background">
      <SystemState
        icon={<span className="size-4 rounded-full" style={{ background: "var(--brand-slate)" }} />}
        iconClass="bg-brand-slate/10"
        title="We couldn't open this page"
        body="Something went wrong. Return to your workspace and try again."
        cta={
          <Button variant="orange" asChild>
            <Link to="/course">Back to workspace</Link>
          </Button>
        }
      />
    </div>
  );
}

function NotFound() {
  return (
    <div className="grid min-h-dvh place-items-center bg-background">
      <SystemState
        icon={<span className="size-4 rounded-full" style={{ background: "var(--brand-slate)" }} />}
        iconClass="bg-brand-slate/10"
        title="We couldn't find that page"
        body="The page you're looking for doesn't exist or may have moved. Check the link, or head back to your workspace."
        cta={
          <Button variant="orange" asChild>
            <Link to="/course">Back to workspace</Link>
          </Button>
        }
      />
    </div>
  );
}
