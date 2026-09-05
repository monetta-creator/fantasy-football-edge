"use client";
import { useEffect, useState } from "react";
import { Board, PlayerRow, fmt } from "@/lib/api";
import { TeamChips } from "@/components/TeamChips";

/** Persistent "record a pick" bar: search a player, tap him, tap the team he went to. */
export function RecordPick({ board, onPick, onUndo, busy, mySlot }: { board: Board; onPick: (id: string, team: number) => Promise<void>; onUndo: () => void; busy: boolean; mySlot: number }) {
  const [q, setQ] = useState("");
  const [opts, setOpts] = useState<PlayerRow[]>([]);
  const [sel, setSel] = useState<PlayerRow | null>(null);
  useEffect(() => {
    const t = setTimeout(() => {
      if (q.trim().length < 2) { setOpts([]); return; }
      fetch(`/api/players?q=${encodeURIComponent(q)}&limit=8&sort=adp`, { cache: "no-store" }).then((r) => r.json()).then((r) => setOpts(r.players)).catch(() => {});
    }, 150);
    return () => clearTimeout(t);
  }, [q]);
  const last = [...board.picks].slice(-3).reverse();
  const done = board.pick_no == null;
  return (
    <div className="card p-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="text-[11px] font-semibold uppercase tracking-wide muted shrink-0">Record a pick{board.pick_no ? ` · #${board.pick_no}` : ""}</div>
        {!sel ? (
          <input className="flex-1 min-w-[220px] text-[15px] py-2" placeholder={done ? "Draft complete" : "Type a player name…"} value={q} disabled={done} onChange={(e) => setQ(e.target.value)} />
        ) : (
          <div className="flex-1 flex items-center gap-2 min-w-[220px]"><span className={`font-bold pos-${sel.pos}`}>{sel.pos}</span><span className="font-semibold text-[15px]">{sel.name}</span><span className="muted text-[12px]">{sel.team ?? "FA"} · VORP {fmt(sel.vorp)} · ADP {fmt(sel.adp, 1)}</span><button type="button" className="pill ml-auto" onClick={() => { setSel(null); setQ(""); }}>change</button></div>
        )}
        <button type="button" disabled={busy || board.picks.length === 0} className="pill" onClick={onUndo}>Undo last</button>
      </div>
      {!sel && opts.length > 0 && (
        <div className="mt-2 divide-y line">
          {opts.map((p) => (
            <button key={p.id} type="button" className="w-full flex items-center gap-2 py-1.5 text-left text-[13px]" onClick={() => { setSel(p); setOpts([]); }}>
              <span className={`w-8 font-bold pos-${p.pos}`}>{p.pos}</span><span className="flex-1 truncate">{p.name} <span className="muted text-[11px]">{p.team ?? "FA"} · ADP {fmt(p.adp, 1)}</span></span><span className="tabular muted text-[12px]">VORP {fmt(p.vorp)}</span>
            </button>
          ))}
        </div>
      )}
      {sel && (
        <div className="mt-3">
          <div className="text-[11px] muted mb-1.5">Who took him? (tap a team; the team on the clock is outlined)</div>
          <TeamChips teams={board.teams} onClock={board.on_clock_team} mySlot={mySlot} busy={busy} onPick={async (team) => { await onPick(sel.id, team); setSel(null); setQ(""); }} />
        </div>
      )}
      {last.length > 0 && !sel && (
        <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
          {last.map((p) => <span key={p.pick_no} className="pill"><span className="muted">#{p.pick_no}</span> <span className={`pos-${p.player.pos}`}>{p.player.pos}</span> {p.player.name} <span className="muted">→ {p.team_name}</span></span>)}
        </div>
      )}
    </div>
  );
}
