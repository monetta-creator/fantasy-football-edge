"use client";
import { useEffect, useState } from "react";
import { Meta, api, api1, fmt } from "@/lib/api";

export default function SettingsPage() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [names, setNames] = useState<Record<number, string>>({});
  const [msg, setMsg] = useState<string>("");
  const [confirmReset, setConfirmReset] = useState(false);
  const [yahoo, setYahoo] = useState<{ configured: boolean; connected: boolean } | null>(null);
  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const load = () => { api.meta().then(setMeta).catch((e) => setMsg(String(e))); api.board().then((b) => setNames(Object.fromEntries(Object.entries(b.teams).map(([k, v]) => [Number(k), v])))).catch(() => {}); };
  useEffect(() => { load(); api1.yahooStatus().then(setYahoo).catch(() => {}); }, []);
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
            <div className="muted text-[12px] mt-1">Sportsbook props: {meta.odds_configured ? "The Odds API key set (pull from the Week tab, ~6 credits per game, 500/month free)" : "no ODDS_API_KEY in .env"} · Kalshi: public, no key.</div>
            <div className="muted text-[12px] mt-1">Pool {meta.sources.counts?.pool} players · built {meta.sources.built_at} · {meta.sim_count} sims/candidate · LLM {meta.llm.enabled ? `${meta.llm.model} (vision ${meta.llm.vision_model})` : "off (deterministic rationale)"}{meta.llm.last?.status && meta.llm.last.status !== "off" ? ` · last call ${meta.llm.last.status}${meta.llm.last.ms ? ` in ${meta.llm.last.ms} ms` : ""}${meta.llm.last.detail ? `: ${meta.llm.last.detail}` : ""}` : ""}{meta.error ? ` · ${meta.error}` : ""}</div>
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
      <div className="card p-4 text-sm">
        <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-2">Yahoo (read-only API)</div>
        {!yahoo ? <div className="muted">…</div> : !yahoo.configured ? <div className="muted">Application pending. When approved, put YAHOO_CLIENT_ID and YAHOO_CLIENT_SECRET in <code>.env</code> and restart.</div> : yahoo.connected ? (
          <div className="flex items-center gap-2"><span className="dot" style={{ background: "var(--green)" }} />Connected. <button className="pill" onClick={() => api1.yahooSync().then((r) => setMsg(`Synced ${r.applied.length} rosters from Yahoo.`)).catch((e) => setMsg(String(e)))}>Sync rosters now</button></div>
        ) : (
          <div className="space-y-2">
            {!authUrl ? <button className="btn btn-primary" onClick={() => api1.yahooAuthUrl().then((r) => setAuthUrl(r.url)).catch((e) => setMsg(String(e)))}>Connect Yahoo</button> : (
              <>
                <div>1. <a className="underline" href={authUrl} target="_blank" rel="noreferrer">Sign in at Yahoo</a> and copy the code it shows.</div>
                <div className="flex gap-2">2. <input className="flex-1" placeholder="paste code" value={code} onChange={(e) => setCode(e.target.value)} /><button className="btn btn-primary" onClick={() => api1.yahooCallback(code).then(() => { setMsg("Yahoo connected."); api1.yahooStatus().then(setYahoo); }).catch((e) => setMsg(String(e)))}>Finish</button></div>
              </>
            )}
          </div>
        )}
        <div className="muted mt-2 text-[12px]">Yahoo grants read access only, so every move is still made by you in the Yahoo app; this tool records and recommends.</div>
      </div>
    </div>
  );
}
