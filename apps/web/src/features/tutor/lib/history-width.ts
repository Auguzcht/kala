export const TUTOR_HISTORY_MIN = 280;
export const TUTOR_HISTORY_MAX = 440;
export const TUTOR_HISTORY_DEFAULT = 320;

export function tutorHistoryMaxWidth(viewportWidth: number): number {
  // Retain the 56px course rail and at least 480px of desktop conversation.
  return Math.max(
    TUTOR_HISTORY_MIN,
    Math.min(TUTOR_HISTORY_MAX, viewportWidth - 56 - 480),
  );
}

export function clampTutorHistoryWidth(
  width: number,
  viewportWidth: number,
): number {
  return Math.round(
    Math.max(
      TUTOR_HISTORY_MIN,
      Math.min(tutorHistoryMaxWidth(viewportWidth), width),
    ),
  );
}
