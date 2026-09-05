"""Correlated game-level Monte Carlo.

Each NFL game's score is sampled from its Vegas line (margin and total ~ Normal with NFL-typical sd),
then every player's weekly points scale with his team's simulated scoring, plus individual noise.
Teammates rise and fall together, a DST moves against the opposing offense, and lineups with stacks
get honest floors and ceilings.
"""
from __future__ import annotations

import numpy as np

from . import config
from .weekly import WeekRow

MARGIN_SD = 13.5
TOTAL_SD = 13.5
ALPHA = {"QB": 0.75, "WR": 0.75, "TE": 0.7, "RB": 0.55, "K": 0.8}
RESID = {"QB": 0.72, "WR": 0.78, "TE": 0.8, "RB": 0.8, "K": 0.7, "DEF": 0.65}
PA_POINTS = [(0.5, 10.0), (6.5, 7.0), (13.5, 4.0), (20.5, 1.0), (27.5, 0.0), (34.5, -1.0), (1e9, -4.0)]


def pa_bucket_points(pts: np.ndarray) -> np.ndarray:
    out = np.full(pts.shape, -4.0)
    for hi, val in reversed(PA_POINTS):
        out = np.where(pts < hi, val, out)
    return out


class GameSim:
    def __init__(self, rows: dict[str, WeekRow], lines: dict[str, dict], n: int = 20000, seed: int = 3):
        self.rows = rows
        self.lines = lines
        self.n = n
        self.rng = np.random.default_rng(seed)
        self.team_pts: dict[str, np.ndarray] = {}
        self._simulate_games()
        self._cache: dict[str, np.ndarray] = {}

    def _simulate_games(self):
        done = set()
        for team, v in self.lines.items():
            if team in done or not v.get("opp"):
                continue
            opp = v["opp"]
            home, away = (team, opp) if v.get("home") else (opp, team)
            hv = self.lines.get(home, v)
            total = float(hv.get("total") or 45.0)
            spread = float(hv.get("spread") or 0.0)  # positive = home favored
            tot = self.rng.normal(total, TOTAL_SD, self.n)
            mar = self.rng.normal(spread, MARGIN_SD, self.n)
            hp = np.clip((tot + mar) / 2, 0, None)
            ap = np.clip((tot - mar) / 2, 0, None)
            self.team_pts[home] = hp
            self.team_pts[away] = ap
            done.update([home, away])

    def factor(self, team: str, alpha: float) -> np.ndarray:
        pts = self.team_pts.get(team)
        v = self.lines.get(team) or {}
        implied = float(v.get("implied") or 0)
        if pts is None or implied <= 0:
            return np.ones(self.n)
        return np.clip(pts / implied, 0.3, 2.5) ** alpha

    def draw(self, pid: str) -> np.ndarray:
        if pid in self._cache:
            return self._cache[pid]
        r = self.rows.get(pid)
        if r is None or r.on_bye or r.mean <= 0 or not r.team:
            out = np.zeros(self.n)
        elif r.pos == "DEF":
            opp = (self.lines.get(r.team) or {}).get("opp")
            opp_pts = self.team_pts.get(opp) if opp else None
            st = r.stats or {}
            exp_pa = sum(float(st.get(k, 0) or 0) * val for k, val in zip(("dst_pa_0", "dst_pa_1_6", "dst_pa_7_13", "dst_pa_14_20", "dst_pa_21_27", "dst_pa_28_34", "dst_pa_35p"), (10, 7, 4, 1, 0, -1, -4)))
            other = max(0.0, r.mean - exp_pa)
            if opp_pts is None:
                out = np.full(self.n, r.mean) + self.rng.normal(0, r.sd * RESID["DEF"], self.n)
            else:
                f_def = self.factor(opp, 0.3)
                out = pa_bucket_points(opp_pts) + other / f_def + self.rng.normal(0, r.sd * RESID["DEF"] * 0.8, self.n)
        else:
            a = ALPHA.get(r.pos, 0.7)
            out = r.mean * self.factor(r.team, a) + self.rng.normal(0, r.sd * RESID.get(r.pos, 0.75), self.n)
        out = np.clip(out, -3.0, None)
        self._cache[pid] = out
        return out

    def draws(self, ids: list[str]) -> dict[str, np.ndarray]:
        return {i: self.draw(i) for i in ids}

    def summary(self, pid: str) -> dict:
        d = self.draw(pid)
        return {"mean": float(d.mean()), "sd": float(d.std()), "p10": float(np.percentile(d, 10)), "p90": float(np.percentile(d, 90))}

    def correlation(self, a: str, b: str) -> float:
        x, y = self.draw(a), self.draw(b)
        if x.std() == 0 or y.std() == 0:
            return 0.0
        return float(np.corrcoef(x, y)[0, 1])
