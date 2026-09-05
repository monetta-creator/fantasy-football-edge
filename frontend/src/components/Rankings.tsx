"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { PlayerRow, fmt, pct } from "@/lib/api";

const POS = ["ALL", "QB", "RB", "WR", "TE", "K", "DEF"];
type SortKey = "vorp" | "pts" | "adp" | "stash";

/** Cheat-sheet view: full ranked board with tiers, independent of the live pick flow. */
export function Rankings({ version, onGone, onMine, busy }: { version: number; onGone: (p: PlayerRow) => void; onMine: (p: PlayerRow) => void; busy: boolean }) {
  const [pos, setPos] = useState("ALL");
  const [sort, setSort] = useState<SortKey>("vorp");
  const [q, setQ] = useState("");
  const [showDrafted, setShowDrafted] = useState(false);
  const [rows, setRows] = useState<PlayerRow[]>([]);
  const [nextPick, setNextPick] = useState<number | null>(null);
  useEffect(() => {
    let alive = true;
    fetch(`/api/players?q=${encodeURIComponent(q)}&pos=${pos}&sort=${sort}&limit=400&available=${!showDrafted}`, { cache: "no-store" }).then((r) => r.json()).then((r) => { if (alive) { setRows(r.players); setNextPick(r.next_pick); } }).catch(() => {});
    return () => { alive = false; };
  }, [q, pos, sort, showDrafted, version]);
  // tiers: break when VORP drops by more than 12% of the top VORP within the list (per position view) or every ~8 players overall
  const top = rows[0]?.vorp ?? 1;
  const v = (r: PlayerRow) => r.vorp ?? 0;
  const tiers: number[] = [];
  let tier = 1;
  rows.forEach((r, i) => { if (i > 0 && sort === "vorp" && (v(rows[i - 1]) - v(r)) > Math.max(6, 0.06 * top)) tier += 1; tiers.push(tier); });
  return (
    <div className="card p-3">
      <div className="flex flex-wrap gap-2 mb-2 items-center">
        <input className="flex-1 min-w-[160px] text-[15px]" placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)} className="text-[13px]"><option value="vorp">By VORP</option><option value="pts">By points</option><option value="adp">By ADP</option><option value="stash">By stash value</option></select>
        <label className="text-[12px] muted flex items-center gap-1"><input type="checkbox" checked={showDrafted} onChange={(e) => setShowDrafted(e.target.checked)} /> show drafted</label>
      </div>
      <div className="flex gap-1.5 mb-2 overflow-x-auto">{POS.map((p) => <button key={p} onClick={() => setPos(p)} className="pill" style={pos === p ? { background: "var(--text)", color: "var(--bg)" } : {}}>{p}</button>)}</div>
      <div className="grid grid-cols-[2rem_2.2rem_1fr_3.2rem_3.2rem_3.2rem_3.6rem_auto] gap-x-2 text-[11px] muted px-1 pb-1 border-b line">
        <span>#</span><span>Pos</span><span>Player</span><span className="text-right">VORP</span><span className="text-right">Pts</span><span className="text-right">ADP</span><span className="text-right">Gone #{nextPick ?? "–"}</span><span></span>
      </div>
      <div className="max-h-[70vh] overflow-y-auto">
        {rows.map((p, i) => (
          <div key={p.id}>
            {sort === "vorp" && (i === 0 || tiers[i] !== tiers[i - 1]) && <div className="text-[11px] font-semibold muted pt-2 pb-0.5 px-1">Tier {tiers[i]}</div>}
            <div className={`grid grid-cols-[2rem_2.2rem_1fr_3.2rem_3.2rem_3.2rem_3.6rem_auto] gap-x-2 items-center text-[13px] py-1.5 px-1 border-b line tabular ${p.drafted ? "opacity-50" : ""}`}>
              <span className="muted">{i + 1}</span>
              <span className={`font-bold pos-${p.pos}`}>{p.pos}</span>
              <span className="min-w-0 truncate"><Link className="underline decoration-dotted" href={`/player/${encodeURIComponent(p.id)}`}>{p.name}</Link> <span className="muted text-[11px]">{p.team ?? "FA"} · bye {p.bye ?? "–"}{p.injury?.flag ? ` · ${p.injury.code}` : ""}{p.drafted ? ` · #${p.drafted.pick_no}` : ""}</span></span>
              <span className="text-right font-semibold">{fmt(p.vorp)}</span>
              <span className="text-right">{fmt(p.pts)}</span>
              <span className="text-right muted">{fmt(p.adp, 1)}</span>
              <span className="text-right" style={{ color: (p.p_gone_by_next ?? 0) > 0.7 ? "var(--red)" : (p.p_gone_by_next ?? 0) > 0.35 ? "var(--amber)" : "var(--green)" }}>{nextPick && !p.drafted ? pct(p.p_gone_by_next) : "–"}</span>
              <span className="flex gap-1">{!p.drafted && <><button disabled={busy} className="pill text-[11px]" onClick={() => onGone(p)}>Gone</button><button disabled={busy} className="pill text-[11px]" style={{ borderColor: "var(--green)" }} onClick={() => onMine(p)}>Mine</button></>}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
