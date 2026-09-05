export type Injury = { code?: string | null; label?: string | null; type?: string | null; return_week?: number | null; ir_eligible?: boolean; flag?: boolean };
export type Brief = { id: string; name: string; pos: string; team: string | null; pts?: number; vorp?: number; adp?: number; bye?: number | null; injury?: Injury };
export type PlayerRow = Brief & {
  ppg: number; vols: number; adp_sigma: number; yahoo_rank: number | null; games: number; stash_value: number; proj_spread: number;
  p_gone_by_decision: number; p_gone_by_next: number | null; drafted: { pick_no: number; team: number } | null; injury: Injury;
};
export type Candidate = Brief & {
  rank: number; ppg: number; vols: number; yahoo_rank: number | null; roster_score: number; roster_score_se: number; delta_vs_best: number;
  p_gone_by_next: number | null; next_pick: number | null; p_available_at_decision: number; injury: Injury; proj_spread: number; mechanism: string; stash_value: number;
};
export type Scarcity = { pos: string; best_now: { id: string; name: string; pts: number; vorp: number }; expected_best_at_next: number | null; expected_best_at_next2: number | null; dropoff_to_next: number | null; next_pick: number | null; next_pick2: number | null; replacement_pts: number };
export type Recommend = {
  done: boolean; pick_no: number; decision_pick: number; is_me: boolean; next_pick: number | null; next_pick2: number | null; round: number;
  recommended: Candidate; alternatives: Candidate[]; all_candidates: Candidate[]; confidence: "High" | "Medium" | "Low"; margin: number;
  rationale: string; rationale_llm?: string; llm?: { status: string; model?: string | null; ms?: number | null; detail?: string | null }; scarcity: Scarcity[]; n_sims: number; computed_ms: number;
  likely_available_next: (Brief & { p_available: number })[];
};
export type Slot = { slot: string; elig: string[]; player: Brief | null };
export type Board = {
  pick_no: number | null; round: number | null; total_picks: number; on_clock_team: number | null; on_clock_name: string | null; is_me: boolean;
  my_next_picks: number[]; picks_until_me: number | null; picks: { pick_no: number; player_id: string; team: number; player: Brief; team_name: string }[];
  my_roster: { slots: Slot[]; ir: Brief[]; needs: string[]; score: number; count: number; starter_pts: number }; teams: Record<string, string>; drafted_count: number;
  team_rosters: { slot: number; name: string; players: Brief[]; counts: Record<string, number> }[];
};
export type Meta = {
  season: number; league_id: number; teams: number; my_slot: number; rounds: number; my_picks: number[]; sources: Record<string, unknown> & { counts?: Record<string, number>; built_at?: string };
  replacement: { replacement_pts: Record<string, number>; replacement_rank: Record<string, number>; allocation: { starters: Record<string, number>; flex: Record<string, Record<string, number>> } };
  llm: { enabled: boolean; model: string | null; vision_model?: string | null; last?: { status: string; model?: string | null; ms?: number | null; detail?: string | null } }; sim_count: number; ir_plus: boolean; error: string | null; odds_configured?: boolean;
};
export type StashRow = Brief & { ppg: number; stash_value: number; status: string | null; label: string | null; type: string | null; return_week: number | null; return_date: string | null; ir_eligible: boolean; comment: string | null; drafted: boolean };
export type PickAnalysis = { pick_no: number; next_picks: number[]; n_sims: number; candidates: (Brief & { p_available: number; roster_score: number; se: number; delta: number; board_at_next: (Brief & { p_available: number })[]; best_pos_at_next: Record<string, number>; best_pos_at_next2: Record<string, number>; injury: Injury })[] };

async function j<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { cache: "no-store", ...init });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export const api = {
  meta: () => j<Meta>("/api/meta"),
  board: () => j<Board>("/api/board"),
  recommend: () => j<Recommend>("/api/recommend"),
  players: (q = "", pos = "ALL", sort = "vorp", limit = 250) => j<{ decision_pick: number | null; next_pick: number | null; players: PlayerRow[] }>(`/api/players?q=${encodeURIComponent(q)}&pos=${pos}&sort=${sort}&limit=${limit}`),
  pick: (player_id: string, team?: number) => j<{ pick_no: number }>("/api/pick", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ player_id, team }) }),
  undo: () => j<unknown>("/api/undo", { method: "POST" }),
  reset: () => j<unknown>("/api/reset", { method: "POST" }),
  teams: (names: Record<number, string>) => j<Record<string, string>>("/api/teams", { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify({ names }) }),
  pickAnalysis: () => j<PickAnalysis>("/api/pick-analysis"),
  irStash: () => j<{ rows: StashRow[]; ir_plus: boolean }>("/api/ir-stash"),
  refresh: () => j<{ ok: boolean; error: string | null }>("/api/refresh", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ force: true }) }),
};

export const fmt = (n: number | null | undefined, d = 0) => (n == null ? "–" : n.toFixed(d));
export const pct = (p: number | null | undefined) => (p == null ? "–" : `${Math.round(p * 100)}%`);

// ---- Phase 1 types ----
export type WeekPlayer = Brief & { slot: string | null; mean: number; sd: number; on_bye: boolean; opp: string | null; floor?: number; ceiling?: number; season_pts: number; stash_value: number; note?: string; vegas?: { implied?: number; opp_implied?: number; spread?: number } };
export type Eval = { win_prob: number; mean: number; sd: number; p10: number; p90: number; opp_mean: number; opp_sd: number };
export type Rec = { kind: string; headline: string; number: number; unit: string; secondary: string; confidence: "High" | "Medium" | "Low"; rationale: string; action: string; player_id?: string };
export type StreamRow = { id: string; name: string; team: string | null; opp: string | null; mean: number; floor: number; ceiling: number; owner: number | null; mine: boolean; available: boolean; mechanism: string; opp_implied?: number; implied?: number; gameday?: string };
export type Week = {
  week: number; empty: boolean; message?: string; my_team?: string;
  opponent: { slot: number | null; name: string | null; lineup?: WeekPlayer[]; eval?: { mean: number; sd: number } };
  current?: { lineup: WeekPlayer[]; eval: Eval };
  optimized?: { lineup: Record<string, WeekPlayer>; eval: Eval; posture: string; n_candidates: number; mean_eval: Eval };
  roster?: WeekPlayer[]; recommendations?: Rec[]; streaming: { K: StreamRow[]; DEF: StreamRow[] }; market?: import("@/components/MarketCheck").Market;
};
export type PageRow = { text: string; position: string | null; nfl_team: string | null; status_code: string | null; fantasy_team: string | null; team: number | null; slot: string | null; action: string | null; date: string | null; status: "ok" | "ambiguous" | "unknown"; confidence: number; player_id: string | null; player_name: string | null; candidates: { id: string; name: string; pos: string; team: string | null; confidence: number }[] };

export const api1 = {
  week: () => j<Week>("/api/week"),
  rosters: () => j<{ week: number; teams: { slot: number; name: string; players: WeekPlayer[] }[] }>("/api/rosters"),
  seed: (replace = false) => j<{ rows: number }>("/api/rosters/seed-from-draft", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ replace }) }),
  move: (player_id: string, slot: string, team?: number) => j<unknown>("/api/roster/move", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ player_id, slot, team }) }),
  add: (player_id: string, drop_player_id?: string, team?: number) => j<unknown>("/api/roster/add", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ player_id, drop_player_id, team }) }),
  drop: (player_id: string, team?: number) => j<unknown>("/api/roster/drop", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ player_id, team }) }),
  applyOptimized: () => j<{ win_prob: number }>("/api/roster/apply-optimized", { method: "POST" }),
  freeAgents: (pos = "ALL", sort = "week") => j<{ week: number; players: WeekPlayer[]; rostered: number }>(`/api/free-agents?pos=${pos}&sort=${sort}`),
  importPage: (image: string) => j<{ page_type: string; fantasy_team: string | null; rows: PageRow[]; model: string }>("/api/import-page", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ image }) }),
  applyPage: (team: number, mode: string, rows: PageRow[]) => j<{ applied: number }>("/api/import-page/apply", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ team, mode, rows }) }),
  yahooStatus: () => j<{ configured: boolean; connected: boolean }>("/api/yahoo/status"),
  yahooAuthUrl: () => j<{ url: string }>("/api/yahoo/auth-url"),
  yahooCallback: (code: string) => j<{ connected: boolean }>("/api/yahoo/callback", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ code }) }),
  yahooSync: () => j<{ applied: { team: number; players: number }[] }>("/api/yahoo/sync", { method: "POST" }),
};
