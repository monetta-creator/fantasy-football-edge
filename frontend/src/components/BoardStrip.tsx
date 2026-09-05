"use client";
import { Board } from "@/lib/api";

export function BoardStrip({ board, onUndo, busy }: { board: Board; onUndo: () => void; busy: boolean }) {
  const last = [...board.picks].slice(-6).reverse();
  return (
    <div className="card p-3">
      <div className="flex items-center justify-between mb-1">
        <div className="text-[12px] font-semibold uppercase tracking-wide muted">Recent picks</div>
        <button disabled={busy || board.picks.length === 0} className="pill" onClick={onUndo}>Undo last</button>
      </div>
      {last.length === 0 ? <div className="text-sm muted">No picks yet. Tap a player below as each pick happens.</div> : (
        <div className="flex flex-wrap gap-1.5">
          {last.map((p) => (
            <span key={p.pick_no} className="pill"><span className="muted">#{p.pick_no}</span> <span className={`pos-${p.player.pos}`}>{p.player.pos}</span> {p.player.name} <span className="muted">· {p.team_name}</span></span>
          ))}
        </div>
      )}
    </div>
  );
}

export function TeamRosters({ board }: { board: Board }) {
  return (
    <div className="card p-4">
      <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-2">All teams</div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {board.team_rosters.map((t) => (
          <div key={t.slot} className="text-[12px]">
            <div className="font-semibold text-[13px]">{t.slot}. {t.name} <span className="muted font-normal">{Object.entries(t.counts).map(([k, v]) => `${v}${k}`).join(" ")}</span></div>
            <div className="muted truncate">{t.players.map((p) => p.name.split(" ").slice(-1)[0]).join(", ") || "—"}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
