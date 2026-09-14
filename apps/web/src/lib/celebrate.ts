import confetti from "canvas-confetti";

// One shared celebration burst, so "the lesson is done" looks the same
// wherever it is triggered from and there is a single place to tune it.
//
// Gated on reduced-motion by the CALLER (see LessonChat) rather than inside
// this function: callers already know whether the user opted out, and keeping
// the check at the call site means this stays a plain side effect with no
// React dependency, callable from anywhere (the worker, a toast, a future
// streak screen).
//
// Two bursts fired from BELOW the viewport, angled inward, so the particles
// arc up into frame and cross in front of the content rather than raining down
// from the top edge. `origin.y` is a fraction of the canvas height and
// canvas-confetti accepts values past 1, so 1.05 puts the emitter just off the
// bottom edge — the confetti reads as coming from underneath the screen, which
// is what a celebration launched by a bottom-docked button should look like.
// `startVelocity` is raised to compensate for the extra distance the particles
// now have to travel before they are visible.
//
// The palette is Kala's own (orange / gold / ink / paper) — confetti that
// ignores the brand reads as a different product's celebration pasted in.
const KALA_COLORS = ["#ff8a00", "#ffc63d", "#0e1b33", "#f7f8fb"];

export function celebrate() {
  const common = {
    particleCount: 110,
    spread: 75,
    startVelocity: 58,
    decay: 0.92,
    gravity: 0.95,
    scalar: 0.95,
    ticks: 240,
    colors: KALA_COLORS,
    disableForReducedMotion: true,
  } as const;

  // Just off the bottom edge, one burst each side, angled up and inward.
  confetti({ ...common, origin: { x: 0.1, y: 1.05 }, angle: 65 });
  confetti({ ...common, origin: { x: 0.9, y: 1.05 }, angle: 115 });
}
