"""Rescale raw stat projections to this league's exact scoring.

Canonical stat keys (season totals unless noted):
  offense: pass_yd pass_td pass_int pass_2pt rush_yd rush_td rush_2pt rec rec_yd rec_td rec_2pt
           ret_td fum_lost off_fum_ret_td
  kicker:  fg_0_19 fg_20_29 fg_30_39 fg_0_39 fg_40_49 fg_50p xp_made
  dst:     dst_sack dst_int dst_fum_rec dst_td dst_safety dst_blk dst_ret_td dst_xp_ret
           dst_pa_0 dst_pa_1_6 dst_pa_7_13 dst_pa_14_20 dst_pa_21_27 dst_pa_28_34 dst_pa_35p
           (points-allowed keys = number of games in that bucket)
  meta:    games
"""
from __future__ import annotations

from . import config

ALL_SCORING: dict[str, float] = {
    **config.OFFENSE_SCORING,
    **config.KICKER_SCORING,
    **config.DST_SCORING,
    **config.DST_POINTS_ALLOWED,
}


def score(stats: dict[str, float]) -> float:
    """Points for a stat line under league scoring. Unknown keys are ignored."""
    total = 0.0
    for k, v in stats.items():
        w = ALL_SCORING.get(k)
        if w is not None and v:
            total += w * float(v)
    return round(total, 2)


def score_breakdown(stats: dict[str, float]) -> dict[str, float]:
    """Per-stat contribution, for explanations."""
    out = {}
    for k, v in stats.items():
        w = ALL_SCORING.get(k)
        if w is not None and v:
            out[k] = round(w * float(v), 2)
    return out


# --- Points-allowed distribution helper -------------------------------------
# Some sources give only a mean points-allowed per game. Convert a per-game mean
# into expected bucket occupancy using a normal approximation (sd ~ 9.5 points,
# which matches the empirical spread of NFL team points allowed).
PA_BUCKETS = [
    ("dst_pa_0", -1e9, 0.5),
    ("dst_pa_1_6", 0.5, 6.5),
    ("dst_pa_7_13", 6.5, 13.5),
    ("dst_pa_14_20", 13.5, 20.5),
    ("dst_pa_21_27", 20.5, 27.5),
    ("dst_pa_28_34", 27.5, 34.5),
    ("dst_pa_35p", 34.5, 1e9),
]


def pa_buckets_from_mean(mean_pa: float, games: float, sd: float = 9.5) -> dict[str, float]:
    from math import erf, sqrt

    def cdf(x: float) -> float:
        return 0.5 * (1 + erf((x - mean_pa) / (sd * sqrt(2))))

    out = {}
    for key, lo, hi in PA_BUCKETS:
        p = cdf(hi) - cdf(lo)
        out[key] = games * max(p, 0.0)
    return out


def expected_pa_points_per_game(mean_pa: float, sd: float = 9.5) -> float:
    b = pa_buckets_from_mean(mean_pa, 1.0, sd)
    return sum(config.DST_POINTS_ALLOWED[k] * v for k, v in b.items())
