# Edge — fantasy football platform for "Marian Prayers" (Yahoo league 872372)

AI-assisted manager for one 12-team Yahoo league. Phase 0 (this build) is the **draft assistant**: live board, Monte Carlo pick recommendations rescaled to this league's exact scoring, positional scarcity, opponent-ADP availability, and IR-stash ranking. Draft: **Sunday Sept 6, 2026, 6:00 pm EDT, pick 5, 15 rounds**. League facts (slot, roster, team names, schedule) live in `data/league.json`.

## Setup (Mac)

Requirements: Python 3.11+ with [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
cd fantasy-football
cp .env.example .env            # add OPENROUTER_API_KEY (LLM) and ODDS_API_KEY (props); both optional
cd backend && uv venv --python 3.12 .venv && uv pip install -e ".[dev]" && cd ..
cd frontend && npm install && cd ..
./dev.sh                         # or double-click "Launch Edge.command" in Finder
```

Then open `http://localhost:3000/draft` in your browser. The launcher does this for you and installs dependencies on first run. (`dev.sh` also prints a LAN URL if you ever want it on a phone.)

First start pulls projections/ADP/injuries (about 10 s) and caches them in `data/cache/`. The draft board is in `data/ffedge.db`.

Tests: `cd backend && .venv/bin/python -m pytest -q` (scoring rescaler, VORP, ADP model, draft sim, state, LLM grounding).

## Draft-day walkthrough

The Draft screen works as a tool: nothing polls or counts down unless you toggle **Live**. The **Decide** tab is the main flow: mark picks as they happen (Gone → pick the team; Mine for yours), press **Run**, and get two options side by side with a full reason list each, plus an optional AI comparison; press "I took …" on the one you chose. The **Rankings** tab is the cheat sheet (VORP tiers, ADP, gone-by probability); tap **Gone** as players come off the board and **Mine** for your own picks, and the recommendation card recomputes. **About** (last tab) explains every number.

1. **Before the draft**: team names are preloaded from `data/league.json` (you are slot 5, "Show Me Your TDs"); Settings lets you edit them. Tap **Refresh projections** so the data is from the last hour. Open Draft → **Plan** tab to see the pick-5 comparison and what the board looks like at #20 / #29 for each choice.
2. **As picks happen** (you draft in the Yahoo app; this is the monitor): the header shows who is on the clock. Tap the drafted player in the list (search box or position filter), then tap **"[Team] took him"**. The next team is now on the clock. Mistake? **Undo last**.
   Faster: with `OPENROUTER_API_KEY` set, tap **Photo / screenshot** on the Board tab, take a screenshot of the Yahoo board, and confirm the transcribed picks; they are applied in order.
3. **When you are on the clock**: the green card is the answer. Big number = VORP (points over what will be free on waivers). Below it: projected points and the chance he is gone by your next pick. Make the pick in Yahoo, then tap **I took him · record pick** here. The four alternatives show their VORP and "gone by #N" probability. The clock pill counts down 2:00 from each new pick; tap it to restart.
4. **Between your picks** the card shows the *target* for your next pick with its availability probability, so you can pre-decide.
5. **Scarcity** tab: drop-off from the best available now to the expected best at your next pick, per position, plus who is likely to still be there.
6. **Stash** tab: injured players ranked by return-week value. Blue dot = can go straight to an IR slot on Yahoo; amber = must sit on the bench first (Questionable/Out with IR-only slots).
7. Rounds 12–15 the model starts considering K/DEF; it will not recommend them earlier because streaming replaces them for free.

Recommendations recompute in about a second after every pick (300 draft simulations per candidate); the page polls every 2.5 s.

## Weekly loop (Phase 1)

After the draft, open **Roster → Seed from draft** once. Then each week:

1. **Week** tab: win probability for your current lineup vs. this week's opponent (from `data/league.json`), the max-win-probability lineup, and recommendation cards (lineup swaps, K/DEF streams, IR moves, bye warnings). Tap a card to *record* the move here, then make the same move in the Yahoo app. Yahoo's API is read-only, so nothing here changes Yahoo.
2. **Roster** tab: every team's roster, slot changes, drops, IR choreography (bench/IR counts, IR-eligible players not yet parked). Import a roster or transactions screenshot to update any team; the vision model transcribes, names are matched, you confirm.
3. **FA** tab: free agents ranked by this week's projection, season VORP, or IR-stash value; K/DEF streaming uses Vegas implied totals from the schedule file.
4. **Settings**: data freshness, model replacement levels, Yahoo connect (when the application is approved).

Weekly projections: Sleeper weekly raw stats scored with league rules, DST points-allowed blended with the Vegas opponent implied total, per-player variance from 2025 weekly stats. The lineup optimizer simulates 20,000 games per candidate lineup and picks the one with the highest win probability.

## Market check (Week tab)

Three independent views of the same week: our projections scaled to Vegas team totals, sportsbook player props (blended 50/50 when pulled), and Kalshi prediction-market prices. Press **Pull props** once a week after lines post (about 90 API credits of the 500/month free tier); page loads never spend credits. The correlated simulation drives win probability: teammates rise and fall together, a defense moves against the opposing offense. Every block has an ⓘ note and a ✨ button for a grounded AI explanation.

## Player pages

Click any player name. Hero numbers (this week, season projection, VORP), the 2025 weekly points chart re-scored with league rules with a 3-week rolling average and the 2026 per-game line, consistency tiles (startable / boom / bust / median / last 4 / half-season trend), position ranks, 2025 per-game rates, the projection breakdown by stat, every source's number, and an **AI summary** button. Type a name in **Benchmark against another player** to overlay his 2025 line and compare every metric side by side.

## What the model does

- **Scoring**: every projection is stored as raw stats and scored with the league rules in `backend/ffedge/scoring.py` (6-pt pass TD, 25 yds/pt, full PPR, K distance buckets, DST points-allowed buckets).
- **Projections**: ESPN and Sleeper/Rotowire blended per stat (K/DST from ESPN only). Source disagreement is shown per player.
- **ADP**: 0.6 Yahoo average pick + 0.2 Sleeper + 0.2 ESPN, with a pick-variance model that widens for later picks and for source disagreement.
- **Replacement level**: expected best player left undrafted after 180 picks, per position, plus a streaming uplift for K/DEF. VORP = points − replacement. The league-wide lineup allocation (empirical flex shares) is shown in Settings.
- **Recommendation**: for each candidate, simulate the rest of the draft (opponents pick by noisy ADP with roster caps; my later picks follow need-weighted VORP) and score my final roster. Highest expected roster value wins; confidence reflects the margin over the runner-up versus simulation noise.
- **IR stash**: weighted surplus over replacement from expected return week (ESPN injuries feed) through week 17, playoff weeks weighted 1.5×, discounted by designation risk.
- **LLM (optional)**: OpenRouter model (default Gemini 3.8 Flash, ~3 s per call) rewrites the rationale sentence, writes "Explain this pick" and per-player "AI summary" text, and transcribes screenshots, always from a fact sheet under a strict JSON schema; any output with a number or name not in the facts is discarded and the UI says so. Numbers never come from the model.

## Layout

```
backend/ffedge/        FastAPI app (api.py), scoring, players (pool builder), vorp, adp_model, draft_sim, recommend, ir_stash, draft_state, llm
backend/ffedge/sources sleeper, espn, yahoo_public, injuries (ESPN), schedule (nflverse), cache
backend/tests/         pytest suite
frontend/src/app       Next.js screens: draft (live), dashboard/roster/free-agents/trades/playoffs/ideas (Phase 1+ stubs), settings
frontend/src/components RecCard, Alternatives, PlayerList, PickSheet, RosterTray, Scarcity, IRStash, Pick4, BoardStrip, PickClock
data/                  cache/ (source JSON), ffedge.db (draft board)
DECISIONS.md           every modelling and stack decision, with reasons
FEATURE_BACKLOG.md     seeded feature proposals
```

## API (all under `/api`)

Draft: `GET board`, `GET recommend`, `GET players?q=&pos=&sort=`, `GET players/{id}`, `POST pick`, `POST picks/bulk`, `POST undo`, `POST reset`, `PUT teams`, `GET pick-analysis`, `GET ir-stash`, `POST import-screenshot`, `GET meta`, `POST refresh`, `GET log`.

Week: `GET week`, `GET rosters`, `POST rosters/seed-from-draft`, `POST roster/move|add|drop|apply-lineup|apply-optimized`, `GET free-agents?pos=&sort=`, `POST import-page`, `POST import-page/apply`, `GET yahoo/status`, `GET yahoo/auth-url`, `POST yahoo/callback`, `POST yahoo/sync`.

## Next phases

Yahoo's API is read-only and requires an approved application. Phase 1 will support two sync paths: Yahoo OAuth (if approved) and browser/screenshot sync. Execution (adds, drops, lineups, IR moves) is done by you in the Yahoo app. See `claude_code_handoff.md` for the full plan.
