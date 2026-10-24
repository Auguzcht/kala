import { createRootRoute, Link, Outlet, type ErrorComponentProps } from "@tanstack/react-router";
import { useEffect } from "react";
import { RootLayout } from "@/app/layout/RootLayout";
import { SystemState } from "@/components/shared/SystemState";
import { Button } from "@/components/ui/button";
import { useSession } from "@/lib/auth/AuthProvider";

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

  return <RouteRecovery title="We couldn't open this page" body="Something went wrong. Return to your workspace and try again." />;
}

function NotFound() {
  return <RouteRecovery title="We couldn't find that page" body="The page you're looking for doesn't exist or may have moved. Check the link, or head back to your workspace." />;
}

function RouteRecovery({ title, body }: { title: string; body: string }) {
  const session = useSession();
  const destination = session?.role === "student" ? "/course" : "/class";
  return (
    <div className="grid min-h-dvh place-items-center bg-background">
      <SystemState
        icon={<span className="size-4 rounded-full" style={{ background: "var(--brand-slate)" }} />}
        iconClass="bg-brand-slate/10"
        title={title}
        body={session ? body : "Your session ended. Go back to your Blackboard course and open Kala again."}
        cta={session ? (
          <Button variant="orange" asChild>
            <Link to={destination}>Back to workspace</Link>
          </Button>
        ) : undefined}
      />
    </div>
  );
}
