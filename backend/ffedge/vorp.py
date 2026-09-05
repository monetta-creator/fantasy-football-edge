"""Value over replacement for this roster shape and scoring.

Two baselines are computed per position:
  * last-starter (VOLS): from a league-wide optimal lineup allocation (empirical flex shares)
  * waiver replacement (VORP): expected points of the best player left undrafted after 144 picks,
    using the ADP availability model. In an unlimited-FA league this is what a roster spot is
    really worth relative to. K/DEF get a streaming uplift on top.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import config
from .adp_model import norm_cdf
from .players import Player

POS_INDEX = {"QB": 0, "RB": 1, "WR": 2, "TE": 3, "K": 4, "DEF": 5}
POS_NAMES = ["QB", "RB", "WR", "TE", "K", "DEF"]
STREAMING_UPLIFT_PPG = {"K": 0.5, "DEF": 1.5}


@dataclass
class Arrays:
    ids: list[str]
    names: list[str]
    pos: list[str]
    pos_idx: np.ndarray
    pts: np.ndarray
    ppg: np.ndarray
    games: np.ndarray
    adp: np.ndarray
    sigma: np.ndarray
    vorp: np.ndarray
    vols: np.ndarray
    ir_eligible: np.ndarray
    stash: np.ndarray
    myval: np.ndarray  # value used for my roster in sims: max(vorp, stash) for IR-eligible
    index: dict[str, int]


def league_allocation(pos_idx: np.ndarray, pts: np.ndarray, teams: int = config.NUM_TEAMS) -> dict:
    """Greedy optimal starter allocation across the league (nested eligibility => greedy is optimal)."""
    caps = {"QB": teams, "RB": teams, "WR": 2 * teams, "TE": teams, "K": teams, "DEF": teams, "W/R": teams, "W/R/T": teams}
    order = np.argsort(-pts)
    starters = {p: 0 for p in POS_NAMES}
    flex_alloc = {"W/R": {"RB": 0, "WR": 0}, "W/R/T": {"RB": 0, "WR": 0, "TE": 0}}
    last_pts = {p: 0.0 for p in POS_NAMES}
    for i in order:
        p = POS_NAMES[pos_idx[i]]
        if caps[p] > 0:
            caps[p] -= 1
        elif p in ("RB", "WR") and caps["W/R"] > 0:
            caps["W/R"] -= 1
            flex_alloc["W/R"][p] += 1
        elif p in ("RB", "WR", "TE") and caps["W/R/T"] > 0:
            caps["W/R/T"] -= 1
            flex_alloc["W/R/T"][p] += 1
        else:
            continue
        starters[p] += 1
        last_pts[p] = float(pts[i])
    return {"starters": starters, "last_starter_pts": last_pts, "flex": flex_alloc}


def waiver_replacement(pos_idx: np.ndarray, pts: np.ndarray, adp: np.ndarray, sigma: np.ndarray,
                       draft_len: int = config.NUM_TEAMS * config.ROUNDS) -> dict:
    """Expected points of the best undrafted player per position, plus the median replacement rank."""
    q_undrafted = 1.0 - norm_cdf((draft_len + 0.5 - adp) / sigma)  # P(pick > draft_len)
    out = {}
    for p, pi in POS_INDEX.items():
        idx = np.where(pos_idx == pi)[0]
        if len(idx) == 0:
            out[p] = {"pts": 0.0, "rank": 0, "expected_drafted": 0.0}
            continue
        idx = idx[np.argsort(-pts[idx])]
        surv = 1.0
        exp_best = 0.0
        cum = 0.0
        rank = None
        for r, i in enumerate(idx, start=1):
            pr = q_undrafted[i] * surv
            exp_best += pts[i] * pr
            cum += pr
            if rank is None and cum >= 0.5:
                rank = r
            surv *= 1.0 - q_undrafted[i]
            if surv < 1e-6:
                break
        exp_best += surv * (pts[idx[-1]] if len(idx) else 0.0)
        out[p] = {
            "pts": float(exp_best), "rank": int(rank or len(idx)),
            "expected_drafted": float(np.sum(1.0 - q_undrafted[idx])),
        }
    return out


def compute(players: list[Player], teams: int = config.NUM_TEAMS) -> tuple[Arrays, dict]:
    n = len(players)
    pos_idx = np.array([POS_INDEX[p.pos] for p in players], dtype=int)
    pts = np.array([p.pts for p in players], dtype=float)
    ppg = np.array([p.ppg for p in players], dtype=float)
    games = np.array([p.games for p in players], dtype=float)
    adp = np.array([p.adp for p in players], dtype=float)
    sigma = np.array([p.adp_sigma for p in players], dtype=float)

    alloc = league_allocation(pos_idx, pts, teams)
    waiver = waiver_replacement(pos_idx, pts, adp, sigma)
    repl_pts = {}
    for p in POS_NAMES:
        base = waiver[p]["pts"] + STREAMING_UPLIFT_PPG.get(p, 0.0) * config.FANTASY_REG_WEEKS
        repl_pts[p] = base
    repl_arr = np.array([repl_pts[POS_NAMES[i]] for i in pos_idx])
    vorp = pts - repl_arr
    last_arr = np.array([alloc["last_starter_pts"][POS_NAMES[i]] for i in pos_idx])
    vols = pts - last_arr

    from .ir_stash import stash_value

    ir_el = np.array([bool(p.injury.get("ir_eligible")) for p in players])
    stash = np.zeros(n)
    for i, p in enumerate(players):
        if p.injury.get("flag"):
            stash[i] = stash_value(p, repl_pts[p.pos] / config.DEFAULT_GAMES if hasattr(config, "DEFAULT_GAMES") else repl_pts[p.pos] / 17.0)
    myval = np.where(ir_el, np.maximum(vorp, 0.9 * stash), vorp)

    for i, p in enumerate(players):
        p.__dict__["vorp"] = round(float(vorp[i]), 1)
        p.__dict__["vols"] = round(float(vols[i]), 1)
        p.__dict__["stash_value"] = round(float(stash[i]), 1)
        p.__dict__["repl_pts"] = round(repl_pts[p.pos], 1)

    arrays = Arrays(
        ids=[p.id for p in players], names=[p.name for p in players], pos=[p.pos for p in players],
        pos_idx=pos_idx, pts=pts, ppg=ppg, games=games, adp=adp, sigma=sigma, vorp=vorp, vols=vols,
        ir_eligible=ir_el, stash=stash, myval=myval, index={p.id: i for i, p in enumerate(players)},
    )
    info = {
        "allocation": alloc,
        "waiver": waiver,
        "replacement_pts": {k: round(v, 1) for k, v in repl_pts.items()},
        "replacement_rank": {k: waiver[k]["rank"] for k in POS_NAMES},
        "streaming_uplift_ppg": STREAMING_UPLIFT_PPG,
    }
    return arrays, info
