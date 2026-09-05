"use client";
import { Board, fmt } from "@/lib/api";

export function RosterTray({ board }: { board: Board }) {
  const r = board.my_roster;
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[12px] font-semibold uppercase tracking-wide muted">My roster · {r.count}/12</div>
        <div className="text-[12px] muted tabular">starters {fmt(r.starter_pts)} pts</div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6">
        {r.slots.map((s, i) => (
          <div key={i} className="flex items-center gap-3 py-1.5 border-b line last:border-0">
            <span className="w-12 text-[11px] font-bold muted">{s.slot}</span>
            {s.player ? (
              <span className="flex-1 min-w-0 truncate text-[14px]"><span className={`font-semibold pos-${s.player.pos}`}>{s.player.pos}</span> {s.player.name} <span className="muted text-[12px]">{fmt(s.player.pts)}</span></span>
            ) : (
              <span className="flex-1 text-[13px] muted flex items-center gap-2"><span className="dot" style={{ background: s.slot === "BN" ? "var(--line)" : "var(--amber)" }} />{s.slot === "BN" ? "open" : "needs starter"}</span>
            )}
          </div>
        ))}
        {r.ir.map((p) => (
          <div key={p.id} className="flex items-center gap-3 py-1.5 border-b line last:border-0">
            <span className="w-12 text-[11px] font-bold muted">IR</span>
            <span className="flex-1 truncate text-[14px]"><span className={`font-semibold pos-${p.pos}`}>{p.pos}</span> {p.name} <span className="muted text-[12px]">{p.injury?.label}</span></span>
          </div>
        ))}
      </div>
    </div>
  );
}
