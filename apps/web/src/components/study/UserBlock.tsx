import { UserIcon } from "lucide-react";

// The student's own message in a stream — only Tutor needs this (Lessons
// has no student-authored turns, the teaching content and the check are
// both Kala's).
//
// The user avatar mirrors the assistant's (Kala logo on the left): an
// initials chip from the session display name — the shell's own pattern,
// the same chip CourseShell's topbar draws — falling back to a user
// glyph. `initials` is computed by the caller (it owns the session) so
// this block stays presentation-only. Text is plain, never markdown, and
// keeps its line breaks (whitespace-pre-wrap) the way the old inline
// version did.
export function UserBlock({
  text,
  initials,
}: {
  text: string;
  /** Display-name initials for the avatar chip; undefined falls back to a user glyph. */
  initials?: string;
}) {
  return (
    <div className="ml-auto flex max-w-[85%] items-start gap-2.5">
      <div className="min-w-0 whitespace-pre-wrap rounded-md bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground">
        {text}
      </div>
      <span
        className="grid size-7 shrink-0 place-items-center rounded-full bg-brand-slate text-[10px] font-bold text-background"
        title="You"
        aria-hidden
      >
        {initials || <UserIcon size={12} />}
      </span>
    </div>
  );
}
