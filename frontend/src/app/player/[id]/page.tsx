"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { PointsChart } from "@/components/PointsChart";
import { fmt } from "@/lib/api";

type Detail = {
  id: string; name: string; pos: string; team: string | null; bye: number | null; injury: Record<string, unknown> & { label?: string | null; type?: string | null; return_week?: number | null; ir_eligible?: boolean; flag?: boolean; comment?: string | null };
  adp: number; adp_sigma: number; adp_sources: Record<string, number>; yahoo_rank: number | null; proj_sources: Record<string, number>; proj_spread: number;
  vorp: number; vols: number; repl_pts: number; stash_value: number; outlook: string; owner: number | null; owner_name: string | null;
  season: { pts: number; games: number; ppg: number; stats: Record<string, number>; breakdown: Record<string, number> };
  week: { week: number; mean?: number; sd?: number; floor?: number; ceiling?: number; opp?: string | null; on_bye?: boolean; note?: string; stats?: Record<string, number>; vegas?: { implied?: number; opp_implied?: number; spread?: number; total?: number } };
  history: { season: number; games: number; mean: number | null; sd: number | null; weeks: { week: number; opp: string | null; pts: number; stats: Record<string, number>; extra?: Record<string, number> }[] };
};
const LABELS: Record<string, string> = { pass_yd: "Pass yds", pass_td: "Pass TD", pass_int: "INT", pass_2pt: "Pass 2pt", rush_yd: "Rush yds", rush_td: "Rush TD", rush_2pt: "Rush 2pt", rec: "Receptions", rec_yd: "Rec yds", rec_td: "Rec TD", rec_2pt: "Rec 2pt", fum_lost: "Fumbles lost", ret_td: "Return TD",
  fg_0_19: "FG 0-19", fg_20_29: "FG 20-29", fg_30_39: "FG 30-39", fg_0_39: "FG 0-39", fg_40_49: "FG 40-49", fg_50p: "FG 50+", xp_made: "XP", dst_sack: "Sacks", dst_int: "INT", dst_fum_rec: "Fum rec", dst_td: "Def TD", dst_safety: "Safety", dst_blk: "Blocks", dst_ret_td: "Return TD", dst_pa_0: "PA 0", dst_pa_1_6: "PA 1-6", dst_pa_7_13: "PA 7-13", dst_pa_14_20: "PA 14-20", dst_pa_21_27: "PA 21-27", dst_pa_28_34: "PA 28-34", dst_pa_35p: "PA 35+", pa: "Pts allowed" };
const WEEK_COLS: Record<string, string[]> = { QB: ["pass_yd", "pass_td", "pass_int", "rush_yd", "rush_td"], RB: ["rush_yd", "rush_td", "rec", "rec_yd", "rec_td"], WR: ["rec", "rec_yd", "rec_td", "rush_yd"], TE: ["rec", "rec_yd", "rec_td"], K: ["fg_0_19", "fg_20_29", "fg_30_39", "fg_40_49", "fg_50p", "xp_made"], DEF: ["dst_sack", "dst_int", "dst_fum_rec", "dst_td", "pa"] };

export default function PlayerPage() {
  const { id } = useParams<{ id: string }>();
  const [d, setD] = useState<Detail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [showTable, setShowTable] = useState(false);
  const [summary, setSummary] = useState<{ text: string | null; status: string; model?: string | null; detail?: string | null } | null>(null);
  const [summarizing, setSummarizing] = useState(false);
  const askSummary = async () => {
    setSummarizing(true);
    try { const r = await fetch(`/api/players/${encodeURIComponent(decodeURIComponent(id))}/summary`, { method: "POST" }); setSummary(await r.json()); } catch (e) { setSummary({ text: null, status: "error", detail: String(e) }); } finally { setSummarizing(false); }
  };
  useEffect(() => { fetch(`/api/players/${encodeURIComponent(decodeURIComponent(id))}/detail`, { cache: "no-store" }).then(async (r) => { if (!r.ok) throw new Error(await r.text()); setD(await r.json()); }).catch((e) => setErr(String(e))); }, [id]);
  if (err) return <div className="text-sm" style={{ color: "var(--red)" }}>{err}</div>;
  if (!d) return <div className="muted text-sm">Loading…</div>;
  const inj = d.injury || {};
  const wk = d.week;
  const projPerGame = d.season.games ? d.season.pts / d.season.games : null;
  const cols = WEEK_COLS[d.pos] ?? [];
  const breakdown = Object.entries(d.season.breakdown).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const maxAbs = Math.max(1, ...breakdown.map(([, v]) => Math.abs(v)));
  return (
    <div className="space-y-3">
      <Link href="/draft" className="text-[13px] muted">← Back</Link>
      <header>
        <div className="text-[26px] font-bold leading-tight">{d.name}</div>
        <div className="text-[13px] muted"><span className={`font-semibold pos-${d.pos}`}>{d.pos}</span> · {d.team ?? "FA"} · bye {d.bye ?? "–"} · ADP {fmt(d.adp, 1)} (Yahoo rank {d.yahoo_rank ? fmt(d.yahoo_rank) : "–"}){d.owner_name ? ` · on ${d.owner_name}` : " · free agent"}</div>
        {inj.flag ? <div className="text-[13px] mt-1 flex items-center gap-2"><span className="dot" style={{ background: inj.ir_eligible ? "var(--blue)" : "var(--amber)" }} />{inj.label}{inj.type ? ` · ${inj.type}` : ""}{inj.return_week ? ` · expected back week ${inj.return_week}` : ""} · {inj.ir_eligible ? "IR-eligible" : "not IR-eligible"}{d.stash_value ? ` · stash value ${fmt(d.stash_value)}` : ""}</div> : null}
      </header>
      <div className="card p-5">
        <div className="grid grid-cols-3 gap-3 items-end">
          <div><div className="text-[52px] leading-none font-bold tabular">{wk.mean != null ? fmt(wk.mean, 1) : "–"}</div><div className="text-[11px] muted uppercase mt-1">Week {wk.week} proj{wk.on_bye ? " (bye)" : wk.opp ? ` vs ${wk.opp}` : ""}</div>{wk.floor != null && <div className="text-[11px] muted">floor {fmt(wk.floor, 0)} · ceiling {fmt(wk.ceiling, 0)}</div>}</div>
          <div><div className="text-[28px] leading-none font-bold tabular">{fmt(d.season.pts)}</div><div className="text-[11px] muted uppercase mt-1">2026 season proj</div><div className="text-[11px] muted">{fmt(d.season.ppg, 1)}/g · {fmt(d.season.games, 0)} games</div></div>
          <div><div className="text-[28px] leading-none font-bold tabular">{fmt(d.vorp)}</div><div className="text-[11px] muted uppercase mt-1">VORP</div><div className="text-[11px] muted">repl {fmt(d.repl_pts)} · VOLS {fmt(d.vols)}</div></div>
        </div>
        {wk.note && <div className="text-[12px] muted mt-2">{wk.note}</div>}
        <div className="mt-3">
          {!summary ? <button disabled={summarizing} className="pill" onClick={askSummary}>{summarizing ? "Asking the model…" : "AI summary"}</button> : summary.text ? (
            <div className="text-[13px] p-3 rounded-xl" style={{ background: "var(--bg)" }}><span className="text-[11px] muted uppercase tracking-wide">AI summary · {summary.model} · numbers verified against our data</span><p className="mt-1">{summary.text}</p></div>
          ) : <div className="text-[12px] muted">AI summary unavailable ({summary.status}{summary.detail ? `: ${summary.detail}` : ""}).</div>}
        </div>
      </div>
      <div className="card p-4">
        <div className="flex items-center justify-between mb-1"><div className="text-[12px] font-semibold uppercase tracking-wide muted">{d.history.season} weekly points (league scoring)</div><div className="text-[11px] muted">{d.history.games} games · avg {fmt(d.history.mean, 1)} · sd {fmt(d.history.sd, 1)}</div></div>
        <PointsChart weeks={d.history.weeks.map((w) => ({ week: w.week, opp: w.opp, pts: w.pts }))} projMean={projPerGame} projLabel="2026 proj/g" />
        <div className="text-[11px] muted mt-1">Dashed green line: 2026 projected points per game. Hover or drag for a week.</div>
        <button className="pill mt-2" onClick={() => setShowTable(!showTable)}>{showTable ? "Hide" : "Show"} weekly table</button>
        {showTable && (
          <div className="overflow-x-auto mt-2">
            <table className="text-[12px] tabular w-full">
              <thead><tr className="muted text-left"><th className="pr-2">Wk</th><th className="pr-2">Opp</th><th className="pr-2 text-right">Pts</th>{cols.map((c) => <th key={c} className="pr-2 text-right">{LABELS[c] ?? c}</th>)}</tr></thead>
              <tbody>{d.history.weeks.map((w) => <tr key={w.week} className="border-t line"><td className="pr-2">{w.week}</td><td className="pr-2">{w.opp ?? ""}</td><td className="pr-2 text-right font-semibold">{fmt(w.pts, 1)}</td>{cols.map((c) => <td key={c} className="pr-2 text-right">{fmt(w.stats?.[c] ?? 0, c.includes("yd") || c === "pa" ? 0 : c.startsWith("fg") || c === "xp_made" ? 0 : 0)}</td>)}</tr>)}</tbody>
            </table>
          </div>
        )}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="card p-4">
          <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-2">2026 projection breakdown</div>
          {breakdown.map(([k, v]) => (
            <div key={k} className="flex items-center gap-2 py-1 text-[12px]">
              <span className="w-24 muted truncate">{LABELS[k] ?? k}</span>
              <span className="flex-1 h-2 rounded-full" style={{ background: "var(--line)" }}><span className="block h-2 rounded-full" style={{ width: `${Math.min(100, (Math.abs(v) / maxAbs) * 100)}%`, background: v < 0 ? "var(--red)" : "var(--blue)" }} /></span>
              <span className="w-14 text-right tabular">{v > 0 ? "+" : ""}{fmt(v, 0)}</span>
              <span className="w-14 text-right muted tabular">{fmt(d.season.stats[k], k.includes("yd") ? 0 : 1)}</span>
            </div>
          ))}
        </div>
        <div className="card p-4 text-[12px] space-y-1">
          <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-1">Sources</div>
          <div>Projection: {Object.entries(d.proj_sources).map(([k, v]) => `${k} ${fmt(v)}`).join(" · ")} · spread {fmt(d.proj_spread)}{d.proj_spread > 40 ? " (sources disagree)" : ""}</div>
          <div>ADP: {Object.entries(d.adp_sources).map(([k, v]) => `${k} ${fmt(v, 1)}`).join(" · ") || "–"} · consensus {fmt(d.adp, 1)} ± {fmt(d.adp_sigma, 1)}</div>
          {wk.vegas?.implied != null && <div>Vegas week {wk.week}: team implied {fmt(wk.vegas.implied, 1)} · opp implied {fmt(wk.vegas.opp_implied, 1)} · spread {wk.vegas.spread != null && wk.vegas.spread > 0 ? "+" : ""}{fmt(wk.vegas.spread, 1)} · total {fmt(wk.vegas.total, 1)}</div>}
          {wk.stats && Object.keys(wk.stats).length > 0 && <div>Week {wk.week} line: {Object.entries(wk.stats).filter(([k]) => !k.startsWith("dst_pa")).map(([k, v]) => `${LABELS[k] ?? k} ${fmt(v, k.includes("yd") ? 0 : 1)}`).join(" · ")}</div>}
          {inj.comment ? <div className="muted mt-2">Injury note: {String(inj.comment)}</div> : null}
          {d.outlook ? <div className="muted mt-2">ESPN outlook: {d.outlook}</div> : null}
        </div>
      </div>
    </div>
  );
}
