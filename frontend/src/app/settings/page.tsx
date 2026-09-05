"use client";
import { useEffect, useState } from "react";
import { Meta, api, fmt } from "@/lib/api";

export default function SettingsPage() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [names, setNames] = useState<Record<number, string>>({});
  const [msg, setMsg] = useState<string>("");
  const [confirmReset, setConfirmReset] = useState(false);
  const load = () => { api.meta().then(setMeta).catch((e) => setMsg(String(e))); api.board().then((b) => setNames(Object.fromEntries(Object.entries(b.teams).map(([k, v]) => [Number(k), v])))).catch(() => {}); };
  useEffect(load, []);
  const src = (meta?.sources ?? {}) as Record<string, { age_s?: number; from_cache?: boolean; error?: string | null }>;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Settings</h1>
      {msg && <div className="text-sm" style={{ color: "var(--red)" }}>{msg}</div>}
      <div className="card p-4">
        <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-2">Team names (draft slot order)</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {Array.from({ length: meta?.teams ?? 12 }, (_, i) => i + 1).map((slot) => (
            <label key={slot} className="flex items-center gap-2 text-sm"><span className="w-6 muted tabular">{slot}</span>
              <input className="flex-1" value={names[slot] ?? ""} onChange={(e) => setNames({ ...names, [slot]: e.target.value })} />
            </label>
          ))}
        </div>
        <button className="btn btn-primary mt-3" onClick={() => api.teams(names).then(() => setMsg("Saved team names.")).catch((e) => setMsg(String(e)))}>Save names</button>
      </div>
      <div className="card p-4">
        <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-2">Data</div>
        {meta ? (
          <div className="text-sm space-y-1">
            {Object.entries(src).filter(([k]) => ["sleeper", "espn", "yahoo", "injuries", "schedule"].includes(k)).map(([k, v]) => (
              <div key={k} className="flex items-center gap-2"><span className="dot" style={{ background: v?.error ? "var(--red)" : "var(--green)" }} /><span className="w-20 capitalize">{k}</span><span className="muted">fetched {v?.age_s != null ? `${Math.round(v.age_s / 60)} min ago` : "?"}{v?.error ? ` · ${v.error}` : ""}</span></div>
            ))}
            <div className="muted text-[12px] mt-1">Pool {meta.sources.counts?.pool} players · built {meta.sources.built_at} · {meta.sim_count} sims/candidate · LLM {meta.llm.enabled ? meta.llm.model : "off (deterministic rationale)"}{meta.error ? ` · ${meta.error}` : ""}</div>
          </div>
        ) : <div className="muted text-sm">Loading…</div>}
        <button className="btn btn-ghost mt-3" onClick={() => { setMsg("Refreshing sources…"); api.refresh().then((r) => { setMsg(r.error ? `Refresh error: ${r.error}` : "Sources refreshed."); load(); }).catch((e) => setMsg(String(e))); }}>Refresh projections, ADP, injuries</button>
      </div>
      {meta && (
        <div className="card p-4">
          <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-2">Model: replacement levels (league scoring)</div>
          <div className="grid grid-cols-6 gap-2 text-center text-sm tabular">
            {Object.entries(meta.replacement.replacement_pts).map(([pos, pts]) => (
              <div key={pos}><div className={`font-bold pos-${pos}`}>{pos}</div><div>{fmt(pts)}</div><div className="text-[10px] muted">#{meta.replacement.replacement_rank[pos]} · {meta.replacement.allocation.starters[pos]} start</div></div>
            ))}
          </div>
          <div className="text-[12px] muted mt-2">Flex allocation from the league-wide optimal lineup sim: W/R → {Object.entries(meta.replacement.allocation.flex["W/R"]).map(([k, v]) => `${v} ${k}`).join(", ")}; W/R/T → {Object.entries(meta.replacement.allocation.flex["W/R/T"]).map(([k, v]) => `${v} ${k}`).join(", ")}. Replacement = expected best player left on waivers after 144 picks (+ streaming uplift for K/DEF).</div>
        </div>
      )}
      <div className="card p-4">
        <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-2">Draft</div>
        {!confirmReset ? (
          <button className="btn btn-ghost" onClick={() => setConfirmReset(true)}>Reset draft board…</button>
        ) : (
          <div className="flex gap-2"><button className="btn" style={{ background: "var(--red)", color: "#fff" }} onClick={() => api.reset().then(() => { setConfirmReset(false); setMsg("Draft board reset."); })}>Yes, clear all picks</button><button className="btn btn-ghost" onClick={() => setConfirmReset(false)}>Cancel</button></div>
        )}
      </div>
      <div className="card p-4 text-sm muted">
        <div className="text-[12px] font-semibold uppercase tracking-wide mb-2">Phase 1+ (not wired yet)</div>
        Yahoo OAuth client ID/secret, OpenRouter key, autopilot rules, and IR+ toggle live in <code>.env</code> for now.
      </div>
    </div>
  );
}
