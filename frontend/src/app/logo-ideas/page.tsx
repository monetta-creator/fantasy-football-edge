import { MarkLedger, MarkWedge, MarkUptick } from "@/components/logos/Marks";

type Concept = {
  key: string; name: string; accent: string; Mark: (p: { size?: number; accent?: string; ink?: string }) => React.ReactElement;
  wordmark: React.ReactNode; idea: string; influence: string[]; radius: number; font: string; tracking?: string;
};

const CONCEPTS: Concept[] = [
  {
    key: "A", name: "Ledger", accent: "#1f8a4c", Mark: MarkLedger, radius: 18, font: "-apple-system, 'SF Pro Display', Inter, sans-serif",
    wordmark: <span style={{ fontWeight: 700, letterSpacing: "-0.02em" }}>Edge</span>,
    idea: "An E built from three rules. The bottom rule runs past the others and turns green: the margin you keep. Reads as a ledger, a scoreboard, a baseline.",
    influence: ["One accent: field green, used only on the number that decides something (the extended rule).", "Rules, not boxes: cards keep their left rule; tables get hairline rows; sections divide with lines instead of shadows.", "Tabular numerals everywhere; sentence-case wordmark; generous whitespace. Closest to what exists, tightened."],
  },
  {
    key: "B", name: "Wedge", accent: "#2757ff", Mark: MarkWedge, radius: 10, font: "-apple-system, 'SF Pro Display', Inter, sans-serif", tracking: "0.14em",
    wordmark: <span style={{ fontWeight: 800, letterSpacing: "0.14em", textTransform: "uppercase" }}>Edge</span>,
    idea: "A rising right triangle with one clean diagonal cut: the delta, the blade, the slope of a projection. Bold and geometric.",
    influence: ["Cobalt replaces the current blue; it is the only saturated color. Green/amber/red stay for status dots.", "Angles: hero cards get a clipped top-right corner; progress bars end in a slant; buttons drop to a 10px radius.", "Uppercase tracked labels for section headers; the wordmark is all caps. More editorial, less iOS."],
  },
  {
    key: "C", name: "Uptick", accent: "#d99a1b", Mark: MarkUptick, radius: 14, font: "ui-monospace, 'SF Mono', Menlo, monospace",
    wordmark: <span style={{ fontWeight: 600, letterSpacing: "0", fontFamily: "ui-monospace, 'SF Mono', Menlo, monospace" }}>edge</span>,
    idea: "A sparkline whose last move is a sharp upward edge. The product's chart language becomes the mark; the baseline underneath is the replacement level.",
    influence: ["Warm graphite ink with a single gold accent for the 'uptick' moments (positive deltas, the recommended option).", "Numbers set in a monospace face; sparklines appear beside hero numbers and in list rows.", "Hairline borders instead of shadows; charts and tables carry the identity, so the app feels like an instrument."],
  },
];

function Sample({ c, dark }: { c: Concept; dark: boolean }) {
  const bg = dark ? "#000" : "#f5f5f7", card = dark ? "#1c1c1e" : "#fff", ink = dark ? "#f5f5f7" : "#1d1d1f", muted = dark ? "#98989d" : "#6e6e73", line = dark ? "#2c2c2e" : "#e5e5ea";
  const Mark = c.Mark;
  return (
    <div style={{ background: bg, color: ink, padding: 16, borderRadius: 18, fontFamily: c.key === "C" ? "-apple-system, Inter, sans-serif" : undefined }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, height: 40, borderBottom: `1px solid ${line}`, marginBottom: 12 }}>
        <Mark size={22} accent={c.accent} ink={ink} />
        <span style={{ fontSize: 15 }}>{c.wordmark}</span>
        <span style={{ color: muted, fontSize: 13 }}>· Marian Prayers</span>
        <span style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
          {["Draft", "Week", "Roster"].map((t, i) => <span key={t} style={{ fontSize: 12, padding: "4px 10px", borderRadius: c.key === "B" ? 6 : 999, background: i === 0 ? ink : "transparent", color: i === 0 ? bg : muted, textTransform: c.key === "B" ? "uppercase" : "none", letterSpacing: c.key === "B" ? "0.08em" : 0 }}>{t}</span>)}
        </span>
      </div>
      <div style={{ background: card, borderRadius: c.radius, padding: 16, borderLeft: c.key === "A" ? `4px solid ${c.accent}` : undefined, border: c.key === "C" ? `1px solid ${line}` : undefined, clipPath: c.key === "B" ? "polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%)" : undefined, boxShadow: c.key === "A" ? "0 6px 20px rgba(0,0,0,.05)" : undefined }}>
        <div style={{ fontSize: 11, color: muted, textTransform: "uppercase", letterSpacing: c.key === "B" ? "0.14em" : "0.06em", fontWeight: 600 }}>Recommended pick</div>
        <div style={{ fontSize: 24, fontWeight: 700, marginTop: 4, letterSpacing: "-0.01em" }}>Puka Nacua</div>
        <div style={{ display: "flex", gap: 24, alignItems: "flex-end", marginTop: 10 }}>
          <div><div style={{ fontSize: 44, fontWeight: 700, lineHeight: 1, fontFamily: c.key === "C" ? c.font : undefined, fontVariantNumeric: "tabular-nums" }}>198</div><div style={{ fontSize: 10, color: muted, textTransform: "uppercase", marginTop: 4, borderTop: c.key === "A" ? `2px solid ${c.accent}` : undefined, paddingTop: c.key === "A" ? 3 : 0 }}>VORP</div></div>
          <div><div style={{ fontSize: 22, fontWeight: 700, lineHeight: 1, fontFamily: c.key === "C" ? c.font : undefined }}>336</div><div style={{ fontSize: 10, color: muted, textTransform: "uppercase", marginTop: 4 }}>Proj pts</div></div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 6 }}><div style={{ fontSize: 22, fontWeight: 700, lineHeight: 1, color: c.accent, fontFamily: c.key === "C" ? c.font : undefined }}>+2.0</div>{c.key === "C" && <svg width="46" height="18" viewBox="0 0 46 18"><path d="M1 14 L9 10 L16 12 L24 5 L31 8 L45 2" stroke={c.accent} strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>}<div style={{ fontSize: 10, color: muted, textTransform: "uppercase", marginBottom: 2 }}>vs runner-up</div></div>
        </div>
        <div style={{ height: 6, background: line, borderRadius: c.key === "B" ? 0 : 999, marginTop: 14, overflow: "hidden", clipPath: c.key === "B" ? "polygon(0 0, 100% 0, calc(100% - 6px) 100%, 0 100%)" : undefined }}><div style={{ width: "72%", height: "100%", background: c.accent, clipPath: c.key === "B" ? "polygon(0 0, 100% 0, calc(100% - 6px) 100%, 0 100%)" : undefined }} /></div>
        <button style={{ marginTop: 14, background: c.key === "B" ? c.accent : ink, color: bg, border: 0, borderRadius: c.key === "B" ? 8 : 14, padding: "10px 16px", fontWeight: 600, fontSize: 14, textTransform: c.key === "B" ? "uppercase" : "none", letterSpacing: c.key === "B" ? "0.08em" : 0 }}>I took Nacua</button>
      </div>
    </div>
  );
}

export default function LogoIdeas() {
  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold">Edge · three marks</h1><p className="text-[14px] muted">Each concept: the mark at 16/24/40/96 px, the header lockup, a sample card in light and dark, and what it would change across the app. Pick one and I&apos;ll apply it everywhere.</p></div>
      {CONCEPTS.map((c) => {
        const Mark = c.Mark;
        return (
          <section key={c.key} className="card p-5 space-y-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="text-[12px] font-semibold uppercase tracking-wide muted w-6">{c.key}</div>
              <div className="text-[18px] font-bold">{c.name}</div>
              <div className="flex items-end gap-5 ml-auto"><Mark size={16} accent={c.accent} /><Mark size={24} accent={c.accent} /><Mark size={40} accent={c.accent} /><Mark size={96} accent={c.accent} /></div>
            </div>
            <div className="flex items-center gap-3 text-[20px]" style={{ fontFamily: c.font }}><Mark size={28} accent={c.accent} />{c.wordmark}<span className="muted text-[15px]" style={{ fontFamily: "-apple-system, Inter, sans-serif" }}>· Marian Prayers</span><span className="ml-4 inline-block w-4 h-4 rounded-full" style={{ background: c.accent }} /><span className="text-[12px] muted" style={{ fontFamily: "-apple-system, Inter, sans-serif" }}>{c.accent}</span></div>
            <p className="text-[14px]">{c.idea}</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3"><Sample c={c} dark={false} /><Sample c={c} dark /></div>
            <ul className="text-[13px] space-y-1">{c.influence.map((t) => <li key={t} className="flex gap-2"><span className="dot mt-1.5 shrink-0" style={{ background: c.accent }} /><span>{t}</span></li>)}</ul>
          </section>
        );
      })}
    </div>
  );
}
