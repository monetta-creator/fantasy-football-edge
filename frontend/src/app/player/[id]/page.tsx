"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { PointsChart } from "@/components/PointsChart";
import { fmt, pct } from "@/lib/api";
import { Info } from "@/components/Info";
import { AiNote } from "@/components/AiNote";

type Detail = {
  id: string; name: string; pos: string; team: string | null; bye: number | null; injury: Record<string, unknown> & { label?: string | null; type?: string | null; return_week?: number | null; ir_eligible?: boolean; flag?: boolean; comment?: string | null };
  adp: number; adp_sigma: number; adp_sources: Record<string, number>; yahoo_rank: number | null; proj_sources: Record<string, number>; proj_spread: number;
  vorp: number; vols: number; repl_pts: number; stash_value: number; outlook: string; owner: number | null; owner_name: string | null;
  season: { pts: number; games: number; ppg: number; stats: Record<string, number>; breakdown: Record<string, number> };
  week: { week: number; mean?: number; sd?: number; floor?: number; ceiling?: number; opp?: string | null; on_bye?: boolean; note?: string; stats?: Record<string, number>; vegas?: { implied?: number; opp_implied?: number; spread?: number; total?: number } };
  history: { season: number; games: number; mean: number | null; sd: number | null; weeks: { week: number; opp: string | null; pts: number; stats: Record<string, number>; extra?: Record<string, number> }[] };
  rates_2025: Record<string, number | null>; consistency: { startable_threshold?: number; startable_pct?: number; boom_pct?: number; bust_pct?: number; best?: number; worst?: number; median?: number; last4_avg?: number; first_half_avg?: number; second_half_avg?: number | null; trend?: string; rolling?: { week: number; avg3: number }[] };
  ranks: { proj_rank: number | null; vorp_rank: number | null; adp_rank: number | null; rank_2025_ppg: number | null; n_pos: number; n_2025: number };
  market?: { available: boolean; points?: number; delta_market_vs_model?: number; model_mean_before?: number; blended_mean?: number; covered?: string[]; books?: string[]; lines?: Record<string, { line?: number; p_over?: number; p_td?: number; exp_td?: number; books?: number }>; kalshi?: Record<string, { median?: number; mean?: number } | number> };
  team_consistency?: { team: string; implied: number; proj_points: number; factor: number; flag: string } | null;
};
const PROP_LABEL: Record<string, string> = { player_pass_yds: "Pass yds", player_pass_tds: "Pass TD", player_rush_yds: "Rush yds", player_receptions: "Receptions", player_reception_yds: "Rec yds", player_anytime_td: "Anytime TD" };
const RATE_LABELS: Record<string, string> = { games: "Games", pass_att_per_game: "Att/g", comp_pct: "Comp %", yds_per_att: "Yds/att", pass_yds_per_game: "Pass yds/g", pass_td_rate_pct: "TD %", int_rate_pct: "INT %", rush_yds_per_game: "Rush yds/g", rush_td: "Rush TD", carries_per_game: "Carries/g",
  targets_per_game: "Targets/g", receptions_per_game: "Rec/g", catch_pct: "Catch %", yds_per_target: "Yds/target", yds_per_rec: "Yds/rec", rec_yds_per_game: "Rec yds/g", rec_td: "Rec TD", yds_per_carry: "Yds/carry", touches_per_game: "Touches/g", td_per_game: "TD/g",
  fg_made_per_game: "FG/g", fg_pct: "FG %", fg_50plus: "50+ made", xp_per_game: "XP/g", long: "Long", sacks_per_game: "Sacks/g", takeaways_per_game: "Takeaways/g", def_td: "TDs", pts_allowed_per_game: "PA/g",
  target_share_pct: "Target share %", air_yards_share_pct: "Air-yards share %", rush_share_pct: "Rush share %", wopr: "WOPR", adot: "aDOT", racr: "RACR", yac_per_rec: "YAC/rec", air_yds_per_game: "Air yds/g",
  rec_epa_per_game: "Rec EPA/g", rush_epa_per_game: "Rush EPA/g", epa_per_target: "EPA/target", epa_per_carry: "EPA/carry", first_downs_per_game: "1st downs/g",
  pass_epa_per_game: "Pass EPA/g", epa_per_dropback: "EPA/dropback", yac_pct_of_yds: "YAC % of yds" };
const RATE_HELP: Record<string, string> = { wopr: "Weighted opportunity: 1.5 × target share + 0.7 × air-yards share", adot: "Average depth of target (air yards per target)", racr: "Receiving yards per air yard", epa_per_target: "Expected points added per target", epa_per_carry: "Expected points added per carry", epa_per_dropback: "Expected points added per pass attempt" };
const LABELS: Record<string, string> = { pass_yd: "Pass yds", pass_td: "Pass TD", pass_int: "INT", pass_2pt: "Pass 2pt", rush_yd: "Rush yds", rush_td: "Rush TD", rush_2pt: "Rush 2pt", rec: "Receptions", rec_yd: "Rec yds", rec_td: "Rec TD", rec_2pt: "Rec 2pt", fum_lost: "Fumbles lost", ret_td: "Return TD",
  fg_0_19: "FG 0-19", fg_20_29: "FG 20-29", fg_30_39: "FG 30-39", fg_0_39: "FG 0-39", fg_40_49: "FG 40-49", fg_50p: "FG 50+", xp_made: "XP", dst_sack: "Sacks", dst_int: "INT", dst_fum_rec: "Fum rec", dst_td: "Def TD", dst_safety: "Safety", dst_blk: "Blocks", dst_ret_td: "Return TD", dst_pa_0: "PA 0", dst_pa_1_6: "PA 1-6", dst_pa_7_13: "PA 7-13", dst_pa_14_20: "PA 14-20", dst_pa_21_27: "PA 21-27", dst_pa_28_34: "PA 28-34", dst_pa_35p: "PA 35+", pa: "Pts allowed" };
const WEEK_COLS: Record<string, string[]> = { QB: ["pass_yd", "pass_td", "pass_int", "rush_yd", "rush_td"], RB: ["rush_yd", "rush_td", "rec", "rec_yd", "rec_td"], WR: ["rec", "rec_yd", "rec_td", "rush_yd"], TE: ["rec", "rec_yd", "rec_td"], K: ["fg_0_19", "fg_20_29", "fg_30_39", "fg_40_49", "fg_50p", "xp_made"], DEF: ["dst_sack", "dst_int", "dst_fum_rec", "dst_td", "pa"] };
const WEEK_EXTRA: Record<string, [string, string, number][]> = { QB: [["attempts", "Att", 0], ["passing_epa", "EPA", 1]], RB: [["carries", "Car", 0], ["targets", "Tgt", 0], ["rush_share", "Rush%", 0]], WR: [["targets", "Tgt", 0], ["target_share", "Tgt%", 0], ["receiving_air_yards", "AirY", 0], ["receiving_epa", "EPA", 1]], TE: [["targets", "Tgt", 0], ["target_share", "Tgt%", 0], ["receiving_epa", "EPA", 1]], K: [], DEF: [] };
const pctish = (k: string, v: number | undefined) => (v == null ? undefined : k.endsWith("share") ? v * 100 : v);

export default function PlayerPage() {
  const { id } = useParams<{ id: string }>();
  const [d, setD] = useState<Detail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [showTable, setShowTable] = useState(false);
  const [summary, setSummary] = useState<{ text: string | null; status: string; model?: string | null; detail?: string | null } | null>(null);
  const [cmpQ, setCmpQ] = useState("");
  const [cmpOpts, setCmpOpts] = useState<{ id: string; name: string; pos: string; team: string | null }[]>([]);
  const [cmp, setCmp] = useState<Detail | null>(null);
  useEffect(() => {
    const t = setTimeout(() => {
      if (cmpQ.length < 2) { setCmpOpts([]); return; }
      fetch(`/api/players?q=${encodeURIComponent(cmpQ)}&available=false&limit=8`, { cache: "no-store" }).then((r) => r.json()).then((r) => setCmpOpts(r.players)).catch(() => {});
    }, 200);
    return () => clearTimeout(t);
  }, [cmpQ]);
  const pickCompare = (pid: string) => { setCmpQ(""); setCmpOpts([]); fetch(`/api/players/${encodeURIComponent(pid)}/detail`, { cache: "no-store" }).then((r) => r.json()).then(setCmp).catch(() => {}); };
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
          {!summary ? <button disabled={summarizing} className="pill" onClick={askSummary}>{summarizing ? "✨ …" : "✨ Summary"}</button> : summary.text ? (
            <div className="text-[13px] p-3 rounded-xl" style={{ background: "var(--bg)" }}><span className="text-[11px] muted uppercase tracking-wide">AI summary · {summary.model} · numbers verified against our data</span><p className="mt-1">{summary.text}</p></div>
          ) : <div className="text-[12px] muted">AI summary unavailable ({summary.status}{summary.detail ? `: ${summary.detail}` : ""}).</div>}
        </div>
      </div>
      <div className="card p-4">
        <div className="flex items-center justify-between mb-1"><div className="text-[12px] font-semibold uppercase tracking-wide muted">{d.history.season} weekly points (league scoring)</div><div className="text-[11px] muted">{d.history.games} games · avg {fmt(d.history.mean, 1)} · sd {fmt(d.history.sd, 1)}</div></div>
        <PointsChart weeks={d.history.weeks.map((w) => ({ week: w.week, opp: w.opp, pts: w.pts }))} projMean={projPerGame} projLabel="2026 proj/g" label={d.name} rolling={d.consistency?.rolling} compare={cmp ? cmp.history.weeks.map((w) => ({ week: w.week, opp: w.opp, pts: w.pts })) : undefined} compareLabel={cmp?.name} />
        <div className="text-[11px] muted mt-1">Dashed green line: 2026 projected points per game. Hover or drag for a week.</div>
        {d.consistency?.startable_pct != null && (
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mt-3 text-center tabular">
            <div><div className="text-[20px] font-bold">{d.consistency.startable_pct}%</div><div className="text-[10px] muted uppercase">startable (≥{d.consistency.startable_threshold})</div></div>
            <div><div className="text-[20px] font-bold">{d.consistency.boom_pct}%</div><div className="text-[10px] muted uppercase">boom (≥25)</div></div>
            <div><div className="text-[20px] font-bold">{d.consistency.bust_pct}%</div><div className="text-[10px] muted uppercase">bust (&lt;8)</div></div>
            <div><div className="text-[20px] font-bold">{fmt(d.consistency.median, 1)}</div><div className="text-[10px] muted uppercase">median</div></div>
            <div><div className="text-[20px] font-bold">{fmt(d.consistency.last4_avg, 1)}</div><div className="text-[10px] muted uppercase">last 4 avg</div></div>
            <div><div className="text-[20px] font-bold" style={{ color: d.consistency.trend === "up" ? "var(--green)" : d.consistency.trend === "down" ? "var(--red)" : "var(--text)" }}>{d.consistency.trend === "up" ? "↑" : d.consistency.trend === "down" ? "↓" : "→"} {fmt(d.consistency.second_half_avg, 1)}</div><div className="text-[10px] muted uppercase">2nd half avg (1st {fmt(d.consistency.first_half_avg, 1)})</div></div>
          </div>
        )}
        <div className="mt-3 relative">
          <div className="flex items-center gap-2">
            <input className="flex-1 text-[14px]" placeholder="Benchmark against another player…" value={cmpQ} onChange={(e) => setCmpQ(e.target.value)} />
            {cmp && <button className="pill" onClick={() => setCmp(null)}>Clear {cmp.name.split(" ").slice(-1)[0]}</button>}
          </div>
          {cmpOpts.length > 0 && (
            <div className="absolute z-20 left-0 right-0 card mt-1 p-1 max-h-60 overflow-y-auto">
              {cmpOpts.map((o) => <button key={o.id} className="block w-full text-left px-3 py-2 text-[13px] hover:opacity-70" onClick={() => pickCompare(o.id)}><span className={`font-semibold pos-${o.pos}`}>{o.pos}</span> {o.name} <span className="muted">{o.team ?? ""}</span></button>)}
            </div>
          )}
        </div>
        {cmp && (
          <div className="overflow-x-auto mt-3">
            <table className="text-[13px] tabular w-full">
              <thead><tr className="muted text-left"><th></th><th className="text-right"><span className="dot" style={{ background: "var(--blue)" }} /> {d.name}</th><th className="text-right"><span className="dot" style={{ background: "var(--amber)" }} /> {cmp.name}</th></tr></thead>
              <tbody>
                {([
                  ["2026 proj pts", d.season.pts, cmp.season.pts, 0], ["Proj per game", d.season.ppg, cmp.season.ppg, 1], ["VORP", d.vorp, cmp.vorp, 0], ["ADP", d.adp, cmp.adp, 1],
                  ["Pos rank (proj)", d.ranks?.proj_rank, cmp.ranks?.proj_rank, 0], [`Week ${d.week.week} proj`, d.week.mean, cmp.week.mean, 1], ["Week floor", d.week.floor, cmp.week.floor, 1], ["Week ceiling", d.week.ceiling, cmp.week.ceiling, 1],
                  ["2025 avg", d.history.mean, cmp.history.mean, 1], ["2025 sd", d.history.sd, cmp.history.sd, 1], ["2025 pos rank (ppg)", d.ranks?.rank_2025_ppg, cmp.ranks?.rank_2025_ppg, 0], ["Startable %", d.consistency?.startable_pct, cmp.consistency?.startable_pct, 0], ["Boom %", d.consistency?.boom_pct, cmp.consistency?.boom_pct, 0], ["Bust %", d.consistency?.bust_pct, cmp.consistency?.bust_pct, 0],
                  ...Object.keys(d.rates_2025 ?? {}).filter((k) => k !== "games" && cmp.rates_2025?.[k] != null).map((k) => [RATE_LABELS[k] ?? k, d.rates_2025[k], cmp.rates_2025[k], 1] as [string, number | null | undefined, number | null | undefined, number]),
                ] as [string, number | null | undefined, number | null | undefined, number][]).map(([label, a, b, dec]) => (
                  <tr key={label} className="border-t line"><td className="py-1 pr-2 muted">{label}</td><td className="text-right font-semibold">{fmt(a, dec)}</td><td className="text-right">{fmt(b, dec)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <button className="pill mt-2" onClick={() => setShowTable(!showTable)}>{showTable ? "Hide" : "Show"} weekly table</button>
        {showTable && (
          <div className="overflow-x-auto mt-2">
            <table className="text-[12px] tabular w-full">
              <thead><tr className="muted text-left"><th className="pr-2">Wk</th><th className="pr-2">Opp</th><th className="pr-2 text-right">Pts</th>{cols.map((c) => <th key={c} className="pr-2 text-right">{LABELS[c] ?? c}</th>)}{(WEEK_EXTRA[d.pos] ?? []).map(([k, l]) => <th key={k} className="pr-2 text-right">{l}</th>)}</tr></thead>
              <tbody>{d.history.weeks.map((w) => <tr key={w.week} className="border-t line"><td className="pr-2">{w.week}</td><td className="pr-2">{w.opp ?? ""}</td><td className="pr-2 text-right font-semibold">{fmt(w.pts, 1)}</td>{cols.map((c) => <td key={c} className="pr-2 text-right">{fmt(w.stats?.[c] ?? 0, 0)}</td>)}{(WEEK_EXTRA[d.pos] ?? []).map(([k, , dec]) => <td key={k} className="pr-2 text-right">{fmt(pctish(k, w.extra?.[k]), dec)}</td>)}</tr>)}</tbody>
            </table>
          </div>
        )}
      </div>
      <div className="card p-4">
        <div className="text-[12px] font-semibold uppercase tracking-wide muted flex items-center gap-2 mb-1">Market · week {wk.week}
          <Info title="How to read">Sportsbook props are the market&apos;s projection for this player; each line is the median with the over/under prices giving the lean. We convert the props that exist into this league&apos;s points and blend them 50/50 into the weekly projection. Kalshi shows prediction-market ladders where priced. The Vegas factor is how much the whole team&apos;s projection was scaled toward its implied total.</Info>
        </div>
        {d.market?.available ? (
          <>
            <div className="grid grid-cols-3 gap-2 items-end tabular">
              <div><div className="text-[24px] font-bold">{fmt(d.market.points, 1)}</div><div className="text-[10px] muted uppercase">market-implied pts</div></div>
              <div><div className="text-[24px] font-bold">{fmt(d.market.model_mean_before, 1)}</div><div className="text-[10px] muted uppercase">model before blend</div></div>
              <div><div className="text-[24px] font-bold" style={{ color: (d.market.delta_market_vs_model ?? 0) > 2 ? "var(--green)" : (d.market.delta_market_vs_model ?? 0) < -2 ? "var(--red)" : "var(--text)" }}>{(d.market.delta_market_vs_model ?? 0) > 0 ? "+" : ""}{fmt(d.market.delta_market_vs_model, 1)}</div><div className="text-[10px] muted uppercase">market − model</div></div>
            </div>
            <div className="flex flex-wrap gap-2 mt-2 text-[12px]">{Object.entries(d.market.lines ?? {}).map(([k, v]) => <span key={k} className="pill">{PROP_LABEL[k] ?? k} {v.line != null ? `${v.line}` : v.p_td != null ? pct(v.p_td) : ""}{v.p_over != null ? <span className="muted"> · over {pct(v.p_over)}</span> : null}</span>)}</div>
            <div className="text-[11px] muted mt-1">Blended weekly mean {fmt(d.market.blended_mean, 1)} · books: {(d.market.books ?? []).join(", ") || "–"}</div>
          </>
        ) : <div className="text-[12px] muted">No sportsbook props pulled for this player this week{d.team_consistency ? `; team scaled ×${fmt(d.team_consistency.factor, 2)} (Vegas ${fmt(d.team_consistency.implied, 1)} vs projected ${fmt(d.team_consistency.proj_points, 1)})` : ""}.</div>}
        {d.market?.kalshi && <div className="text-[12px] mt-2">Kalshi: {Object.entries(d.market.kalshi).map(([k, v]) => `${k} ${typeof v === "number" ? pct(v) : fmt((v as { median?: number }).median, 1)}`).join(" · ")}</div>}
        <div className="mt-2"><AiNote topic="player_market" id={d.id} compact /></div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="card p-4">
          <div className="text-[12px] font-semibold uppercase tracking-wide muted mb-2">Position ranks · {d.pos}</div>
          <div className="grid grid-cols-4 gap-2 text-center tabular">
            <div><div className="text-[22px] font-bold">#{d.ranks?.proj_rank ?? "–"}</div><div className="text-[10px] muted uppercase">2026 proj</div></div>
            <div><div className="text-[22px] font-bold">#{d.ranks?.vorp_rank ?? "–"}</div><div className="text-[10px] muted uppercase">VORP</div></div>
            <div><div className="text-[22px] font-bold">#{d.ranks?.adp_rank ?? "–"}</div><div className="text-[10px] muted uppercase">ADP</div></div>
            <div><div className="text-[22px] font-bold">#{d.ranks?.rank_2025_ppg ?? "–"}</div><div className="text-[10px] muted uppercase">2025 ppg</div></div>
          </div>
          <div className="text-[11px] muted mt-2">Among {d.ranks?.n_pos} {d.pos}s in the pool; 2025 rank among {d.ranks?.n_2025} with 6+ games.</div>
          {d.rates_2025 && Object.keys(d.rates_2025).length > 1 && (
            <>
              <div className="text-[12px] font-semibold uppercase tracking-wide muted mt-4 mb-1">2025 rates</div>
              <div className="grid grid-cols-3 gap-x-3 gap-y-1 text-[12px] tabular">
                {Object.entries(d.rates_2025).filter(([k, v]) => k !== "games" && v != null).map(([k, v]) => <div key={k} className="flex justify-between border-b line py-0.5" title={RATE_HELP[k]}><span className="muted">{RATE_LABELS[k] ?? k}</span><span className="font-semibold">{fmt(v, Number.isInteger(v) ? 0 : k.startsWith("epa") || k === "racr" || k === "wopr" ? 2 : 1)}</span></div>)}
              </div>
            </>
          )}
        </div>
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
