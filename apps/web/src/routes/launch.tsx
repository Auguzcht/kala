import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { captureLaunchToken } from "@/lib/auth/session";

export const Route = createFileRoute("/launch")({
  component: LaunchLanding,
});

function LaunchLanding() {
  const navigate = useNavigate();
  const [error, setError] = useState(false);

  useEffect(() => {
    const session = captureLaunchToken();
    if (!session) {
      setError(true);
      return;
    }
    // TODO: once features/instructor and features/twin exist, route by role
    // instead of always going home.
    navigate({ to: "/" });
  }, [navigate]);

  if (error) {
    return (
      <div className="mx-auto max-w-md px-6 py-16 text-center">
        <p className="text-muted-foreground">
          No valid session token found in this launch. Open Kala from inside your
          course instead of visiting this page directly.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md px-6 py-16 text-center">
      <p className="text-muted-foreground">Signing you in...</p>
    </div>
  );
}
