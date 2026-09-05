"use client";
import Link from "next/link";
import { useState } from "react";
import { Injury, fmt, pct } from "@/lib/api";

type Reason = { kind: string; text: string; good: boolean };
type Option = { id: string; name: string; pos: string; team: string | null; pts: number; ppg: number; vorp: number; adp: number; bye: number | null; roster_score: number; roster_score_se: number; delta_vs_best: number; p_gone_by_next: number | null; injury: Injury; reasons: Reason[]; history: { games: number; mean: number; sd: number } | null };
type Decision = { done?: boolean; error?: string; pick_no: number; decision_pick: number; is_me: boolean; next_pick: number | null; round: number; options: Option[]; margin: number; confidence: string; n_sims: number; computed_ms: number; my_picks_so_far: { id: string; name: string; pos: string }[]; drafted_count: number };

const KIND: Record<string, string> = { value: "Value", scarcity: "Scarcity", availability: "Availability", fit: "Roster fit", simulation: "Simulation", scoring: "League scoring", market: "Market", risk: "Risk", sources: "Sources", history: "2025" };

export function Decide({ onChoose, busy }: { onChoose: (id: string) => void; busy: boolean }) {
  const [d, setD] = useState<Decision | null>(null);
  const [running, setRunning] = useState(false);
  const [ai, setAi] = useState<{ text: string | null; status: string; model?: string | null; detail?: string | null } | null>(null);
  const [asking, setAsking] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const run = async (fresh = false) => {
    setRunning(true); setAi(null); setErr(null);
    try { const r = await fetch(`/api/decide?fresh=${fresh}`, { cache: "no-store" }); if (!r.ok) throw new Error(await r.text()); setD(await r.json()); } catch (e) { setErr(String(e)); } finally { setRunning(false); }
  };
  const askAi = async () => { setAsking(true); try { const r = await fetch("/api/decide/explain", { method: "POST" }); setAi(await r.json()); } catch (e) { setAi({ text: null, status: "error", detail: String(e) }); } finally { setAsking(false); } };
  return (
    <div className="space-y-3">
      <div className="card p-5 flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[220px]">
          <div className="text-[16px] font-bold">Run the model for my pick</div>
          <div className="text-[12px] muted">Uses every player you have marked (Gone / Mine / team picks) and treats everyone else as available. Returns the two best options with reasons; you choose.</div>
        </div>
        <button disabled={running || busy} className="btn btn-green text-[15px]" onClick={() => run(true)}>{running ? "Simulating…" : d ? "Run again" : "Run"}</button>
      </div>
      {err && <div className="text-[13px]" style={{ color: "var(--red)" }}>{err}</div>}
      {d?.done && <div className="card p-4 text-sm muted">Draft complete.</div>}
      {d && !d.done && (
        <>
          <div className="text-[13px] muted">Pick #{d.decision_pick} (round {d.round}) · {d.drafted_count} players marked · your next pick #{d.next_pick ?? "–"} · {d.n_sims} sims per option · {d.computed_ms} ms · you have: {d.my_picks_so_far.map((p) => `${p.name} (${p.pos})`).join(", ") || "nobody yet"}</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {d.options.map((o, i) => (
              <div key={o.id} className="card p-5 border-l-4" style={{ borderLeftColor: i === 0 ? "var(--green)" : "var(--blue)" }}>
                <div className="flex items-center justify-between">
                  <div className="text-[12px] font-semibold uppercase tracking-wide muted">Option {i === 0 ? "A" : "B"}{i === 0 ? " · model favorite" : ""}</div>
                  {i === 0 && <span className="pill"><span className="dot" style={{ background: d.confidence === "High" ? "var(--green)" : d.confidence === "Medium" ? "var(--amber)" : "var(--red)" }} />{d.confidence} · +{fmt(d.margin, 1)}</span>}
                </div>
                <Link href={`/player/${encodeURIComponent(o.id)}`} className="block mt-1"><span className="text-[26px] font-bold leading-tight">{o.name}</span></Link>
                <div className="text-[13px] muted"><span className={`font-semibold pos-${o.pos}`}>{o.pos}</span> · {o.team} · ADP {fmt(o.adp, 1)} · bye {o.bye ?? "–"}{o.injury?.flag || o.injury?.code === "Q" ? ` · ${o.injury.label ?? o.injury.code}` : ""}</div>
                <div className="grid grid-cols-4 gap-2 mt-3 items-end">
                  <div><div className="text-[34px] leading-none font-bold tabular">{fmt(o.vorp)}</div><div className="text-[10px] muted uppercase mt-1">VORP</div></div>
                  <div><div className="text-[22px] leading-none font-bold tabular">{fmt(o.pts)}</div><div className="text-[10px] muted uppercase mt-1">Proj pts</div></div>
                  <div><div className="text-[22px] leading-none font-bold tabular">{fmt(o.roster_score)}</div><div className="text-[10px] muted uppercase mt-1">Roster value</div></div>
                  <div><div className="text-[22px] leading-none font-bold tabular">{d.next_pick ? pct(o.p_gone_by_next) : "–"}</div><div className="text-[10px] muted uppercase mt-1">Gone by #{d.next_pick ?? "–"}</div></div>
                </div>
                <ul className="mt-4 space-y-2">
                  {o.reasons.map((r, j) => (
                    <li key={j} className="flex gap-2 text-[13px] leading-snug">
                      <span className="dot mt-1.5 shrink-0" style={{ background: r.good ? "var(--green)" : "var(--amber)" }} />
                      <span><span className="font-semibold">{KIND[r.kind] ?? r.kind}.</span> {r.text}</span>
                    </li>
                  ))}
                </ul>
                <button disabled={busy} className="btn btn-primary w-full mt-4 text-[15px]" onClick={() => onChoose(o.id)}>I took {o.name.split(" ").slice(-1)[0]}</button>
              </div>
            ))}
          </div>
          <div className="card p-4">
            {!ai ? <button disabled={asking} className="pill" onClick={askAi}>{asking ? "Asking the model…" : "AI comparison of A vs B"}</button> : ai.text ? (
              <div className="text-[13px]"><span className="text-[11px] muted uppercase tracking-wide">AI comparison · {ai.model} · numbers verified</span><p className="mt-1">{ai.text}</p></div>
            ) : <div className="text-[12px] muted">AI comparison unavailable ({ai.status}{ai.detail ? `: ${ai.detail}` : ""}).</div>}
          </div>
        </>
      )}
    </div>
  );
}
