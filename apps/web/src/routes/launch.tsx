import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { motion, useAnimate, useReducedMotion } from "motion/react";
import { useQueryClient } from "@tanstack/react-query";
import { useSetSession } from "@/lib/auth/AuthProvider";
import { captureLaunchToken, loadStoredSession } from "@/lib/auth/session";
import { fetchCourse } from "@/features/courses/api/courses.api";
import { fetchNextUp, fetchTwin } from "@/features/twin/api/twin.api";
import {
  fetchAtRisk,
  fetchAutoMatchedSkills,
  fetchHeatmap,
  fetchProposedSkills,
} from "@/features/instructor/api/instructor.api";
import { BriefLoading } from "@/components/shared/BriefLoading";
import { SystemState } from "@/components/shared/SystemState";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

// Transient landing after an LTI launch (mockup "Launch"): branded
// signing-in screen, then role routing. No login screen on this door —
// the backend already validated the launch and minted the session.
//
// Two beats, deliberately different:
//   First-ever launch (per-user `kala.seen.<userId>` flag): a staged, ~9.5s
//   beat. The line appears (2.2s, slow-fast-slow), holds briefly
//   (0.3s), then erases along its own geometry (1.5s, start-to-end via a
//   reversed-geometry retraction)
//   (1.5s) — logo, spinner, and copy stay hidden until the line is fully
//   gone. Then the hornbill + spinner fade in and the staged copy cycles
//   ("Setting up your course" → "Building your baseline" → "Almost there"),
//   holding for ~4.5s before the cap navigates — the prefetched workspace
//   makes the transition seamless. The prefetch is Promise.race'd against
//   the cap so navigation never blocks on it.
//   Returning user / hard refresh: a short beat — the line draws quickly,
//   no staged copy. Must not feel redundant on every refresh.
//
// prefers-reduced-motion: line renders fully drawn immediately, no
// staged reveal, straight to the short beat.

export const Route = createFileRoute("/launch")({
  component: LaunchLanding,
});

// The line, user-authored in the path editor (smoother, less jagged): one
// continuous stroke. Starts at (120,703), ends at (1620,120) — the path
// spans x 120..1620, y 120..912 in the source's 1740×1036 frame. The viewBox
// is windowed to 200..1500 × 100..900 so BOTH the start and the end fall
// OUTSIDE the visible frame: the line appears from beyond the left edge and
// exits beyond the right/top edge, "seemingly appearing in and out of the
// frame". xMidYMid slice maps the window to the viewport.
const LINE_PATH =
  "M120,703c48,-87 93.40663,-175.4821 144,-261c38.79264,-65.57115 70.98952,-137.2795 124,-192c32.36424,-33.40825 77.58801,-60.92053 124,-64c76.66842,-5.087 119.18837,95.17314 122,150c4.2092,82.07936 -78.05327,436.29165 66,549c37.6889,29.48808 94.4215,37.97466 141,27c81.40051,-19.1793 162.94727,-55.84711 224,-113c212.96671,-199.36311 210.53405,-343.34153 390,-546c46.83424,-52.88666 110,-88.66667 165,-133";

// The same geometry with the direction reversed — computed directly from
// LINE_PATH by swapping each segment's control points and re-expressing
// them relative to the new preceding point, VERIFIED to retrace the
// identical curve backward with no shape distortion (an earlier attempt
// that merely negated/reordered the relative deltas produced wrong control
// points — the "breaks into straight lines" artifact during the erase).
// Written in absolute coordinates (M/C) to remove any chance of a
// relative-delta transcription error. The erase runs pathLength 1→0 on
// this path: its retraction front travels from the original start
// (bottom-left) to the original end (top-right) — start-to-end, round caps
// and all.
const REVERSE_LINE_PATH =
  "M1620,120C1565,164.333 1501.834,200.113 1455,253C1275.534,455.658 1277.967,599.637 1065,799C1003.947,856.153 922.401,892.821 841,912C794.422,922.975 737.689,914.488 700,885C555.947,772.292 638.209,418.079 634,336C631.188,281.173 588.668,180.913 512,186C465.588,189.079 420.364,216.592 388,250C334.99,304.721 302.793,376.429 264,442C213.407,527.518 168,616 120,703";

// Pronounced slow-fast-slow for the draw-on, not linear.
const EASE_DRAW: [number, number, number, number] = [0.83, 0, 0.17, 1];

// Phase 1 — the line appears then erases, slow-fast-slow both ways:
// draw in (pathLength 0→1 on the normal path), brief hold, erase
// (crossfade onto the reversed-geometry path, then pathLength 1→0 — its
// retraction front travels the line start→end, round caps and all).
const DRAW_MS = 2.2;
const HOLD_MS = 0.3;
const ERASE_MS = 1.5;

// Phase 2 starts once the line is fully gone (~4s): logo/spinner/text fade
// in (~1s intro + ~3.3s staged copy), then the logo/spinner/"Almost there"
// hold until the cap navigates — line ~4s + animate-in ~1s + ~4.5s hold ≈
// 9.5s. The prefetch makes the workspace transition seamless.
// First-time navigation gate: leave at MIN (the full beat) IF the prefetch
// is done, else when the data lands, else at MAX — never hang. Returning
// students and instructors keep the fixed 700ms beat with no gating; their
// prefetch is pure upside (raced against RETURNING_MS so it can never delay
// navigation past today's behavior).
const FIRST_TIME_MS = 9500; // MIN — the full first-launch beat
const FIRST_MAX_MS = 13000; // MAX — first-time hard cap
const RETURNING_MS = 700; // short beat + prefetch race bound for the rest
const MAX_WAIT_MS = 13000; // first-time prefetch race bound
const PREFETCH_TIMEOUT_MS = 6000; // per-request abort for the prefetch calls

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
  // Set when the launch prefetch settles (resolved OR failed — a failure
  // counts as "done waiting": nothing to wait for, the workspace shows its
  // own error state). Read by the first-time navigation gate.
  const dataReadyRef = useRef(false);

  useEffect(() => {
    // Prefetch for EVERY path, once (hasRunRef). Exact query keys the real
    // hooks read (useCourse / useTwin / useNextUp — courses+hooks, twin+hooks;
    // useHeatmap / useAtRisk / useProposedSkills / useAutoMatchedSkills —
    // features/instructor/hooks/use-instructor.ts). Mismatched keys would
    // write to a cache entry nothing reads: wasted network traffic for
    // nothing. Each request carries a real abort timeout so a hung network
    // call cannot sit past its own bound — a rejected prefetch counts as
    // "done waiting" (dataReadyRef set either way).
    //   First-time students: raced against MAX_WAIT_MS; the navigation gate
    //   reads dataReadyRef (never blocks — MAX caps it).
    //   Returning students + instructors: raced against RETURNING_MS so the
    //   prefetch can never delay navigation past today's fixed beat; if it
    //   lands in time the destination loads pre-warmed, if not the user
    //   sees the same skeletons as today. Pure upside either way.
    if (hasRunRef.current) return;
    hasRunRef.current = true;
    const courseId = session?.courseId;
    if (!courseId) return;
    const raceMs = fullSequence ? MAX_WAIT_MS : RETURNING_MS;
    const queries =
      session.role === "student"
        ? [
            queryClient.prefetchQuery({
              queryKey: ["course", courseId],
              queryFn: () => fetchCourse(courseId, PREFETCH_TIMEOUT_MS),
            }),
            queryClient.prefetchQuery({
              queryKey: ["twin", courseId],
              queryFn: () => fetchTwin(courseId, PREFETCH_TIMEOUT_MS),
              staleTime: 30_000,
            }),
            queryClient.prefetchQuery({
              queryKey: ["next-up", courseId],
              queryFn: () => fetchNextUp(courseId, PREFETCH_TIMEOUT_MS),
              staleTime: 30_000,
            }),
          ]
        : [
            queryClient.prefetchQuery({
              queryKey: ["heatmap", courseId],
              queryFn: () => fetchHeatmap(courseId, PREFETCH_TIMEOUT_MS),
            }),
            queryClient.prefetchQuery({
              queryKey: ["at-risk", courseId],
              queryFn: () => fetchAtRisk(courseId, PREFETCH_TIMEOUT_MS),
            }),
            queryClient.prefetchQuery({
              queryKey: ["proposed-skills", courseId],
              queryFn: () => fetchProposedSkills(courseId, PREFETCH_TIMEOUT_MS),
            }),
            queryClient.prefetchQuery({
              queryKey: ["auto-matched-skills", courseId],
              queryFn: () => fetchAutoMatchedSkills(courseId, PREFETCH_TIMEOUT_MS),
            }),
          ];
    void Promise.race([
      Promise.all(queries),
      new Promise((resolve) => setTimeout(resolve, raceMs)),
    ]).then(
      () => {
        dataReadyRef.current = true;
      },
      () => {
        // A rejected prefetch is "done waiting" too — nothing to wait for.
        dataReadyRef.current = true;
      }
    );
  }, [fullSequence, queryClient, session, session?.courseId]);

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

    let stopped = false;
    let controls: ReturnType<typeof animate> | null = null;
    let pump: ReturnType<typeof animate> | null = null;
    let pumpGlow: ReturnType<typeof animate> | null = null;
    let phase2: ReturnType<typeof animate> | null = null;
    let phase2Timer: ReturnType<typeof setTimeout> | null = null;
    let pumpTimer: ReturnType<typeof setTimeout> | null = null;
    let pumpStopTimer: ReturnType<typeof setTimeout> | null = null;
    let maxTimer: ReturnType<typeof setTimeout> | null = null;
    let probe: ReturnType<typeof setInterval> | null = null;

    // First-time gate: leave at MIN (the full beat) if the prefetch already
    // settled, else when the data lands, else at MAX — never hang. A 250ms
    // probe between MIN and MAX re-checks readiness, so a late-arriving
    // prefetch exits the moment it's done. Returning students + instructors
    // keep the fixed RETURNING_MS beat, no gating — their prefetch raced
    // against RETURNING_MS so this never waits on it.
    if (fullSequence) {
      const start = Date.now();
      probe = setInterval(() => {
        if (stopped) return;
        if (Date.now() - start >= FIRST_TIME_MS && dataReadyRef.current) go();
      }, 250);
      maxTimer = setTimeout(go, FIRST_MAX_MS);
    } else {
      maxTimer = setTimeout(go, RETURNING_MS);
    }

    if (fullSequence) {
      // Phase 1 — draw + erase in ONE sequence so motion tracks state
      // continuously. NO repeat anywhere in this array.
      //   Draw: pathLength 0→1 on the normal paths (progressive, verified).
      //   Crossfade (hold end): normal paths fade out, reversed-geometry
      //   copies fade in — identical geometry, imperceptible swap.
      //   Erase: pathLength 1→0 on the REVERSED paths — the visible window
      //   is anchored at the reversed start (the line's END, top-right), so
      //   the retraction front travels from the line's START (bottom-left)
      //   toward its END — start-to-end, following the line's own geometry
      //   with round caps. (pathLength-only on the normal path anchors at
      //   the start and erases end-to-start — the backwards read.)
      controls = animate([
        ["#launch-line-main", { pathLength: 1 }, { duration: DRAW_MS, ease: EASE_DRAW }],
        ["#launch-line-glow", { pathLength: 1 }, { duration: DRAW_MS, ease: EASE_DRAW, at: "<" }],
        // crossfade at the hold end: fade the whole GROUP out (glow + main
        // together — the pump owns the glow's opacity, so an individual glow
        // fade never applies), reverse copies fade in
        [
          "#launch-line-group",
          { opacity: 0 },
          { duration: 0.2, ease: "easeOut", at: DRAW_MS + HOLD_MS - 0.2 },
        ],
        [
          "#launch-line-reverse",
          { opacity: 1 },
          { duration: 0.2, ease: "easeIn", at: DRAW_MS + HOLD_MS - 0.2 },
        ],
        [
          "#launch-line-glow-reverse",
          { opacity: 1 },
          { duration: 0.2, ease: "easeIn", at: DRAW_MS + HOLD_MS - 0.2 },
        ],
      ]);
      // Idle pulse — the glow breathes (subtle opacity) and the line gently
      // scales around the FIXED viewBox center (transform-box: view-box —
      // the old fill-box origin wobbled as the partially-drawn paths changed
      // their bounding box, which read as "broken"). Runs through the draw
      // tail + hold, stops at the crossfade (the group fades out, so any
      // continued pumping is invisible anyway). Own non-awaited calls;
      // repeat Infinity lives ONLY here.
      pumpTimer = setTimeout(() => {
        if (stopped) return;
        pump = animate(
          "#launch-line-group",
          { scale: [1, 1.02, 1] },
          { duration: 1.8, ease: "easeInOut", repeat: Infinity, repeatType: "mirror" }
        );
        pumpGlow = animate(
          "#launch-line-glow",
          { opacity: [0.45, 0.9, 0.45] },
          { duration: 1.8, ease: "easeInOut", repeat: Infinity, repeatType: "mirror" }
        );
      }, 1000);
      pumpStopTimer = setTimeout(() => {
        if (stopped) return;
        pump?.stop();
        pumpGlow?.stop();
      }, (DRAW_MS + HOLD_MS - 0.2) * 1000);
      // Phase 2 fires on a timer at the erase END (the retraction itself is
      // a CSS animation on the reversed paths, outside the sequence — see
      // kala-launch-retract), so the sequence's resolve isn't the signal.
      phase2Timer = setTimeout(() => {
        if (stopped) return;
        phase2 = animate([
          ["#launch-mark", { opacity: 1 }, { duration: 0.45, ease: "easeOut" }],
          ["#launch-spinner", { opacity: 1 }, { duration: 0.35, ease: "easeOut", at: 0.2 }],
          ["#launch-copy-1", { opacity: 1 }, { duration: 0.4, ease: "easeOut", at: 0.6 }],
          ["#launch-copy-1", { opacity: 0 }, { duration: 0.35, ease: "easeIn", at: 1.65 }],
          ["#launch-copy-2", { opacity: 1 }, { duration: 0.4, ease: "easeOut", at: 1.7 }],
          ["#launch-copy-2", { opacity: 0 }, { duration: 0.35, ease: "easeIn", at: 2.75 }],
          ["#launch-copy-3", { opacity: 1 }, { duration: 0.4, ease: "easeOut", at: 2.8 }],
        ]);
      }, (DRAW_MS + HOLD_MS + ERASE_MS) * 1000);

    } else {
      // Returning / reduced-motion: no line at all — BriefLoading renders
      // logo + spinner + text, nothing to animate. controls stays null.
    }

    return () => {
      stopped = true;
      if (maxTimer) clearTimeout(maxTimer);
      if (probe) clearInterval(probe);
      if (phase2Timer) clearTimeout(phase2Timer);
      if (pumpTimer) clearTimeout(pumpTimer);
      if (pumpStopTimer) clearTimeout(pumpStopTimer);
      controls?.stop();
      pump?.stop();
      pumpGlow?.stop();
      phase2?.stop();
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
      {fullSequence ? (
        <>
      {/* Drawn line + glow, scaled to cover the viewport. The viewBox window
          (200 100 1300 800) keeps both path ends outside the frame. */}
      <svg
        viewBox="200 100 1300 800"
        preserveAspectRatio="xMidYMid slice"
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 h-full w-full"
      >
        <defs>
          <linearGradient id="launch-line-grad" x1="0%" y1="0%" x2="100%" y2="0%">
            {/* Warm yellow-orange ramp — no dark navy/black in the line. The
                dark stop is a burnt orange via color-mix (token-based, no
                hardcoded hex). */}
            <stop offset="0%" stopColor="var(--brand-gold)" />
            <stop offset="55%" stopColor="var(--brand-orange)" />
            <stop
              offset="100%"
              stopColor="color-mix(in srgb, var(--brand-orange) 62%, black)"
            />
          </linearGradient>
        </defs>
        <g
          id="launch-line-group"
          style={{ transformBox: "view-box", transformOrigin: "50% 50%" }}
        >
          {/* Glow: blur(16px), lower-opacity copy underneath the main line.
              Draw-on via motion's native pathLength support (it manages the
              dash itself); reduced motion renders fully drawn from first
              paint. */}
          <motion.path
            id="launch-line-glow"
            d={LINE_PATH}
            fill="none"
            stroke="var(--brand-orange)"
            strokeWidth={130}
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: reduceMotion ? 1 : 0, pathOffset: 0 }}
            style={{ filter: "blur(12px)", opacity: 0.45 }}
          />
          <motion.path
            id="launch-line-main"
            d={LINE_PATH}
            fill="none"
            stroke="url(#launch-line-grad)"
            strokeWidth={120}
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: reduceMotion ? 1 : 0, pathOffset: 0 }}
          />
        </g>
        {/* Reversed-geometry copies — OUTSIDE the group on purpose: the
            crossfade fades the whole group out (glow + main together, since
            the pump owns the glow's opacity and blocks an individual fade —
            probed), and these must not be affected by the group fade. They
            stay invisible until the crossfade, then retract (pathLength
            1→0) — the erase runs start-to-end along the line. */}
        <motion.path
          id="launch-line-glow-reverse"
          d={REVERSE_LINE_PATH}
          fill="none"
          stroke="var(--brand-orange)"
          strokeWidth={130}
          strokeLinecap="round"
          strokeLinejoin="round"
          pathLength={1}
          style={{
            filter: "blur(12px)",
            opacity: 0,
            strokeDasharray: "1 1",
            animation: `kala-launch-retract ${ERASE_MS}s cubic-bezier(0.83, 0, 0.17, 1) ${DRAW_MS + HOLD_MS}s both`,
          }}
        />
        <motion.path
          id="launch-line-reverse"
          d={REVERSE_LINE_PATH}
          fill="none"
          stroke="url(#launch-line-grad)"
          strokeWidth={120}
          strokeLinecap="round"
          strokeLinejoin="round"
          pathLength={1}
          style={{
            opacity: 0,
            strokeDasharray: "1 1",
            animation: `kala-launch-retract ${ERASE_MS}s cubic-bezier(0.83, 0, 0.17, 1) ${DRAW_MS + HOLD_MS}s both`,
          }}
        />
      </svg>

      {/* Brand + copy — phase-2 content, ONLY in the first-time branch */}
      <div className="relative z-10 flex flex-col items-center px-6 text-center">
        <img
          id="launch-mark"
          src="/Kala-Logo.png"
          alt="Kala"
          className="mb-5 size-16 rounded-xl object-contain"
          style={{ opacity: 0 }}
        />
        <div id="launch-spinner" className="mb-5" style={{ opacity: 0 }}>
          <Spinner className="size-6" />
        </div>
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
      </div>
        </>
      ) : (
        <BriefLoading
          title="Signing you in…"
          subtitle="Validating your launch from your course"
          className="relative z-10"
        />
      )}
    </div>
  );
}
