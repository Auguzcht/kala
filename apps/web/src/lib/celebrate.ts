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
// Two bursts from the lower third, angled inward, so the particles cross in
// front of the content instead of raining from the top edge. The palette is
// Kala's own (orange / gold / green / ink) — confetti that ignores the brand
// reads as a different product's celebration pasted in.
const KALA_COLORS = ["#ff8a00", "#ffc63d", "#0e1b33", "#f7f8fb"];

export function celebrate() {
  const common = {
    particleCount: 90,
    spread: 70,
    startVelocity: 45,
    decay: 0.92,
    gravity: 0.9,
    scalar: 0.9,
    ticks: 220,
    colors: KALA_COLORS,
    disableForReducedMotion: true,
  } as const;

  confetti({ ...common, origin: { x: 0.15, y: 0.9 }, angle: 60 });
  confetti({ ...common, origin: { x: 0.85, y: 0.9 }, angle: 120 });
}
