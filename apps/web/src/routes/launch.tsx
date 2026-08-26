import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { captureLaunchToken } from "@/lib/auth/session";
import { SystemState } from "@/components/shared/SystemState";
import { Button } from "@/components/ui/button";

// Transient landing after an LTI launch (mockup "Launch"): branded
// signing-in screen, then role routing. No login screen on this door —
// the backend already validated the launch and minted the session.

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
    // Brief branded pause so the "validating your launch" state is legible
    // (it doubles as the conference demo's opening beat).
    const t = setTimeout(() => {
      // Role routing: students to the learn loop, instructors/admins to the
      // class dashboard (Phase 4). Standalone admin/researcher doors come
      // later.
      navigate({ to: session.role === "student" ? "/course" : "/class" });
    }, 700);
    return () => clearTimeout(t);
  }, [navigate]);

  if (error) {
    return (
      <div className="grid min-h-dvh place-items-center bg-background">
        <SystemState
          icon={
            <span className="size-4 rounded-[2px]" style={{ background: "var(--brand-red)" }} />
          }
          iconClass="bg-brand-red/10"
          title="Open Kala from inside your course"
          body="This link only works from a Blackboard or Canvas launch. Open Kala from your course to sign in."
          cta={
            <Button
              variant="orange"
              onClick={() => {
                if (window.history.length > 1) window.history.back();
                else navigate({ to: "/" });
              }}
            >
              Return to course
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-background text-center">
      <img
        src="/assets/kala-mark.png"
        alt="Kala"
        className="mb-6 size-16 rounded-xl object-contain"
      />
      <svg width="26" height="26" viewBox="0 0 26 26" className="mb-5 animate-spin">
        <circle cx="13" cy="13" r="10" fill="none" stroke="rgba(31,47,77,0.14)" strokeWidth="3" />
        <circle
          cx="13"
          cy="13"
          r="10"
          fill="none"
          stroke="#FF8A00"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray="24 100"
        />
      </svg>
      <div className="font-display text-[17px] font-semibold text-foreground">Signing you in…</div>
      <div className="mt-1.5 text-[13px] text-muted-foreground">
        Validating your launch from your course
      </div>
      <div className="mt-5 font-mono text-[11.5px] text-muted-foreground/70">
        Detecting your role · routing to your view
      </div>
    </div>
  );
}
