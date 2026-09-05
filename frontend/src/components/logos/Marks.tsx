/** Edge mark: a rising wedge with one diagonal cut (the delta, the blade, the slope of a projection). */
export function MarkWedge({ size = 32, accent = "var(--accent)", cut = "var(--bg)" }: { size?: number; accent?: string; cut?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden>
      <path d="M4 27 L28 27 L28 5 Z" fill={accent} />
      <path d="M11.5 27 L28 11.6" stroke={cut} strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  );
}
