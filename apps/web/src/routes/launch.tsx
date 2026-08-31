import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { motion, useAnimate, useReducedMotion } from "motion/react";
import { useQueryClient } from "@tanstack/react-query";
import { useSetSession } from "@/lib/auth/AuthProvider";
import { captureLaunchToken, loadStoredSession } from "@/lib/auth/session";
import { fetchCourse } from "@/features/courses/api/courses.api";
import { fetchNextUp, fetchTwin } from "@/features/twin/api/twin.api";
import { SystemState } from "@/components/shared/SystemState";
import { Button } from "@/components/ui/button";

// Transient landing after an LTI launch (mockup "Launch"): branded
// signing-in screen, then role routing. No login screen on this door —
// the backend already validated the launch and minted the session.
//
// Two beats, deliberately different:
//   First-ever launch (per-user `kala.seen.<userId>` flag): a slower, staged
//   beat — the signature line draws on (1.3s, slow-fast-slow), the hornbill
//   and staged copy ("Setting up your course" → "Building your baseline" →
//   "Almost there") fade in offset against it, and once drawn the line/glow
//   settles into a continuous idle pump that reads "alive" while the
//   course/twin/next-up queries prefetch behind it. A hard 2400ms cap
//   force-navigates on its own schedule regardless of sequence or prefetch
//   state — a slow model call just means /course shows its normal skeletons,
//   not a stuck screen.
//   The prefetch is Promise.race'd against the cap so navigation never
//   blocks on it.
//   Returning user / hard refresh: a short beat — the line draws quickly,
//   no pump, no staged copy. Must not feel redundant on every refresh.
//
// prefers-reduced-motion: line renders fully drawn immediately, no pump, no
// staged reveal, straight to the short beat.

export const Route = createFileRoute("/launch")({
  component: LaunchLanding,
});

// Hand-authored course-through-learning path (Figma "Animated Moving Line"
// starting point, refined in the svg-path-editor). viewBox 1200x800 with
// xMidYMid slice keeps it legible at any viewport without touching the path.
const LINE_PATH =
  "M 60 620 C 60 520, 140 460, 240 460 C 380 460, 400 580, 300 610 C 220 634, 160 580, 190 500 C 230 400, 360 340, 480 380 C 560 408, 580 480, 660 460 C 760 436, 800 340, 900 320 C 980 305, 1050 260, 1120 180";

// Pronounced slow-fast-slow for the draw-on, not linear.
const EASE_DRAW: [number, number, number, number] = [0.83, 0, 0.17, 1];

const FIRST_TIME_MS = 2400; // hard cap on the first-launch beat (finite
                              // sequence settles ~1.95s; leaves ~0.45s for
                              // the idle pump to read before redirecting)
const RETURNING_MS = 700; // short beat for everyone else
const MAX_WAIT_MS = 2400; // prefetch races this; navigation never waits on it

const STAGED_COPY = [
  "Setting up your course",
  "Building your baseline",
  "Almost there",
];

function seenKey(userId: string) {
  return `kala.seen.${userId}`;
}

function LaunchLanding() {
  const navigate = useNavigate();
  const setSession = useSetSession();
  const queryClient = useQueryClient();
  const [scope, animate] = useAnimate();
  const reduceMotion = useReducedMotion();

  // Boot synchronously: captureLaunchToken and loadStoredSession are both
  // synchronous and idempotent (the token is stored once, the fragment
  // scrubbed once — repeated calls are no-ops), so resolving the session
  // here gives the first paint correct initial states instead of a flash
  // frame. StrictMode's double initializer invoke is harmless for the same
  // reason.
  const [boot] = useState(() => {
    const session = captureLaunchToken() ?? loadStoredSession();
    return {
      session,
      firstTime: session ? !localStorage.getItem(seenKey(session.userId)) : false,
    };
  });
  const [error, setError] = useState(false);

  const { session, firstTime } = boot;
  // The full staged sequence is a first-launch, student-only, motion-allowed
  // path: courseId only exists for students (instructors/admins route to
  // /class and get nothing to prefetch), and reduced motion collapses the
  // whole beat to the short path.
  const fullSequence = firstTime && session?.role === "student" && !!session.courseId && !reduceMotion;

  // StrictMode double-invokes effects in dev. Split responsibilities:
  //   Effect 1 (prefetch) is the one genuinely-once piece — duplicate
  //   network traffic for identical cache keys — so it keeps the ref guard.
  //   Effect 2 (session push, navigation timer, animation) is StrictMode-
  //   safe by the cleanup-cancel-restart pattern instead: invocation 1's
  //   cleanup stops its animation and clears its timer, invocation 2
  //   restarts both and survives. Only the second timer ever fires, so the
  //   seen-flag write and navigate() run exactly once. (The previous
  //   single-effect version put everything behind the guard — invocation 1
  //   started the animation, StrictMode's cleanup killed it at frame 0, and
  //   invocation 2 was blocked from restarting it: blank screen, no
  //   redirect, prefetch completing in the background.)
  const hasRunRef = useRef(false);

  useEffect(() => {
    // Exact query keys the real hooks read (useCourse / useTwin / useNextUp
    // — features/courses/hooks/use-course.ts, features/twin/hooks/use-twin.ts).
    // Mismatched keys would write to a cache entry nothing reads: wasted
    // network traffic for nothing. Never blocks navigation — raced against
    // the cap; a slow prefetch just means /course shows its usual skeletons.
    if (!fullSequence) return;
    if (hasRunRef.current) return;
    hasRunRef.current = true;
    const courseId = session?.courseId;
    if (!courseId) return;
    void Promise.race([
      Promise.all([
        queryClient.prefetchQuery({
          queryKey: ["course", courseId],
          queryFn: () => fetchCourse(courseId),
        }),
        queryClient.prefetchQuery({
          queryKey: ["twin", courseId],
          queryFn: () => fetchTwin(courseId),
          staleTime: 30_000,
        }),
        queryClient.prefetchQuery({
          queryKey: ["next-up", courseId],
          queryFn: () => fetchNextUp(courseId),
          staleTime: 30_000,
        }),
      ]),
      new Promise((resolve) => setTimeout(resolve, MAX_WAIT_MS)),
    ]);
  }, [fullSequence, queryClient, session?.courseId]);

  useEffect(() => {
    // useReducedMotion can be null on first render before the media query
    // resolves; wait for a real value before starting any animation.
    if (reduceMotion === null) return;

    if (!session) {
      setError(true);
      return;
    }
    setSession(session);

    const go = () => {
      // Mark the first launch done HERE, immediately before navigating —
      // never at the top of the effect — so a slow or interrupted first
      // run can't mark itself "seen" without having actually shown the
      // sequence. Also means a refresh mid-beat doesn't replay it.
      if (firstTime) localStorage.setItem(seenKey(session.userId), "1");
      navigate({ to: session.role === "student" ? "/course" : "/class" });
    };

    // Hard cap: force-navigate on its own schedule, set BEFORE any animation
    // work so nothing the sequence does can delay it. Navigation never
    // chains off the sequence or the prefetch — if the sequence hangs for
    // any reason, this still fires.
    const maxTimer = setTimeout(go, fullSequence ? FIRST_TIME_MS : RETURNING_MS);

    let stopped = false;
    let controls: ReturnType<typeof animate> | null = null;
    let pump: ReturnType<typeof animate> | null = null;
    let pumpGlow: ReturnType<typeof animate> | null = null;

    if (fullSequence) {
      // Finite sequence ONLY — line draw, mark, staged copy. No repeat
      // anywhere in this array: a sequence containing an infinite-repeating
      // segment never resolves (motion warns it is invalid), which would
      // hang anything awaiting it. The idle pump is a separate call that
      // fires once this settles.
      controls = animate([
        ["#launch-line-main", { pathLength: 1 }, { duration: 1.3, ease: EASE_DRAW }],
        ["#launch-line-glow", { pathLength: 1 }, { duration: 1.3, ease: EASE_DRAW, at: "<" }],
        ["#launch-mark", { opacity: 1 }, { duration: 0.5, ease: "easeOut", at: 0.15 }],
        ["#launch-copy-1", { opacity: 1 }, { duration: 0.35, ease: "easeOut", at: 0.5 }],
        ["#launch-copy-1", { opacity: 0 }, { duration: 0.3, ease: "easeIn", at: 1.05 }],
        ["#launch-copy-2", { opacity: 1 }, { duration: 0.35, ease: "easeOut", at: 1.1 }],
        ["#launch-copy-2", { opacity: 0 }, { duration: 0.3, ease: "easeIn", at: 1.55 }],
        ["#launch-copy-3", { opacity: 1 }, { duration: 0.35, ease: "easeOut", at: 1.6 }],
      ]);
      void controls.then(
        () => {
          // Finite sequence settled — start the idle pump as its own
          // non-awaited calls; repeat Infinity lives ONLY here, on the
          // pump/glow elements. Nothing downstream awaits these.
          if (stopped) return;
          pump = animate(
            "#launch-line-group",
            { scale: [1, 1.03, 1] },
            { duration: 1.6, ease: "easeInOut", repeat: Infinity, repeatType: "mirror" }
          );
          pumpGlow = animate(
            "#launch-line-glow",
            { opacity: [0.5, 1, 0.5] },
            { duration: 1.6, ease: "easeInOut", repeat: Infinity, repeatType: "mirror" }
          );
        },
        () => {
          // Sequence rejected (shouldn't happen): pump stays off, the cap
          // timer still navigates on its own.
        }
      );
    } else {
      // Short beat: quick draw (instant under reduced motion), no pump, no
      // staged copy — the "Signing you in…" copy is already visible.
      const drawDuration = reduceMotion ? 0 : 0.45;
      controls = animate([
        ["#launch-line-main", { pathLength: 1 }, { duration: drawDuration, ease: EASE_DRAW }],
        ["#launch-line-glow", { pathLength: 1 }, { duration: drawDuration, ease: EASE_DRAW, at: "<" }],
      ]);
    }

    return () => {
      stopped = true;
      clearTimeout(maxTimer);
      controls?.stop();
      pump?.stop();
      pumpGlow?.stop();
    };
  }, [session, firstTime, fullSequence, navigate, setSession, animate, reduceMotion]);

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

  // Draw-on via motion's native pathLength support (it manages the dash
  // itself); reduced motion renders it fully drawn from the first paint.
  return (
    <div
      ref={scope}
      className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden bg-background"
    >
      {/* Drawn line + glow, scaled to cover the viewport */}
      <svg
        viewBox="0 0 1200 800"
        preserveAspectRatio="xMidYMid slice"
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 h-full w-full"
      >
        <defs>
          <linearGradient id="launch-line-grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="var(--brand-slate)" />
            <stop offset="55%" stopColor="var(--brand-orange)" />
            <stop offset="100%" stopColor="var(--brand-gold)" />
          </linearGradient>
        </defs>
        <g
          id="launch-line-group"
          style={{ transformBox: "fill-box", transformOrigin: "center" }}
        >
          {/* Glow: blur(6px), lower-opacity copy underneath the main line.
              Draw-on via motion's native pathLength support (it manages the
              dash itself); reduced motion renders fully drawn from first
              paint. */}
          <motion.path
            id="launch-line-glow"
            d={LINE_PATH}
            fill="none"
            stroke="var(--brand-orange)"
            strokeWidth={10}
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: reduceMotion ? 1 : 0 }}
            style={{ filter: "blur(6px)", opacity: 0.5 }}
          />
          <motion.path
            id="launch-line-main"
            d={LINE_PATH}
            fill="none"
            stroke="url(#launch-line-grad)"
            strokeWidth={5}
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: reduceMotion ? 1 : 0 }}
          />
        </g>
      </svg>

      {/* Brand + copy */}
      <div className="relative z-10 flex flex-col items-center px-6 text-center">
        <img
          id="launch-mark"
          src="/Kala-Logo.png"
          alt="Kala"
          className="mb-6 size-16 rounded-xl object-contain"
          style={{ opacity: fullSequence ? 0 : 1 }}
        />
        {fullSequence ? (
          <div className="relative h-6 w-80" aria-live="polite">
            {STAGED_COPY.map((line, i) => (
              <span
                key={line}
                id={`launch-copy-${i + 1}`}
                className="absolute inset-0 text-[15px] font-medium text-muted-foreground"
                style={{ opacity: 0 }}
              >
                {line}
              </span>
            ))}
          </div>
        ) : (
          <div>
            <div className="font-display text-[17px] font-semibold text-foreground">
              Signing you in…
            </div>
            <div className="mt-1.5 text-[13px] text-muted-foreground">
              Validating your launch from your course
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
