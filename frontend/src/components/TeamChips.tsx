"use client";

/** One-tap team attribution: 12 chips, the team on the clock outlined in the accent, my team labelled Me. */
export function TeamChips({ teams, onClock, mySlot, onPick, busy }: { teams: Record<string, string>; onClock: number | null; mySlot: number; onPick: (team: number) => void; busy: boolean }) {
  return (
    <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-1.5">
      {Object.entries(teams).map(([slot, name]) => {
        const n = Number(slot); const clock = n === onClock; const me = n === mySlot;
        return (
          <button key={slot} type="button" disabled={busy} onClick={() => onPick(n)} className="text-left rounded-[8px] px-2.5 py-2 border text-[12px] leading-tight"
            style={{ borderColor: clock ? "var(--accent)" : "var(--line)", background: me ? "var(--accent)" : "var(--card)", color: me ? "var(--accent-ink)" : "var(--text)", boxShadow: clock ? "0 0 0 2px color-mix(in srgb, var(--accent) 30%, transparent)" : undefined }}>
            <span className="block font-semibold truncate">{me ? "Me" : name}</span>
            <span className="block text-[10px] opacity-70 truncate">{slot}{clock ? " · on the clock" : me ? ` · ${name}` : ""}</span>
          </button>
        );
      })}
    </div>
  );
}
