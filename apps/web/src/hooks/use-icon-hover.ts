import { useRef, type RefObject } from "react";

// Driven hover for a controlled animated icon.
//
// Every lucide-animated icon in components/ui exposes the same imperative API
// (startAnimation / stopAnimation) and switches itself into "controlled" mode
// the moment a ref is attached — which deliberately DISABLES the icon's own
// onMouseEnter/onMouseLeave. That is the point: it lets the thing that should
// really own the gesture (a button, a nav link, a whole row) drive the icon,
// instead of only the icon's own few pixels. CourseShell's rail already works
// this way; this is the same pattern extracted so any dock/button can reuse it
// without re-deriving the ref plumbing each time.
//
// Usage:
//   const icon = useIconHover<ArrowRightIconHandle>();
//   <button onMouseEnter={icon.play} onMouseLeave={icon.stop}>
//     <ArrowRightIcon ref={icon.ref} size={16} />
//   </button>
export function useIconHover<T extends { startAnimation: () => void; stopAnimation: () => void }>() {
  const ref = useRef<T | null>(null);

  return {
    ref: ref as RefObject<T | null>,
    play: () => ref.current?.startAnimation(),
    stop: () => ref.current?.stopAnimation(),
  };
}
