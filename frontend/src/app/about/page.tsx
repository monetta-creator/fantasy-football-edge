const S = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="card p-5 space-y-2"><h2 className="text-[17px] font-bold">{title}</h2><div className="text-[14px] leading-relaxed space-y-2">{children}</div></section>
);
const M = ({ name, children }: { name: string; children: React.ReactNode }) => (
  <div><span className="font-semibold">{name}.</span> {children}</div>
);

export default function AboutPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">About the numbers</h1>
      <p className="text-[14px] muted">Every number here is computed from raw stat projections and this league&apos;s exact scoring (Yahoo league 872372: full PPR, 6-pt passing TD, 1 pt per 25 passing yards, one RB slot, two WR, TE, W/R, W/R/T, K, DEF, 6 bench, 6 IR, 12 teams). The language model never computes a number; it only rephrases numbers we computed, and any sentence containing a number we did not supply is discarded.</p>

      <S title="Projections">
        <M name="Season projection (pts)">Raw stat lines from ESPN and Sleeper/Rotowire, averaged per stat (50/50), then scored with league rules. K and DST come from ESPN only because Sleeper omits short field goals and points-allowed. Per-game = season / projected games (ESPN&apos;s games estimate, which already discounts suspensions and known absences).</M>
        <M name="Week projection (mean)">Sleeper&apos;s weekly raw stats scored with league rules. DST points-allowed is a 50/50 blend of Sleeper&apos;s expected points allowed and the Vegas opponent implied total, converted to Yahoo&apos;s buckets with a normal approximation (sd 9.5). Kicker field-goal and extra-point expectations are scaled by the square root of the team&apos;s implied total relative to a 22.5-point league average.</M>
        <M name="Floor / ceiling">10th and 90th percentile of the weekly distribution: mean ± 1.28 × sd.</M>
        <M name="Weekly sd">Week-to-week spread. From the player&apos;s own 2025 weekly results (at least 6 games), shrunk 70/30 toward the position median coefficient of variation (QB 0.47, RB 0.57, WR 0.58, TE 0.63, K 0.5, DEF 0.7), scaled to this week&apos;s mean.</M>
        <M name="Source spread">Gap between the ESPN and Sleeper season projections under league scoring. Above 40 points is flagged as &quot;sources disagree&quot;: something the market knows that the models split on.</M>
      </S>

      <S title="Value">
        <M name="Replacement level">Per position, the expected points of the best player left undrafted after all 180 picks, using the ADP model below. In a league with free, unlimited pickups this is what a roster spot is worth relative to. K and DEF get a streaming uplift (0.5 and 1.5 points per game) because you can pick the best matchup every week.</M>
        <M name="VORP">Value over replacement: season projection minus the replacement level at the position. The headline draft number. Negative means a waiver pickup projects better.</M>
        <M name="VOLS">Value over last starter: season projection minus the last starter at the position in a league-wide optimal lineup allocation. A secondary number; it also tells you how the flex slots split empirically (this pool: RB 25 starters, WR 35, TE 12).</M>
        <M name="Stash value">For injured players: the weighted surplus over replacement from the expected return week through week 17 (weeks 1–7 × 0.5, 8–14 × 1.0, playoff weeks 15–17 × 1.5), discounted by a designation risk factor (IR-R 0.85, IR 0.7, PUP 0.7, suspension 0.95). Return week comes from ESPN&apos;s injuries feed. A blue dot means the Yahoo status is IR-slot eligible today; amber means he must sit on the bench first.</M>
      </S>

      <S title="Draft">
        <M name="ADP (consensus)">0.6 × Yahoo average pick + 0.2 × Sleeper PPR ADP + 0.2 × ESPN ADP. Yahoo weighs most because your league drafts in Yahoo&apos;s room. A player&apos;s draft position is modelled as Normal(ADP, sigma) with sigma = 1 + 0.16 × ADP, widened by half the disagreement between sources and capped at 35.</M>
        <M name="Gone by #N">Probability the player is taken before your next pick, conditional on still being available now. On the recommendation card it comes from the simulations; in the lists it is the analytic normal-model number.</M>
        <M name="Tiers (Rankings tab)">A new tier starts wherever VORP drops by more than 6 points or 6% of the top VORP between consecutive players. Use them to see when a position&apos;s value cliff is coming.</M>
        <M name="Roster value (sims)">For each candidate at your pick, the rest of the draft is simulated 200–300 times: opponents take the available player with the lowest noisy ADP (per-team noise, roster caps: 3 QB, 8 RB, 8 WR, 3 TE, 2 K, 2 DEF, no K/DEF before round 8); your later picks follow need-weighted VORP with forced QB/TE fills from round 12 and DEF/K in the last two rounds. Each simulated final roster is scored as the sum of starters&apos; VORP (optimal lineup) plus bench VORP weighted 0.20, 0.15, 0.12, 0.08, 0.05, 0.03 by bench depth; IR-eligible players count their stash value and use no bench slot. The recommendation is the candidate with the highest mean roster value.</M>
        <M name="Δ vs #1">Difference in mean roster value between an alternative and the recommended pick, in the same units as VORP.</M>
        <M name="Confidence">Margin over the runner-up relative to the simulation standard error: High if the margin is at least 6 and more than 2 standard errors; Medium if at least 2.5 and more than 1; otherwise Low.</M>
        <M name="Drop-off">Best available projection at a position now minus the expected best available at your next pick, from the simulations.</M>
        <M name="Likely there at #N">Players with the highest value × probability of still being available at your next pick (only those above 25%).</M>
      </S>

      <S title="Week">
        <M name="Win probability">20,000 simulated games: each starter&apos;s weekly points drawn from a truncated normal (mean, sd above), summed, compared with the opponent&apos;s projected lineup (their recorded roster&apos;s mean-optimal lineup). Shown for your current recorded lineup and for the optimized one.</M>
        <M name="Optimized lineup">Candidates are the mean-optimal lineup plus every single-player swap with a bench alternate; the one with the highest win probability wins. That automatically prefers high-variance players when you are the underdog and high-floor players when you are favored.</M>
        <M name="Recommendation cards">Lineup change (Δ win probability in percentage points), K/DEF stream when the best free agent beats your best by at least 1.5 projected points, IR move for any IR-eligible player not parked, and bye-week starters. Buttons only record what you then do in Yahoo.</M>
        <M name="Streaming rank">Weekly projection for every K or DST, with the Vegas team or opponent implied total (total/2 ± spread/2 from the nflverse schedule file) and availability from the roster store.</M>
        <M name="2025 weekly points chart">Last season&apos;s weekly results re-scored with this league&apos;s rules (nflverse stats). The dashed line is the 2026 projected points per game.</M>
      </S>

      <S title="Language model">
        <M name="What it does">Rewrites the one-sentence rationale on recommendation cards, writes on-demand explanations (&quot;Explain this pick&quot;, player summaries), and transcribes screenshots of the Yahoo draft board, rosters and transaction pages. Models via OpenRouter (default google/gemini-3.8-flash for text and images; the model in use and the last call status are shown in Settings).</M>
        <M name="Guardrails">Every call receives a complete fact sheet and must answer in a strict JSON schema. Text is rejected if it contains a number not in the fact sheet or a player name not on the allowed list. Screenshot transcriptions are matched to our player pool and shown to you for confirmation before anything is applied. If the model is unavailable or its answer fails the check, the deterministic text is shown instead and the card says so.</M>
      </S>

      <S title="Data sources (all free, verified for 2026)">
        <div>ESPN fantasy projections and ADP · Sleeper season and weekly projections (Rotowire) and ADP · Yahoo public player list (rank, average pick, status, bye) · ESPN injuries feed (status, return date) · nflverse schedule with Vegas lines · nflverse 2025 weekly stats. Refreshed every few hours while the app runs; Settings shows freshness.</div>
      </S>
    </div>
  );
}
