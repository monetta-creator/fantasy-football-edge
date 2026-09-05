"use client";
import { useEffect, useState } from "react";
import { PickAnalysis, api, fmt, pct } from "@/lib/api";

export function Pick4Panel() {
  const [data, setData] = useState<PickAnalysis | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api.pickAnalysis().then(setData).catch((e) => setErr(String(e))); }, []);
  if (err) return <div className="card p-4 text-sm muted">{err}</div>;
  if (!data) return <div className="card p-4 text-sm muted">Simulating pick #4 scenarios…</div>;
  return (
    <div className="card p-4">
      <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-1">Pick #{data.pick_no} plan · then #{data.next_picks.join(" and #")}</div>
      <div className="text-[12px] muted mb-3">Each row: take this player at #4, simulate the rest of the draft {data.n_sims}×, score the final roster. Δ is vs. the best option. Avail is the chance he is still there at #4.</div>
      <div className="divide-y line">
        {data.candidates.map((c) => (
          <div key={c.id} className="py-2.5">
            <div className="flex items-center gap-2">
              <span className={`w-8 text-[12px] font-bold pos-${c.pos}`}>{c.pos}</span>
              <span className="flex-1 font-semibold text-[15px] truncate">{c.name}{c.injury?.flag ? <span className="ml-1 text-[11px]" style={{ color: "var(--amber)" }}>{c.injury.code}</span> : null}</span>
              <span className="tabular text-right w-14"><span className="block font-bold">{fmt(c.delta, 1)}</span><span className="block text-[10px] muted">Δ value</span></span>
              <span className="tabular text-right w-12"><span className="block">{pct(c.p_available)}</span><span className="block text-[10px] muted">avail</span></span>
              <span className="tabular text-right w-12"><span className="block">{fmt(c.vorp)}</span><span className="block text-[10px] muted">VORP</span></span>
            </div>
            <div className="text-[11px] muted mt-1 ml-10">Board at #{data.next_picks[0]}: {c.board_at_next.slice(0, 6).map((b) => `${b.name.split(" ").slice(-1)[0]} ${Math.round(b.p_available * 100)}%`).join(" · ")}</div>
            <div className="text-[11px] muted ml-10">Best left at #{data.next_picks[0]}: QB {fmt(c.best_pos_at_next.QB)} · RB {fmt(c.best_pos_at_next.RB)} · WR {fmt(c.best_pos_at_next.WR)} · TE {fmt(c.best_pos_at_next.TE)} → at #{data.next_picks[1]}: RB {fmt(c.best_pos_at_next2.RB)} · WR {fmt(c.best_pos_at_next2.WR)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
