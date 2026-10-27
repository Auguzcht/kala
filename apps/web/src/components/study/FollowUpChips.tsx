import { Suggestions, Suggestion } from "@/components/ai-elements/suggestion";
import type { TutorStyle } from "@/features/tutor";

// The follow-up chip row (Gizmo's "Explain like I'm 5 / More detail" from
// the reference screenshots). Wired to the three styles routers/tutor.py's
// _STYLE_HINTS already supports server-side (default/eli5/detail) — this
// is genuinely new wiring, nothing in the UI called these before Stage 2,
// they existed only as unused backend capability.
const CHIPS: { style: TutorStyle; label: string; emoji: string }[] = [
  { style: "eli5", label: "Explain like I'm 5", emoji: "🧸" },
  { style: "detail", label: "More detail", emoji: "🔎" },
];

export function FollowUpChips({
  onPick,
  disabled,
}: {
  onPick: (style: TutorStyle) => void;
  disabled?: boolean;
}) {
  return (
    <Suggestions>
      {CHIPS.map((c) => (
        <Suggestion
          key={c.style}
          suggestion={c.style}
          disabled={disabled}
          onClick={() => onPick(c.style)}
        >
          <span aria-hidden="true">{c.emoji}</span> {c.label}
        </Suggestion>
      ))}
    </Suggestions>
  );
}
