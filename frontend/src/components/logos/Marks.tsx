/** Three candidate marks for Edge. Each is a plain SVG that scales from 16px to hero sizes. */

// A — "Ledger": an E built from three rules whose bottom rule runs past the others: the edge you keep.
export function MarkLedger({ size = 32, accent = "#1f8a4c", ink = "currentColor" }: { size?: number; accent?: string; ink?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden>
      <rect x="5" y="6" width="19" height="3.6" rx="1.2" fill={ink} />
      <rect x="5" y="14.2" width="14" height="3.6" rx="1.2" fill={ink} />
      <rect x="5" y="22.4" width="19" height="3.6" rx="1.2" fill={ink} />
      <rect x="24" y="22.4" width="5" height="3.6" rx="1.2" fill={accent} />
      <path d="M24.6 20.8 L29 20.8 L26.8 17.6 Z" fill={accent} />
    </svg>
  );
}

// B — "Wedge": a rising right triangle (the margin) with a clean diagonal cut: the blade edge and the delta.
export function MarkWedge({ size = 32, accent = "#2757ff", ink = "currentColor" }: { size?: number; accent?: string; ink?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden>
      <path d="M4 27 L28 27 L28 5 Z" fill={accent} />
      <path d="M4 27 L28 27 L28 5 Z" fill="none" stroke="none" />
      <path d="M11.5 27 L28 11.6" stroke="var(--card, #fff)" strokeWidth="2.6" strokeLinecap="round" />
      <path d="M4 27 L17 15" stroke={ink} strokeWidth="0" />
    </svg>
  );
}

// C — "Uptick": a sparkline that ends in a sharp upward edge; the chart language of the product as the mark.
export function MarkUptick({ size = 32, accent = "#d99a1b", ink = "currentColor" }: { size?: number; accent?: string; ink?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden>
      <path d="M4 23 L10 18.5 L14.5 21.5 L20 12.5 L23.5 15.5 L28 7.5" stroke={ink} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M22.4 6.8 L28.9 6.4 L28.4 12.9" stroke={accent} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <path d="M4 27.5 H28" stroke={ink} strokeWidth="1.6" strokeLinecap="round" opacity="0.35" />
    </svg>
  );
}
