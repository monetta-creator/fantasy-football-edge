"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Rec, Week, WeekPlayer, api1, fmt, pct } from "@/lib/api";
import { RecList } from "@/components/RecList";
import { MarketCheck } from "@/components/MarketCheck";
import { Info } from "@/components/Info";
import { AiNote } from "@/components/AiNote";

const SLOT_KEYS = ["QB", "WR1", "WR2", "RB", "TE", "W/R", "W/R/T", "K", "DEF"];

function Row({ p, slot }: { p: WeekPlayer; slot: string }) {
  return (
    <div className="flex items-center gap-2 py-1.5 border-b line last:border-0 text-[13px]">
      <span className="w-12 text-[11px] font-bold muted">{slot}</span>
      <span className="flex-1 min-w-0 truncate"><span className={`font-semibold pos-${p.pos}`}>{p.pos}</span> <Link className="underline decoration-dotted" href={`/player/${encodeURIComponent(p.id)}`}>{p.name}</Link> <span className="muted">{p.on_bye ? "BYE" : p.opp ? `vs ${p.opp}` : ""}{p.injury?.flag ? ` · ${p.injury.code}` : ""}</span></span>
      <span className="tabular w-12 text-right font-semibold">{fmt(p.mean, 1)}</span>
      <span className="tabular w-16 text-right muted text-[11px]">{fmt(p.floor, 0)}–{fmt(p.ceiling, 0)}</span>
    </div>
  );
}

export default function Dashboard() {
  const [w, setW] = useState<Week | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [pulling, setPulling] = useState(false);
  const load = useCallback(() => api1.week().then((x) => { setW(x); setErr(null); }).catch((e) => setErr(String(e))), []);
  const pullProps = async () => { setPulling(true); try { const r = await fetch("/api/odds/refresh", { method: "POST" }); const d = await r.json(); setMsg(r.ok ? `Props pulled: ${d.props_blended} players blended · ${d.odds?.credits_remaining ?? "?"} credits left.` : `Props: ${d.detail ?? "error"}`); await load(); } catch (e) { setMsg(String(e)); } finally { setPulling(false); } };
  useEffect(() => { const t = setTimeout(load, 0); return () => clearTimeout(t); }, [load]);
  const act = async (r: Rec) => {
    setBusy(true);
    try {
      if (r.action === "apply_lineup") { const x = await api1.applyOptimized(); setMsg(`Lineup recorded. Win probability ${pct(x.win_prob)}. Make the same moves in Yahoo.`); }
      else if (r.action === "add" && r.player_id) { await api1.add(r.player_id); setMsg("Recorded the add. Make the same move in Yahoo."); }
      else if (r.action === "move_ir" && r.player_id) { await api1.move(r.player_id, "IR"); setMsg("Recorded the IR move. Make the same move in Yahoo."); }
      await load();
    } catch (e) { setMsg(String(e)); } finally { setBusy(false); }
  };
  if (err) return <div className="text-sm" style={{ color: "var(--red)" }}>{err}</div>;
  if (!w) return <div className="muted text-sm">Loading week…</div>;
  if (w.empty) return (
    <div className="space-y-3">
      <h1 className="text-2xl font-bold">Week {w.week}</h1>
      <div className="card p-5 text-sm">{w.message} <Link className="underline" href="/roster">Go to Roster</Link>.</div>
      <Streaming w={w} />
    </div>
  );
  const ev = w.optimized!.eval, cur = w.current!.eval;
  const wp = cur.win_prob;
  return (
    <div className="space-y-3">
      <header>
        <div className="text-[22px] font-bold leading-tight">Week {w.week} vs {w.opponent.name ?? "?"}</div>
        <div className="text-[13px] muted">{w.my_team} · {w.optimized!.posture} · {w.optimized!.n_candidates} lineups simulated</div>
      </header>
      <div className="card p-5 border-l-4" style={{ borderLeftColor: wp >= 0.55 ? "var(--green)" : wp >= 0.45 ? "var(--amber)" : "var(--red)" }}>
        <div className="text-[12px] font-semibold uppercase tracking-wide muted flex items-center gap-2">Win probability (current lineup)
          <Info title="How this is computed">20,000 simulated games. Each NFL game&apos;s score is drawn from its Vegas line, every player scales with his team&apos;s simulated score plus his own week-to-week noise (from 2025 results), and your lineup total is compared with your opponent&apos;s projected lineup. Above 55% is green, below 45% red.</Info>
        </div>
        <div className="grid grid-cols-3 gap-3 items-end mt-2">
          <div><div className="text-[56px] leading-none font-bold tabular">{Math.round(wp * 100)}<span className="text-[24px]">%</span></div><div className="text-[11px] muted uppercase mt-1">vs {w.opponent.name}</div></div>
          <div><div className="text-[28px] leading-none font-bold tabular">{fmt(cur.mean, 1)}</div><div className="text-[11px] muted uppercase mt-1">my proj · {fmt(cur.p10, 0)}–{fmt(cur.p90, 0)}</div></div>
          <div><div className="text-[28px] leading-none font-bold tabular">{fmt(cur.opp_mean, 1)}</div><div className="text-[11px] muted uppercase mt-1">opp proj</div></div>
        </div>
        {ev.win_prob > wp + 0.005 && <div className="text-[13px] mt-3">Optimized lineup: <b>{pct(ev.win_prob)}</b> ({fmt(ev.mean, 1)} proj). See the card below.</div>}
        <div className="mt-2"><AiNote topic="matchup" label="✨ Explain my matchup" /></div>
      </div>
      {msg && <div className="text-[13px] card p-3">{msg}</div>}
      <RecList recs={w.recommendations ?? []} onAction={act} busy={busy} />
      <div className="card p-4">
        <div className="flex items-center justify-between mb-1"><div className="text-[12px] font-semibold uppercase tracking-wide muted">Optimized lineup</div><span className="text-[11px] muted">proj · floor–ceiling</span></div>
        {SLOT_KEYS.map((k) => { const p = w.optimized!.lineup[k]; return p ? <Row key={k} p={p} slot={k.replace(/\d$/, "")} /> : <div key={k} className="py-1.5 text-[13px] muted">{k.replace(/\d$/, "")}: empty</div>; })}
      </div>
      <div className="card p-4">
        <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-1">{w.opponent.name}&apos;s projected lineup · {fmt(w.opponent.eval?.mean, 1)}</div>
        {(w.opponent.lineup ?? []).map((p, i) => <Row key={i} p={p} slot={p.slot ?? p.pos} />)}
        {!(w.opponent.lineup ?? []).length && <div className="text-sm muted">Opponent roster unknown. Seed from the draft board or import their roster screenshot.</div>}
      </div>
      {w.market && <MarketCheck m={w.market} week={w.week} onRefresh={pullProps} refreshing={pulling} />}
      <Streaming w={w} />
    </div>
  );
}

function Streaming({ w }: { w: Week }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {(["DEF", "K"] as const).map((pos) => (
        <div key={pos} className="card p-4">
          <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-1">{pos} streaming · week {w.week}</div>
          {w.streaming[pos].map((r) => (
            <div key={r.id} className="flex items-center gap-2 py-1.5 border-b line last:border-0 text-[13px]">
              <span className="dot" style={{ background: r.mine ? "var(--green)" : r.available ? "var(--blue)" : "var(--line)" }} />
              <span className="flex-1 min-w-0 truncate">{r.name} <span className="muted">vs {r.opp} · {pos === "DEF" ? `opp ${fmt(r.opp_implied, 1)}` : `team ${fmt(r.implied, 1)}`}{r.mine ? " · yours" : r.available ? "" : " · owned"}</span></span>
              <span className="tabular font-semibold">{fmt(r.mean, 1)}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
