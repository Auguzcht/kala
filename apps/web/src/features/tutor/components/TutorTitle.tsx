import { useRef, useState } from "react";
import { motion, useAnimation, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

export function TutorTitle({
  name,
  active,
  onSelect,
}: {
  name: string;
  active: boolean;
  onSelect: () => void;
}) {
  const viewport = useRef<HTMLSpanElement>(null);
  const text = useRef<HTMLSpanElement>(null);
  const run = useRef(0);
  const controls = useAnimation();
  const reducedMotion = useReducedMotion();
  const [revealing, setRevealing] = useState(false);

  function reveal() {
    const overflow =
      (text.current?.scrollWidth ?? 0) - (viewport.current?.clientWidth ?? 0);
    if (reducedMotion || overflow <= 0) return;
    const current = ++run.current;
    setRevealing(true);
    void controls
      .start({
        x: [0, -overflow, -overflow, 0],
        transition: {
          duration: Math.min(12, Math.max(4, overflow / 30 + 2)),
          delay: 0.3,
          times: [0, 0.45, 0.65, 1],
          ease: "easeInOut",
        },
      })
      .then(() => {
        if (run.current === current) setRevealing(false);
      });
  }
  function reset() {
    const current = ++run.current;
    void controls
      .start({ x: 0, transition: { duration: reducedMotion ? 0 : 0.3 } })
      .then(() => {
        if (run.current === current) setRevealing(false);
      });
  }
  return (
    <button
      type="button"
      aria-label={name}
      title={name}
      aria-current={active ? "page" : undefined}
      onClick={onSelect}
      onMouseEnter={reveal}
      onMouseLeave={reset}
      onFocus={reveal}
      onBlur={reset}
      className="min-w-0 flex-1 rounded-md px-1 py-2 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
    >
      <span
        ref={viewport}
        className="relative block overflow-hidden"
        aria-hidden
      >
        <span className={cn("block truncate", revealing && "invisible")}>
          {name}
        </span>
        <motion.span
          ref={text}
          data-tutor-title
          className="absolute inset-y-0 left-0 w-max whitespace-nowrap"
          style={{ visibility: revealing ? "visible" : "hidden" }}
          animate={controls}
        >
          {name}
        </motion.span>
      </span>
    </button>
  );
}
