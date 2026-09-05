"use client";
import { useEffect, useState } from "react";
import { PlayerRow, api, fmt, pct } from "@/lib/api";

const POS = ["ALL", "QB", "RB", "WR", "TE", "K", "DEF"];

export function PlayerList({ version, onOpen, nextPick }: { version: number; onOpen: (p: PlayerRow) => void; nextPick: number | null }) {
  const [q, setQ] = useState("");
  const [pos, setPos] = useState("ALL");
  const [sort, setSort] = useState("vorp");
  const [rows, setRows] = useState<PlayerRow[]>([]);
  useEffect(() => {
    let alive = true;
    api.players(q, pos, sort, 200).then((r) => alive && setRows(r.players)).catch(() => {});
    return () => { alive = false; };
  }, [q, pos, sort, version]);
  return (
    <div className="card p-3">
      <div className="flex gap-2 mb-2">
        <input className="flex-1 text-[16px]" placeholder="Search player or team" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={sort} onChange={(e) => setSort(e.target.value)} className="text-[14px]">
          <option value="vorp">VORP</option><option value="pts">Pts</option><option value="adp">ADP</option><option value="stash">Stash</option>
        </select>
      </div>
      <div className="flex gap-1.5 mb-2 overflow-x-auto">
        {POS.map((p) => (
          <button key={p} onClick={() => setPos(p)} className="pill" style={pos === p ? { background: "var(--text)", color: "var(--bg)" } : {}}>{p}</button>
        ))}
      </div>
      <div className="divide-y line max-h-[60vh] overflow-y-auto">
        {rows.map((p) => (
          <button key={p.id} className="w-full flex items-center gap-2 py-2 text-left" onClick={() => onOpen(p)}>
            <span className={`w-8 text-[12px] font-bold pos-${p.pos}`}>{p.pos}</span>
            <span className="flex-1 min-w-0">
              <span className="block truncate text-[15px] font-medium">{p.name}{p.injury?.flag ? <span className="ml-1 text-[11px]" style={{ color: p.injury.ir_eligible ? "var(--blue)" : "var(--amber)" }}>{p.injury.code}</span> : null}</span>
              <span className="block text-[11px] muted">{p.team ?? "FA"} · ADP {fmt(p.adp, 1)} · Y{p.yahoo_rank ? fmt(p.yahoo_rank) : "–"} · bye {p.bye ?? "–"}{p.proj_spread > 40 ? " · sources disagree" : ""}</span>
            </span>
            <span className="text-right tabular w-12"><span className="block font-bold text-[15px]">{fmt(p.vorp)}</span><span className="block text-[10px] muted">VORP</span></span>
            <span className="text-right tabular w-12"><span className="block text-[14px]">{fmt(p.pts)}</span><span className="block text-[10px] muted">pts</span></span>
            <span className="text-right tabular w-12"><span className="block text-[14px]" style={{ color: (p.p_gone_by_next ?? 0) > 0.7 ? "var(--red)" : (p.p_gone_by_next ?? 0) > 0.35 ? "var(--amber)" : "var(--green)" }}>{nextPick ? pct(p.p_gone_by_next) : "–"}</span><span className="block text-[10px] muted">gone</span></span>
          </button>
        ))}
        {rows.length === 0 && <div className="py-6 text-center muted text-sm">No players</div>}
      </div>
    </div>
  );
}
