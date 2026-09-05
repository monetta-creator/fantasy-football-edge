# Claude Code Handoff: Fantasy Football Edge Platform

## Mission

Build an AI-powered fantasy football manager for one Yahoo Fantasy league. The goal is to win the league by exploiting rules-specific edges, with a clean Apple-style UI. Draft is **Sunday, September 6, 2026 at 6:00pm EDT**. Build the draft assistant first, everything else after.

I own **pick 4** in a 12-team snake draft. Assume I can connect to any service and spend a small amount of money when needed; default to free tiers.

Work autonomously. Make reasonable decisions, log them in `DECISIONS.md`, and keep going. Ask me only when a choice involves spending money or an irreversible action against the live Yahoo league.

---

## League Facts (from Yahoo Scoring & Settings, verified by me)

**League:** Yahoo Fantasy Football, League ID 872372, "Marian Prayers", 12 teams, head-to-head, live standard draft, 2-minute pick clock, fractional points on, negative points on.

**Roster:** QB, WR, WR, RB, TE, W/R, W/R/T, K, DEF, BN, BN, BN, IR ×6.
Key implications: only one required RB; up to four WR/TE-eligible starters; three bench spots; six IR slots.

**Offense scoring**
- Passing yards: 1 pt per 25 yards
- Passing TD: 6
- Interception thrown: −1
- Rushing yards: 1 pt per 10
- Rushing TD: 6
- Receptions: 1 (full PPR)
- Receiving yards: 1 pt per 10
- Receiving TD: 6
- Return TD: 6
- 2-point conversion: 2
- Fumble lost: −2
- Offensive fumble return TD: 6

**Kickers**
- FG 0–19: 3, 20–29: 3, 30–39: 3, 40–49: 4, 50+: 5
- PAT made: 1

**Defense/Special Teams**
- Sack: 1, Interception: 2, Fumble recovery: 2, TD: 6, Safety: 2, Blocked kick: 2, Kick/punt return TD: 6, Extra point returned: 2
- Points allowed: 0 → 10, 1–6 → 7, 7–13 → 4, 14–20 → 1, 21–27 → 0, 28–34 → −1, 35+ → −4

**Transactions**
- Waiver type: weekly rolling list based on standings (reverse standings priority). Waivers process Tuesday; players go on waivers at game time.
- Waiver time: 2 days. After waivers clear, free agency is first-come, first-served.
- No max acquisitions per week or season. No max trades.
- Trade review: commissioner. Trade reject time: 2 days. Trade deadline: November 28, 2026. No draft-pick trades.
- Injured players from waivers/FA cannot be added directly to IR (must pass through a bench slot).
- Lock benched players: No.

**Playoffs:** 6 teams, Weeks 15–17. No reseeding. No divisions. Tiebreaker: best regular-season record vs. opponent. No median game, no second opponent.

**Draft picks for slot 4, 12 rounds (draftable roster = 9 starters + 3 bench):**
R1 #4, R2 #21, R3 #28, R4 #45, R5 #52, R6 #69, R7 #76, R8 #93, R9 #100, R10 #117, R11 #124, R12 #141.
Note the short turn between #21 and #28 and the long wait between #4 and #21.

---

## The Three Edges the Platform Exists to Exploit

1. **IR hoarding.** Six IR slots + three bench. Draft and claim injured high-upside players, park them, and run a 15-man roster while opponents effectively run 12. The tool must choreograph: keep one bench slot open before Tuesday, claim, move to IR, refill.
2. **Free-agent speed.** Standings-based waivers put a winning team last in priority. The edge is reacting the instant a player clears waivers or is dropped. Unlimited acquisitions means weekly churn costs nothing.
3. **Scoring skew.** 6-pt passing TDs + 25 yds/pt elevate QBs well above 4-pt-league value. Full PPR with four WR/TE-eligible slots and one required RB elevates volume receivers and pass-catching RBs. Kicker scoring rewards long-range legs (50+ = 5). DST scoring is dominated by points allowed, so opponent Vegas implied totals are the primary DST signal.

Every model in this platform must be rescaled to the exact scoring above. Public rankings and ADP are calibrated to different scoring and are only useful as a proxy for what my opponents believe.

---

## Build Order

### Phase 0 — Draft Assistant

Deliver a working web UI I can use on my phone and laptop during the draft.

**Data**
- Pull current 2026 season projections and ADP from a free source (e.g., FantasyPros consensus, Sleeper's public API, or nflverse/nfl_data_py). Verify the source is live for 2026 before relying on it. Cache locally.
- Rescale every projection to this league's scoring. Store raw stat projections, then compute points from them; do not import pre-scored point totals.
- Pull injury status for every draftable player and flag players likely to start the season on IR/PUP (IR-stash candidates).

**Model**
- Value over replacement (VORP) using this roster shape. Replacement levels for 12 teams: QB12, RB ~13–15 (single required slot plus flex share), WR ~40 (two required slots plus heavy flex share), TE12, K12, DST12. Compute the flex allocation empirically by simulating optimal lineups across the projected player pool rather than assuming.
- Positional scarcity curves: show the drop-off between the next available player at each position and the expected best available at my next pick (#21, then #28, etc.).
- Opponent ADP model: estimate who will be gone by my next pick using public ADP with variance.
- Draft-position-aware recommendations for pick 4 specifically: compare the top options at #4 by VORP under this scoring and show what the projected board looks like at #21/#28 for each choice.
- Late-round IR-stash ranking: expected value of an injured player's return weeks (weeks 8–17 matter most; playoff weeks 15–17 matter most of all).

**UI (draft mode)**
- Live board: I mark picks as they happen (tap a player → drafted by team X). Support undo.
- One giant "Recommended pick" card with the number that matters (VORP, projected points) large, plus a one-sentence AI rationale and a confidence indicator.
- Next-best 4 alternatives, each with position, VORP, and "likely gone by #21?" probability.
- My roster tray showing filled/open slots and which positions still need starters.
- A 2-minute pick clock is the constraint; every screen must answer "who do I take" in under 5 seconds of reading.

### Phase 1 — Yahoo Integration + Core Loop

- Yahoo Fantasy Sports API via OAuth2. I will create the developer app and provide client ID/secret; write the auth flow and token refresh. Determine the current NFL game key programmatically; build the league key from it and League ID 872372.
- Sync: my roster, all rosters, free agents, waivers, transactions, matchups, standings, scoring, player status/injuries. Poll on a schedule; store history so we can learn.
- Lineup optimizer with win-probability awareness: Monte Carlo sim over player point distributions (use projection + historical variance). When projected to lose, choose the higher-variance lineup; when favored, choose the higher-floor lineup. Show projected win probability for each candidate lineup.
- Weekly K and DST streaming based on Vegas lines and implied totals (free odds sources; verify availability).

### Phase 2 — Free-Agent Sniper + IR Choreography

- Watch for drops and Tuesday waiver clears. Rank cleared/free players by this league's value model. Present adds with one-tap approval initially; add an "autopilot" toggle per rule (e.g., "auto-add any player above X value if a bench slot is open") once trust is established.
- IR workflow automation: detect IR-eligible players on my roster, propose bench→IR moves, keep one bench slot open before Tuesday processing.
- Injury-stash scanner: injured players on waivers/FA with strong return-week value.

### Phase 3 — Trades + Playoff Planning

- Trade valuator: my rescaled values vs. public consensus values. Surface targets where opponents undervalue QBs and volume receivers, and where they overvalue RBs relative to this scoring.
- Trade proposal generator with a plain-English pitch written in the opponent's frame of reference. Deadline November 28.
- Playoff scheduler: score every player's Weeks 15–17 matchups; bias claims and trades toward soft playoff schedules. Since the tiebreaker is head-to-head record, the sim should weight wins against likely playoff opponents.

### Phase 4 — Feature Recommender

Build a module that recommends new features to me. It should:
- Analyze league data (transaction patterns, opponent tendencies, my win/loss margins, missed points from bench, missed free-agent opportunities) and my usage of the app.
- Propose 1–3 new features per week, each with: the mechanism that produces points, an estimated point impact per season (mark as estimated), effort to build, and a one-line pitch.
- Store proposals in a backlog (`FEATURE_BACKLOG.md` and in-app). I approve or dismiss; approved items become tasks.
- Examples of the kind of thing it should find: "Opponent X drops players Monday night before their game; a Monday-night watcher would have captured 3 pickups so far." "Your bench outscored your starters at flex in 4 of 6 weeks; a flex-specific model tuned to receptions would have added ~N points."

---

## UI Specification

**Aesthetic:** Apple-like. Generous whitespace, system font stack (SF Pro on Apple devices, Inter fallback), white/near-white backgrounds, light gray cards with subtle shadows, rounded corners, minimal chrome, no visual clutter. Dark mode supported.

**Visual cues:** Every actionable state has a color: green (do this / advantage), amber (watch / marginal), red (problem / act now), blue (informational). Use color on a small accent (dot, left border, pill), never on whole backgrounds.

**Standout numbers:** The one number that drives a decision is rendered large (48–64px), bold, with its unit small beneath it. Supporting numbers are small and secondary. Examples: projected points, win probability, VORP, points gained by a proposed move.

**AI recommendation cards:** A distinct card style used everywhere the AI recommends something. Structure: a headline action ("Start Player A over Player B"), the standout number ("+4.2 projected"), a one-sentence rationale, a confidence pill (High/Medium/Low), and a primary action button. Rationale must name the mechanism (e.g., "opponent allows the most receptions to slot WRs"), never generic praise.

**Mobile-first.** I will use this on an iPhone during the draft and on Sundays. Every core action must work with thumbs.

**Screens:** Draft, Dashboard (this week's matchup, lineup, win probability), Roster (with IR choreography), Free Agents (ranked, with sniper status), Trades, Playoff Planner, Feature Ideas, Settings (autopilot rules, API keys).

---

## Tech Stack (default choices; change if there is a clear reason and log it)

- Backend: Python (FastAPI), SQLite for now with a clean path to Postgres.
- Scheduler: APScheduler or cron on a cheap VPS / free-tier cloud. Must run when my laptop is closed.
- Frontend: Next.js + Tailwind, responsive, PWA-installable so it feels like an app on iPhone.
- LLM layer: Anthropic API for rationales, trade pitches, weekly summaries, and feature-recommendation write-ups. Keep the numeric models deterministic; the LLM explains, it does not compute points.
- Data: nfl_data_py / nflverse for stats and schedules; a projection source and an odds source, both free-tier if possible. Verify each source is live for 2026 before wiring it in and record the choice in `DECISIONS.md`.
- Secrets in `.env`, never committed.

---

## Guardrails

- No live roster changes on Yahoo without my explicit tap for the first two weeks. After that, only rules I have enabled in Settings may act automatically.
- Every automated action is logged with the rationale and the model's numbers, so I can audit.
- Respect Yahoo API rate limits; back off on errors.
- Tests for the scoring rescaler (unit tests against hand-computed examples: e.g., a QB with 300 pass yds, 2 pass TD, 1 INT = 12 + 12 − 1 = 23.0; a WR with 8 rec, 100 yds, 1 TD = 8 + 10 + 6 = 24.0; a DST allowing 0 points with 3 sacks and 1 INT = 10 + 3 + 2 = 15.0).

---

## Deliverables and Reporting

1. `README.md` with setup steps I can follow on a Mac.
2. `DECISIONS.md` logging every meaningful choice.
3. `FEATURE_BACKLOG.md` seeded with the feature recommender's first proposals.
4. Working draft assistant with a short walkthrough of how to use it during the live draft.
5. After each phase, a brief summary: what works, what is stubbed, what data sources were verified, what needs my input.

Start with Phase 0 now.
