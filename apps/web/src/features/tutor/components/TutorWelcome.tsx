import { motion, useReducedMotion } from "motion/react";

export function TutorWelcome({
  greeting,
  idle,
}: {
  greeting: string;
  idle: boolean;
}) {
  const reducedMotion = useReducedMotion();
  const animate = idle && !reducedMotion;
  return (
    <div className="mx-auto mb-8 flex self-end max-w-xl flex-col items-center gap-5 px-4 text-center">
      <motion.img
        src="/Kala-Logo.svg"
        alt="Kala"
        className="size-16 object-contain"
        animate={
          animate ? { y: [0, -3, 0], rotate: [0, 1, 0] } : { y: 0, rotate: 0 }
        }
        transition={
          animate
            ? { duration: 6, repeat: Infinity, ease: "easeInOut" }
            : { duration: 0 }
        }
      />
      <h1 className="font-display text-2xl font-semibold tracking-tight sm:text-3xl">
        {greeting}
      </h1>
    </div>
  );
}
