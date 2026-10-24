import { useReducedMotion } from "motion/react";
import { useIconHover } from "@/hooks/use-icon-hover";

export type TutorIconHandle = {
  startAnimation: () => void;
  stopAnimation: () => void;
};

/** Event forwarding only: each published icon owns its distinct animation. */
export function useTutorIcon() {
  const icon = useIconHover<TutorIconHandle>();
  const reducedMotion = useReducedMotion();
  const play = () => {
    if (!reducedMotion) icon.play();
  };
  const stop = () => {
    if (!reducedMotion) icon.stop();
  };
  return {
    ref: icon.ref,
    events: {
      onMouseEnter: play,
      onMouseLeave: stop,
      onFocus: play,
      onBlur: stop,
    },
  };
}
