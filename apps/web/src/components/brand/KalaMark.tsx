// Kala logo mark: a chevron (the Cintana forward-motion signature) built
// from navy and gold. Placeholder starting point; refine with the final
// logo. The chevron means forward progress everywhere it appears.
export function KalaMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} role="img" aria-label="Kala">
      <path d="M6 5 L18 16 L6 27" fill="none" stroke="var(--brand-navy)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M16 5 L28 16 L16 27" fill="none" stroke="var(--brand-gold)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
