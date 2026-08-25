// Kala logo mark: the original chevron placeholder, superseded by the real
// hornbill brand assets (public/assets/kala-mark.png). Kept for inline SVG
// use (favicons, small fallbacks). Ink + gold, the instrument colors.
export function KalaMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} role="img" aria-label="Kala">
      <path d="M6 5 L18 16 L6 27" fill="none" stroke="var(--brand-ink)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M16 5 L28 16 L16 27" fill="none" stroke="var(--brand-gold)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
