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
  rationale: string; rationale_llm?: string; scarcity: Scarcity[]; n_sims: number; computed_ms: number;
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
  llm: { enabled: boolean; model: string | null }; sim_count: number; ir_plus: boolean; error: string | null;
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
