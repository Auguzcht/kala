import { useEffect, useRef } from "react";
import { useReducedMotion } from "motion/react";
import { UploadIcon, type UploadIconHandle } from "@/features/tutor/components/icons/upload";

export function TutorDropOverlay() {
  const icon = useRef<UploadIconHandle>(null);
  const reduced = useReducedMotion();
  useEffect(() => {
    if (!reduced) icon.current?.startAnimation();
    else icon.current?.stopAnimation();
  }, [reduced]);
  return (
    <div aria-live="polite" data-tutor-drop-overlay className="pointer-events-none absolute inset-2 z-20 flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-primary bg-background/95 p-6 text-center">
      <UploadIcon ref={icon} size={32} aria-hidden />
      <p className="font-display text-lg font-medium">Drop files to attach</p>
      <p className="text-sm text-muted-foreground">TXT, MD or PDF · Up to 5MB each</p>
    </div>
  );
}
