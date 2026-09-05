"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Info } from "@/components/Info";
import { AiNote } from "@/components/AiNote";
import { fmt, pct } from "@/lib/api";

export type Market = {
  consistency: { team: string; opp: string; home: boolean; implied: number; proj_points: number; ratio: number; factor: number; flag: string }[];
  flagged: { team: string; implied: number; proj_points: number; factor: number; flag: string }[];
  starters: { id: string; name: string; pos: string; team: string | null; opp: string | null; model_mean: number | null; market_points: number | null; delta: number | null; covered: string[] | null; vegas_factor: number | null; kalshi: Record<string, unknown> | null; sim: { mean: number; sd: number; p10: number; p90: number } | null }[];
  correlations: { a: string; b: string; corr: number }[]; cross_correlations: { mine: string; theirs: string; corr: number }[];
  kalshi_games: { game: string; p_home?: number; p_away?: number; total?: { median: number }; spread?: { median: number }; team_total?: Record<string, { median: number }>; date?: string }[];
  odds: { fetched_at: number | null; credits_remaining: string | null; error: string | null; players_with_props?: number; events?: number } | null;
  kalshi: { games?: number; priced_games?: number; players?: number; error?: string } | null; props_blended: number;
};

export function MarketCheck({ m, week, onRefresh, refreshing }: { m: Market; week: number; onRefresh: () => void; refreshing: boolean }) {
  const [oddsAge, setOddsAge] = useState<number | null>(null);
  useEffect(() => { const t = setTimeout(() => setOddsAge(m.odds?.fetched_at ? Math.round((Date.now() / 1000 - m.odds.fetched_at!) / 3600) : null), 0); return () => clearTimeout(t); }, [m.odds?.fetched_at]);
  return (
    <div className="space-y-3">
      <div className="card p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="text-[12px] font-semibold uppercase tracking-wide muted flex items-center gap-2">Market check · week {week}
            <Info title="What this block is">Three independent views of the same week: our projections (Rotowire via Sleeper, scaled to Vegas team totals), sportsbook player props (the market&apos;s projection, blended 50/50 into ours when available), and Kalshi prediction-market prices. Agreement is reassurance; disagreement is where to look before you set a lineup.</Info>
          </div>
          <button disabled={refreshing} className="pill" onClick={onRefresh}>{refreshing ? "Pulling…" : "Pull props"}</button>
        </div>
        <div className="text-[12px] muted mt-1">Props: {m.odds?.error ? m.odds.error : `${m.odds?.players_with_props ?? 0} players across ${m.odds?.events ?? 0} games${oddsAge != null ? `, pulled ${oddsAge} h ago` : ""}, ${m.props_blended} blended into projections`}{m.odds?.credits_remaining ? ` · ${m.odds.credits_remaining} API credits left` : ""} · Kalshi: {m.kalshi?.priced_games ?? 0}/{m.kalshi?.games ?? 0} games priced{m.kalshi?.players ? `, ${m.kalshi.players} player markets` : ""}</div>
        <div className="mt-2"><AiNote topic="market_week" label="✨ Explain this week's market check" /></div>
      </div>

      <div className="card p-4">
        <div className="text-[12px] font-semibold uppercase tracking-wide muted flex items-center gap-2 mb-1">My starters · model vs market
          <Info title="How to read">Model = our weekly projection after Vegas scaling. Market = points implied by sportsbook props (receptions, yards, TDs) under this league&apos;s scoring, only for the stat components that have a prop. Δ = market − model: a big positive number means the books expect more than our sources; negative means less. Sim column is the correlated game simulation (mean and 10th–90th percentile).</Info>
        </div>
        <div className="grid grid-cols-[2.2rem_1fr_3.4rem_3.4rem_3.2rem_3rem_5rem] gap-x-2 text-[11px] muted pb-1 border-b line"><span>Pos</span><span>Player</span><span className="text-right">Model</span><span className="text-right">Market</span><span className="text-right">Δ</span><span className="text-right">Vegas×</span><span className="text-right">Sim p10–p90</span></div>
        {m.starters.map((s) => (
          <div key={s.id} className="grid grid-cols-[2.2rem_1fr_3.4rem_3.4rem_3.2rem_3rem_5rem] gap-x-2 items-center text-[13px] py-1.5 border-b line tabular">
            <span className={`font-bold pos-${s.pos}`}>{s.pos}</span>
            <span className="min-w-0 truncate"><Link className="underline decoration-dotted" href={`/player/${encodeURIComponent(s.id)}`}>{s.name}</Link> <span className="muted text-[11px]">{s.opp ? `vs ${s.opp}` : "bye"}</span></span>
            <span className="text-right font-semibold">{fmt(s.model_mean, 1)}</span>
            <span className="text-right">{s.market_points != null ? fmt(s.market_points, 1) : <span className="muted">–</span>}</span>
            <span className="text-right" style={{ color: s.delta == null ? "var(--muted)" : s.delta > 2 ? "var(--green)" : s.delta < -2 ? "var(--red)" : "var(--text)" }}>{s.delta != null ? `${s.delta > 0 ? "+" : ""}${fmt(s.delta, 1)}` : "–"}</span>
            <span className="text-right muted">{s.vegas_factor != null ? `${fmt(s.vegas_factor, 2)}` : "–"}</span>
            <span className="text-right muted text-[11px]">{s.sim ? `${fmt(s.sim.p10, 0)}–${fmt(s.sim.p90, 0)}` : "–"}</span>
          </div>
        ))}
        {m.starters.every((s) => s.market_points == null) && <div className="text-[12px] muted mt-2">No props blended yet. Pull props (about 6 credits per game) once lines are posted, usually Tuesday–Wednesday.</div>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="card p-4">
          <div className="text-[12px] font-semibold uppercase tracking-wide muted flex items-center gap-2 mb-1">Vegas consistency
            <Info title="How to read">For each NFL team: the points Vegas implies (total/2 ± spread/2) versus the points our player projections add up to (6 × TDs + 3 × FGs + XPs). Ratio above 1.15 means our sources are too low and the whole offense was scaled up; below 0.85, scaled down. The factor is the square root of the ratio, capped at ±15%.</Info>
          </div>
          {m.flagged.length === 0 ? <div className="text-[12px] muted">All teams within ±15% of Vegas. Nothing was scaled meaningfully.</div> : (
            <div className="text-[12px] tabular">
              {m.flagged.map((c) => <div key={c.team} className="flex justify-between py-1 border-b line"><span><span className="font-semibold">{c.team}</span> <span className="muted">Vegas {fmt(c.implied, 1)} vs proj {fmt(c.proj_points, 1)}</span></span><span style={{ color: c.flag === "low" ? "var(--green)" : "var(--amber)" }}>×{fmt(c.factor, 2)}</span></div>)}
            </div>
          )}
          <details className="mt-2 text-[12px]"><summary className="muted cursor-pointer">All {m.consistency.length} teams</summary>
            <div className="tabular mt-1">{m.consistency.map((c) => <div key={c.team} className="flex justify-between py-0.5"><span>{c.team} {c.home ? "vs" : "@"} {c.opp}</span><span className="muted">{fmt(c.implied, 1)} / {fmt(c.proj_points, 1)} · ×{fmt(c.factor, 2)}</span></div>)}</div>
          </details>
          <div className="mt-2"><AiNote topic="consistency" compact /></div>
        </div>
        <div className="card p-4">
          <div className="text-[12px] font-semibold uppercase tracking-wide muted flex items-center gap-2 mb-1">Correlations in my lineup
            <Info title="How to read">From the game-level simulation: each game&apos;s score is drawn from its Vegas line, then every player scales with his team&apos;s score. Teammates (QB + WR) rise and fall together, which raises your ceiling and lowers your floor; a DST against your own receiver moves the other way. Values are correlation coefficients (−1 to 1) of weekly points.</Info>
          </div>
          {m.correlations.length === 0 ? <div className="text-[12px] muted">No notable correlations (no stacks in the lineup).</div> : m.correlations.map((c, i) => <div key={i} className="flex justify-between text-[12px] py-1 border-b line tabular"><span>{c.a} · {c.b}</span><span style={{ color: c.corr > 0 ? "var(--green)" : "var(--red)" }}>{c.corr > 0 ? "+" : ""}{fmt(c.corr, 2)}</span></div>)}
          {m.cross_correlations.length > 0 && <div className="mt-2 text-[12px]"><div className="muted mb-1">Versus my opponent&apos;s lineup</div>{m.cross_correlations.map((c, i) => <div key={i} className="flex justify-between py-0.5 tabular"><span>{c.mine} · {c.theirs}</span><span style={{ color: c.corr > 0 ? "var(--amber)" : "var(--green)" }}>{c.corr > 0 ? "+" : ""}{fmt(c.corr, 2)}</span></div>)}</div>}
          <div className="mt-2"><AiNote topic="matchup" compact label="✨ Explain my matchup" /></div>
        </div>
      </div>

      <div className="card p-4">
        <div className="text-[12px] font-semibold uppercase tracking-wide muted flex items-center gap-2 mb-1">Kalshi prediction market · my players&apos; games
          <Info title="How to read">Public prices from Kalshi. p = the market&apos;s probability the team wins; total, spread and team totals are implied medians from the price ladders. Compare with the sportsbook line: a gap of more than a point is a sign the market is moving on news. Empty rows mean the markets are not priced yet (liquidity arrives closer to kickoff).</Info>
        </div>
        {m.kalshi_games.length === 0 ? <div className="text-[12px] muted">No Kalshi games matched to your starters yet.</div> : (
          <div className="text-[12px] tabular">{m.kalshi_games.map((g) => <div key={g.game} className="flex flex-wrap justify-between gap-2 py-1 border-b line"><span className="font-semibold">{g.game}</span><span className="muted">{g.p_home != null ? `home ${pct(g.p_home)}` : "unpriced"}{g.total ? ` · total ${fmt(g.total.median, 1)}` : ""}{g.spread ? ` · spread ${fmt(g.spread.median, 1)}` : ""}{g.team_total ? ` · ${Object.entries(g.team_total).map(([t, v]) => `${t} ${fmt(v.median, 1)}`).join(", ")}` : ""}</span></div>)}</div>
        )}
        <div className="mt-2"><AiNote topic="kalshi" compact /></div>
      </div>
    </div>
  );
}
