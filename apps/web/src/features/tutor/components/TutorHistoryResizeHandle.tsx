import { useRef, useState } from "react";
import {
  TUTOR_HISTORY_DEFAULT,
  TUTOR_HISTORY_MIN,
} from "@/features/tutor/lib/history-width";
import { cn } from "@/lib/utils";

export function TutorHistoryResizeHandle({
  width,
  maxWidth,
  onChange,
}: {
  width: number;
  maxWidth: number;
  onChange: (width: number) => void;
}) {
  const drag = useRef<{ pointer: number; x: number; width: number } | null>(
    null,
  );
  const [dragging, setDragging] = useState(false);
  function endDrag() {
    drag.current = null;
    setDragging(false);
  }
  return (
    <div
      title="Drag to resize chat history"
      role="separator"
      aria-label="Resize chat history"
      aria-orientation="vertical"
      aria-valuemin={TUTOR_HISTORY_MIN}
      aria-valuemax={maxWidth}
      aria-valuenow={width}
      aria-valuetext={`${width} pixels`}
      tabIndex={0}
      className={cn(
        "group absolute inset-y-0 -right-1 z-20 w-2 cursor-col-resize touch-none select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        dragging && "bg-muted",
      )}
      onPointerDown={(event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        event.currentTarget.focus();
        drag.current = { pointer: event.pointerId, x: event.clientX, width };
        event.currentTarget.setPointerCapture(event.pointerId);
        setDragging(true);
      }}
      onPointerMove={(event) => {
        if (drag.current?.pointer === event.pointerId)
          onChange(drag.current.width + event.clientX - drag.current.x);
      }}
      onPointerUp={(event) => {
        if (event.currentTarget.hasPointerCapture(event.pointerId))
          event.currentTarget.releasePointerCapture(event.pointerId);
        endDrag();
      }}
      onPointerCancel={endDrag}
      onLostPointerCapture={endDrag}
      onDoubleClick={() => onChange(TUTOR_HISTORY_DEFAULT)}
      onKeyDown={(event) => {
        const next =
          event.key === "ArrowLeft"
            ? width - 16
            : event.key === "ArrowRight"
              ? width + 16
              : event.key === "Home"
                ? TUTOR_HISTORY_MIN
                : event.key === "End"
                  ? maxWidth
                  : undefined;
        if (next !== undefined) {
          event.preventDefault();
          onChange(next);
        }
      }}
    >
      <span
        aria-hidden
        className="absolute inset-y-0 left-1/2 w-px bg-transparent group-hover:bg-border group-focus-visible:bg-primary"
      />
    </div>
  );
}
