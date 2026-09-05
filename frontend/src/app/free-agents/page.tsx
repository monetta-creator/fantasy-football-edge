"use client";
import { useCallback, useEffect, useState } from "react";
import { WeekPlayer, api1, fmt } from "@/lib/api";

const POS = ["ALL", "QB", "RB", "WR", "TE", "K", "DEF"];

export default function FreeAgentsPage() {
  const [pos, setPos] = useState("ALL");
  const [sort, setSort] = useState("week");
  const [rows, setRows] = useState<WeekPlayer[]>([]);
  const [rostered, setRostered] = useState(0);
  const [week, setWeek] = useState(1);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => api1.freeAgents(pos, sort).then((r) => { setRows(r.players); setRostered(r.rostered); setWeek(r.week); }).catch((e) => setMsg(String(e))), [pos, sort]);
  useEffect(() => { const t = setTimeout(load, 0); return () => clearTimeout(t); }, [load]);
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-bold">Free agents</h1>
      <div className="text-[12px] muted">{rostered ? `${rostered} players rostered across the league (from the draft board + recorded moves). ` : "No rosters yet: everyone shows as available. "}Sniper mode (drop watcher) needs Yahoo API access or a transactions screenshot.</div>
      <div className="flex gap-1.5 overflow-x-auto">{POS.map((p) => <button key={p} onClick={() => setPos(p)} className="pill" style={pos === p ? { background: "var(--text)", color: "var(--bg)" } : {}}>{p}</button>)}
        <select className="ml-auto text-[13px] py-1" value={sort} onChange={(e) => setSort(e.target.value)}><option value="week">Week {week} proj</option><option value="season">Season VORP</option><option value="stash">IR stash value</option></select></div>
      {msg && <div className="text-[13px] card p-3">{msg}</div>}
      <div className="card p-3 divide-y line">
        {rows.map((p) => (
          <div key={p.id} className="flex items-center gap-2 py-2 text-[13px]">
            <span className={`w-8 text-[12px] font-bold pos-${p.pos}`}>{p.pos}</span>
            <span className="flex-1 min-w-0"><span className="block truncate font-medium text-[14px]">{p.name}{p.injury?.flag ? <span className="ml-1 text-[11px]" style={{ color: p.injury.ir_eligible ? "var(--blue)" : "var(--amber)" }}>{p.injury.code}</span> : null}</span><span className="block text-[11px] muted">{p.team ?? "FA"} · {p.on_bye ? "BYE" : p.opp ? `vs ${p.opp}` : "no game"} · season {fmt(p.season_pts)} · VORP {fmt(p.vorp)}{p.stash_value ? ` · stash ${fmt(p.stash_value)}` : ""}</span></span>
            <span className="tabular text-right w-12"><span className="block font-bold text-[15px]">{fmt(p.mean, 1)}</span><span className="block text-[10px] muted">wk {week}</span></span>
            <button className="pill text-[11px]" onClick={() => api1.add(p.id).then(() => { setMsg(`Recorded add: ${p.name}. Make the claim in Yahoo.`); load(); }).catch((e) => setMsg(String(e)))}>Add</button>
          </div>
        ))}
      </div>
    </div>
  );
}
