"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Injury, fmt, pct } from "@/lib/api";

type Reason = { kind: string; text: string; good: boolean };
type Option = {
  id: string; name: string; pos: string; team: string | null; pts: number; ppg: number; vorp: number; adp: number; bye: number | null;
  roster_score: number; roster_score_se: number; delta_vs_best: number; p_gone_by_next: number | null;
  p_available_at_decision?: number | null; conditional?: boolean; n_sims_used?: number;
  injury: Injury; reasons: Reason[]; bull: string; bear: string;
  history: { games: number; mean: number; sd: number } | null; wait_cost: number | null; wait_best: number | null;
};
type Other = { id: string; name: string; pos: string; roster_score: number; delta_vs_best: number; p_available_at_decision: number | null };
type Unlikely = { id: string; name: string; pos: string; adp: number; p_available_at_decision: number };
type Decision = {
  done?: boolean; error?: string; pick_no: number; decision_pick: number; is_me: boolean; next_pick: number | null; round: number; lookahead?: boolean;
  options: Option[]; others?: Other[]; unlikely_available?: Unlikely[]; margin: number; confidence: string; n_sims: number; computed_ms: number;
  my_picks_so_far: { id: string; name: string; pos: string }[]; drafted_count: number;
};

const KIND: Record<string, string> = { value: "Value", scarcity: "Scarcity", availability: "Availability", fit: "Roster fit", simulation: "Simulation", scoring: "League scoring", market: "Market", risk: "Risk", sources: "Sources", history: "2025" };
const LABELS = ["A", "B", "C"];
const SUFFIX = new Set(["jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"]);
const last = (name: string) => { const p = name.split(" ").filter((x) => !SUFFIX.has(x.toLowerCase())); return (p.length ? p : name.split(" ")).slice(-1)[0]; };
const signed = (n: number, d = 1) => `${n > 0 ? "+" : ""}${n.toFixed(d)}`;

export function Decide({ onChoose, busy, version = 0 }: { onChoose: (id: string) => void; busy: boolean; version?: number }) {
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
  const seen = useRef(version);
  useEffect(() => {
    if (version === seen.current) return;
    seen.current = version;
    if (!d) return;
    const t = setTimeout(() => run(true), 300);  // board changed: refresh the options
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version]);
  const labels = d ? LABELS.slice(0, d.options.length) : LABELS;
  const compareLabel = labels.length > 1 ? `${labels.slice(0, -1).join(", ")} and ${labels[labels.length - 1]}` : labels[0];
  return (
    <div className="space-y-3">
      <div className="card p-5 flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[220px]">
          <div className="text-[16px] font-bold">Run the model for my pick</div>
          <div className="text-[12px] muted">Uses every player you have marked (Gone / Mine / team picks) and treats everyone else as available. Returns the three best options, each with a bull case, a bear case and the full reason list; you choose.</div>
        </div>
        <button disabled={running || busy} className="btn btn-accent text-[15px]" onClick={() => run(true)}>{running ? "Simulating…" : d ? "Run again" : "Run"}</button>
      </div>
      {err && <div className="text-[13px]" style={{ color: "var(--red)" }}>{err}</div>}
      {d?.done && <div className="card p-4 text-sm muted">Draft complete.</div>}
      {d && !d.done && (
        <>
          <div className="text-[13px] muted">Pick #{d.decision_pick} (round {d.round}) · {d.drafted_count} players marked · your next pick #{d.next_pick ?? "–"} · {d.n_sims} sims per option · {d.computed_ms} ms · you have: {d.my_picks_so_far.map((p) => `${p.name} (${p.pos})`).join(", ") || "nobody yet"}</div>
          {d.lookahead && (
            <div className="text-[12px] muted">Picks before #{d.decision_pick} are not marked yet, so the model also guesses those. Each option&apos;s value counts only the simulated drafts where he was still on the board: it answers &quot;if he is there, is he the pick?&quot;, not &quot;will he be there?&quot;</div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {d.options.map((o, i) => (
              <div key={o.id} className="card card-hero p-5 border-l-4" style={{ borderLeftColor: i === 0 ? "var(--accent)" : "var(--line)" }}>
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[12px] font-semibold uppercase tracking-wide muted">Option {LABELS[i]}{i === 0 ? " · model favorite" : ""}</div>
                  {i === 0 ? (
                    <span className="pill"><span className="dot" style={{ background: d.confidence === "High" ? "var(--green)" : d.confidence === "Medium" ? "var(--amber)" : "var(--red)" }} />{d.confidence} · +{fmt(d.margin, 1)}</span>
                  ) : (
                    <span className="pill muted">{signed(o.delta_vs_best)} vs A</span>
                  )}
                </div>
                <Link href={`/player/${encodeURIComponent(o.id)}`} className="block mt-1"><span className="text-[26px] font-bold leading-tight">{o.name}</span></Link>
                <div className="text-[13px] muted"><span className={`font-semibold pos-${o.pos}`}>{o.pos}</span> · {o.team} · ADP {fmt(o.adp, 1)} · bye {o.bye ?? "–"}{o.injury?.flag || o.injury?.code === "Q" ? ` · ${o.injury.label ?? o.injury.code}` : ""}</div>
                {o.conditional && o.p_available_at_decision != null && (
                  <div className="text-[12px] mt-1" style={{ color: o.p_available_at_decision >= 0.5 ? "var(--muted)" : "var(--amber)" }}>On the board at #{d.decision_pick} in {pct(o.p_available_at_decision)} of sims · value below is conditional on that ({o.n_sims_used} drafts).</div>
                )}
                <div className="mt-3 rounded-[10px] px-3 py-2.5 space-y-1.5 border" style={{ borderColor: "var(--line)", background: "var(--bg)" }}>
                  <div className="flex gap-2 text-[13px] leading-snug"><span className="dot mt-1.5 shrink-0" style={{ background: "var(--green)" }} /><span><span className="font-semibold">Bull.</span> {o.bull}</span></div>
                  <div className="flex gap-2 text-[13px] leading-snug"><span className="dot mt-1.5 shrink-0" style={{ background: "var(--red)" }} /><span><span className="font-semibold">Bear.</span> {o.bear}</span></div>
                </div>
                <div className="grid grid-cols-4 gap-2 mt-3 items-end">
                  <div><div className="text-[34px] leading-none font-bold tabular">{fmt(o.vorp)}</div><div className="text-[10px] muted uppercase mt-1">VORP</div></div>
                  <div><div className="text-[22px] leading-none font-bold tabular">{fmt(o.pts)}</div><div className="text-[10px] muted uppercase mt-1">Proj pts</div></div>
                  <div><div className="text-[22px] leading-none font-bold tabular">{fmt(o.roster_score)}</div><div className="text-[10px] muted uppercase mt-1">Roster value{o.conditional ? " · if there" : ""}</div></div>
                  <div><div className="text-[22px] leading-none font-bold tabular" style={{ color: (o.wait_cost ?? 0) > 40 ? "var(--red)" : (o.wait_cost ?? 0) > 15 ? "var(--amber)" : "var(--text)" }}>{o.wait_cost != null ? `−${fmt(o.wait_cost)}` : "–"}</div><div className="text-[10px] muted uppercase mt-1">Cost of waiting on {o.pos}</div></div>
                </div>
                <ul className="mt-4 space-y-2">
                  {o.reasons.map((r, j) => (
                    <li key={j} className="flex gap-2 text-[13px] leading-snug">
                      <span className="dot mt-1.5 shrink-0" style={{ background: r.good ? "var(--green)" : "var(--amber)" }} />
                      <span><span className="font-semibold">{KIND[r.kind] ?? r.kind}.</span> {r.text}</span>
                    </li>
                  ))}
                </ul>
                <button disabled={busy} className={`btn ${i === 0 ? "btn-accent" : "btn-primary"} w-full mt-4 text-[15px]`} onClick={() => onChoose(o.id)}>I took {last(o.name)}</button>
              </div>
            ))}
          </div>
          {((d.others?.length ?? 0) > 0 || (d.unlikely_available?.length ?? 0) > 0) && (
            <div className="text-[12px] muted">
              {(d.others?.length ?? 0) > 0 && <span>Also simulated, roster value vs A: {d.others!.map((o) => `${last(o.name)} ${signed(o.delta_vs_best)}${d.lookahead && o.p_available_at_decision != null ? ` (there ${pct(o.p_available_at_decision)})` : ""}`).join(" · ")}. </span>}
              {(d.unlikely_available?.length ?? 0) > 0 && <span>Not evaluated, gone before #{d.decision_pick} in nearly every sim: {d.unlikely_available!.map((u) => `${last(u.name)} (there ${pct(u.p_available_at_decision)})`).join(" · ")}.</span>}
            </div>
          )}
          <div className="card p-4">
            {!ai ? <button disabled={asking} className="pill" onClick={askAi}>{asking ? "✨ …" : `✨ Compare ${compareLabel}`}</button> : ai.text ? (
              <div className="text-[13px]"><span className="text-[11px] muted uppercase tracking-wide">AI comparison · {ai.model} · numbers verified</span><p className="mt-1">{ai.text}</p></div>
            ) : <div className="text-[12px] muted">AI comparison unavailable ({ai.status}{ai.detail ? `: ${ai.detail}` : ""}).</div>}
          </div>
        </>
      )}
    </div>
  );
}
