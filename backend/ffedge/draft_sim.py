"""Vectorized Monte Carlo draft simulator.

All simulations run in lockstep as numpy arrays of shape (sims, players). Opponents draft the
available player with the lowest noisy ADP (per-team noise), subject to positional caps. My future
picks follow a need-weighted VORP heuristic. The result is my expected roster value for a forced
current pick, plus what the board looks like at my next picks.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import config
from .vorp import POS_NAMES, Arrays

# Roster caps scale with draft length (15 rounds => deeper benches than the 12-round default).
_DEEP = config.ROUNDS >= 14
OPP_CAPS = np.array([3, 8, 8, 3, 2, 2]) if _DEEP else np.array([2, 7, 7, 2, 1, 1])  # QB RB WR TE K DEF
MY_CAPS = np.array([2, 8, 8, 2, 1, 1]) if _DEEP else np.array([2, 7, 7, 2, 1, 1])
_KD_MIN = max(7, config.ROUNDS - 7)
OPP_MIN_ROUND = np.array([1, 1, 1, 1, _KD_MIN, _KD_MIN])  # opponents don't take K/DEF before this round
NEED = {
    0: [1.0, 0.15, 0.0],
    1: [1.0, 0.8, 0.5, 0.3, 0.18, 0.1, 0.06, 0.03, 0.0],
    2: [1.0, 0.95, 0.75, 0.5, 0.32, 0.18, 0.1, 0.05, 0.0],
    3: [1.0, 0.2, 0.0],
    4: [1.0, 0.0],
    5: [1.0, 0.0],
}
NEED_TABLE = np.zeros((6, 10))
for _p, _row in NEED.items():
    for _c in range(10):
        NEED_TABLE[_p, _c] = _row[min(_c, len(_row) - 1)]

BENCH_WEIGHT = 0.15
BENCH_WEIGHTS = [0.2, 0.15, 0.12, 0.08, 0.05, 0.03, 0.02, 0.01]
SLOT_ELIG = [set(e) for _, e in config.ROSTER_SLOTS]
SLOT_NAMES = [s for s, _ in config.ROSTER_SLOTS]


def lineup_value(pos_list: list[str], val_list: list[float], ir_list: list[bool] | None = None,
                 bench_weight: float = BENCH_WEIGHT) -> tuple[float, list[dict]]:
    """Greedy optimal lineup (nested eligibility) on non-negative values. Returns (score, assignments)."""
    n = len(pos_list)
    order = sorted(range(n), key=lambda i: -val_list[i])
    caps = [1] * len(SLOT_ELIG)
    slot_order = list(range(len(SLOT_ELIG)))
    assign = []
    score = 0.0
    bench = 0
    for i in order:
        p = pos_list[i]
        v = max(0.0, val_list[i])
        placed = None
        for s in slot_order:
            if caps[s] and p in SLOT_ELIG[s]:
                caps[s] = 0
                placed = SLOT_NAMES[s]
                break
        if placed:
            score += v
            assign.append({"i": i, "slot": placed})
        elif ir_list is not None and ir_list[i]:
            score += v  # IR-eligible: counted via stash value, no bench slot used
            assign.append({"i": i, "slot": "IR"})
        else:
            bench += 1
            if bench <= config.BENCH_SLOTS:
                w = BENCH_WEIGHTS[bench - 1] if bench_weight == BENCH_WEIGHT else bench_weight
                score += w * v
                assign.append({"i": i, "slot": "BN"})
            else:
                assign.append({"i": i, "slot": "X"})
    return score, assign


@dataclass
class SimResult:
    roster_score_mean: float
    roster_score_std: float
    avail_at_next: np.ndarray | None  # (players,) probability available at my next pick
    best_pos_at_next: dict  # pos -> mean best available pts at my next pick
    best_pos_at_next2: dict
    my_rosters: np.ndarray  # (sims, my_picks) player indices
    n_sims: int


class DraftSim:
    def __init__(self, arr: Arrays, teams: int = config.NUM_TEAMS, rounds: int = config.ROUNDS, my_slot: int = config.MY_SLOT):
        self.a = arr
        self.T = teams
        self.R = rounds
        self.me = my_slot
        self.total = teams * rounds
        self.my_picks = config.my_picks(my_slot, teams, rounds)
        self.P = len(arr.ids)

    def run(self, picks_made: list[dict], forced: dict[int, int] | None = None, n_sims: int = 200, seed: int = 7,
            record_next_for: int | None = None) -> SimResult:
        a = self.a
        S, P, T = n_sims, self.P, self.T
        rng = np.random.default_rng(seed)
        forced = forced or {}
        avail = np.ones((S, P), dtype=bool)
        counts = np.zeros((S, T + 1, 6), dtype=int)  # team index 1..T
        made = {int(p["pick_no"]): p for p in picks_made}
        for pk, p in made.items():
            i = a.index.get(p["player_id"])
            if i is None:
                continue
            avail[:, i] = False
            counts[:, int(p["team"]), a.pos_idx[i]] += 1
        # per-team noisy ADP, one draw per sim/team/player
        noise = rng.standard_normal((S, T + 1, P))
        V = a.adp[None, None, :] + a.sigma[None, None, :] * noise
        picked = np.full((S, self.total + 1), -1, dtype=int)
        start = max(made.keys(), default=0) + 1
        # decision pick = the pick we are evaluating (forced) or my first pick from `start`
        if forced:
            decision_pick = min(forced.keys())
        else:
            later_mine = [k for k in self.my_picks if k >= start]
            decision_pick = later_mine[0] if later_mine else None
        next_pick = None
        next_pick2 = None
        if decision_pick is not None:
            after = [k for k in self.my_picks if k > decision_pick]
            next_pick = after[0] if after else None
            next_pick2 = after[1] if len(after) > 1 else None
        if record_next_for is not None:
            next_pick = record_next_for
        avail_at_next = None
        best_next = None
        best_next2 = None
        rows = np.arange(S)
        pos_of = a.pos_idx
        vorp_pos = np.maximum(a.myval, 0.0)
        pts = a.pts
        for k in range(start, self.total + 1):
            if k == next_pick:
                avail_at_next = avail.copy()
                best_next = self._best_by_pos(avail)
            if k == next_pick2:
                best_next2 = self._best_by_pos(avail)
            t = config.team_on_clock(k, T)
            rnd = config.round_of(k, T)
            if t == self.me:
                if k in forced:
                    i = forced[k]
                    choice = np.full(S, i, dtype=int)
                    # if not available in some sims (shouldn't happen for current pick), fall back to heuristic
                    bad = ~avail[rows, choice]
                    if bad.any():
                        alt = self._my_choice(avail, counts[:, t, :], rnd, vorp_pos, pts, pos_of)
                        choice = np.where(bad, alt, choice)
                else:
                    choice = self._my_choice(avail, counts[:, t, :], rnd, vorp_pos, pts, pos_of)
            else:
                cand = V[:, t, :].copy()
                cand[~avail] = np.inf
                over = counts[:, t, :] >= OPP_CAPS[None, :]  # (S,6)
                cand[over[:, pos_of]] = np.inf
                if rnd < _KD_MIN:
                    early_block = (OPP_MIN_ROUND[pos_of] > rnd)
                    cand[:, early_block] = np.inf
                choice = np.argmin(cand, axis=1)
            picked[:, k] = choice
            avail[rows, choice] = False
            np.add.at(counts, (rows, np.full(S, t), pos_of[choice]), 1)
        self.last_picked = picked
        # my rosters
        my_idx = [k for k in self.my_picks]
        my_rosters = np.stack([np.array([made[k]["player_id"] and a.index.get(made[k]["player_id"], -1) if k in made else -1 for k in my_idx])] * 1)
        my_rosters = np.repeat(my_rosters, S, axis=0)
        for j, k in enumerate(my_idx):
            if k >= start:
                my_rosters[:, j] = picked[:, k]
        scores = np.zeros(S)
        for s in range(S):
            idxs = [i for i in my_rosters[s] if i >= 0]
            sc, _ = lineup_value([POS_NAMES[pos_of[i]] for i in idxs], [float(a.myval[i]) for i in idxs], [bool(a.ir_eligible[i]) for i in idxs])
            scores[s] = sc
        return SimResult(
            roster_score_mean=float(scores.mean()), roster_score_std=float(scores.std(ddof=1) if S > 1 else 0.0),
            avail_at_next=(avail_at_next.mean(axis=0) if avail_at_next is not None else None),
            best_pos_at_next=best_next or {}, best_pos_at_next2=best_next2 or {}, my_rosters=my_rosters, n_sims=S,
        )

    def _best_by_pos(self, avail: np.ndarray) -> dict:
        out = {}
        for p, pi in enumerate(POS_NAMES):
            m = avail & (self.a.pos_idx[None, :] == p)
            v = np.where(m, self.a.pts[None, :], -np.inf).max(axis=1)
            vv = np.where(m, self.a.vorp[None, :], -np.inf).max(axis=1)
            out[pi] = {"pts": float(np.mean(v[np.isfinite(v)])) if np.isfinite(v).any() else 0.0,
                       "vorp": float(np.mean(vv[np.isfinite(vv)])) if np.isfinite(vv).any() else 0.0}
        return out

    def _my_choice(self, avail, my_counts, rnd, vorp_pos, pts, pos_of):
        need = NEED_TABLE[pos_of[None, :], np.minimum(my_counts[:, pos_of], 9)]  # (S,P)
        score = vorp_pos[None, :] * need + 1e-3 * pts[None, :]
        score = np.where(avail, score, -np.inf)
        over = my_counts >= MY_CAPS[None, :]
        score[over[:, pos_of]] = -np.inf
        if rnd < self.R - 3:
            # no K/DEF before the last four rounds in my own heuristic
            score[:, (pos_of == 4) | (pos_of == 5)] = -np.inf
        choice = np.argmax(score, axis=1)
        if rnd >= self.R - 3:
            # fill empty required starter slots late: QB/TE from round R-3, DEF/K in the last two rounds
            order = [0, 3] if rnd < self.R - 1 else [0, 3, 5, 4]
            done = np.zeros(avail.shape[0], dtype=bool)
            for pi in order:
                missing = (my_counts[:, pi] == 0) & ~done
                if not missing.any():
                    continue
                m = avail & (pos_of[None, :] == pi)
                forced = np.where(m, pts[None, :], -np.inf)
                alt = np.argmax(forced, axis=1)
                has = np.isfinite(forced.max(axis=1))
                sel = missing & has
                choice = np.where(sel, alt, choice)
                done |= sel
        return choice
