import { createRootRoute, Link, Outlet } from "@tanstack/react-router";
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
});

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
