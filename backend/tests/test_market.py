import numpy as np

from ffedge.gamesim import GameSim, pa_bucket_points
from ffedge.kalshi import ladder_stats
from ffedge.market import consistency, apply_vegas_scaling
from ffedge.odds import _implied, _ppf, market_points
from ffedge.weekly import WeekRow


def _row(pid, pos, team, opp, mean, sd, stats=None):
    return WeekRow(pid, pid, pos, team, opp, mean, sd, False, stats or {}, {"opp": opp, "implied": 24.0, "total": 48.0, "spread": 0.0, "home": True}, "")


def test_pa_buckets():
    assert list(pa_bucket_points(np.array([0, 3, 10, 17, 24, 30, 40]))) == [10, 7, 4, 1, 0, -1, -4]


def test_gamesim_correlations_and_means():
    lines = {"KC": {"opp": "DEN", "home": True, "spread": 7.0, "total": 48.0, "implied": 27.5}, "DEN": {"opp": "KC", "home": False, "spread": -7.0, "total": 48.0, "implied": 20.5}}
    rows = {
        "QB:kc": _row("QB:kc", "QB", "KC", "DEN", 22.0, 8.0), "WR:kc": _row("WR:kc", "WR", "KC", "DEN", 16.0, 8.0),
        "RB:den": _row("RB:den", "RB", "DEN", "KC", 14.0, 7.0), "DEF:DEN": _row("DEF:DEN", "DEF", "DEN", "KC", 7.0, 5.0, {"dst_pa_14_20": 0.4, "dst_pa_21_27": 0.4, "dst_pa_28_34": 0.2, "dst_sack": 2.5}),
    }
    sim = GameSim(rows, lines, n=20000, seed=1)
    assert sim.correlation("QB:kc", "WR:kc") > 0.2          # teammates move together
    assert sim.correlation("QB:kc", "DEF:DEN") < -0.1       # opposing defense moves against the offense
    assert abs(sim.summary("QB:kc")["mean"] - 22.0) < 1.5   # means roughly preserved
    assert sim.draw("QB:kc").min() >= -3.0


def test_consistency_and_scaling():
    lines = {"KC": {"opp": "DEN", "home": True, "implied": 30.0}, "DEN": {"opp": "KC", "home": False, "implied": 10.0}}
    rows = {
        "QB:kc": _row("QB:kc", "QB", "KC", "DEN", 20, 8, {"pass_td": 1.5, "rush_td": 0.2}), "WR:kc": _row("WR:kc", "WR", "KC", "DEN", 15, 8, {"rush_td": 0.0}),
        "RB:kc": _row("RB:kc", "RB", "KC", "DEN", 14, 7, {"rush_td": 0.6}), "K:kc": _row("K:kc", "K", "KC", "DEN", 9, 3, {"fg_0_39": 1.0, "fg_40_49": 0.5, "xp_made": 2.5}),
        "QB:den": _row("QB:den", "QB", "DEN", "KC", 18, 8, {"pass_td": 1.6}), "WR:den": _row("WR:den", "WR", "DEN", "KC", 12, 7, {}), "RB:den": _row("RB:den", "RB", "DEN", "KC", 11, 6, {"rush_td": 0.7}),
    }
    table = {t["team"]: t for t in consistency(rows, lines)}
    assert table["KC"]["proj_points"] == round(6 * (1.5 + 0.2 + 0.6) + 3 * 1.5 + 2.5, 1)
    assert table["DEN"]["flag"] == "high" and table["DEN"]["factor"] < 1.0   # we project 13.8, Vegas says 10 -> scale down
    assert table["KC"]["flag"] == "low" and table["KC"]["factor"] > 1.0      # we project 20.8, Vegas says 30 -> scale up
    before_den, before_kc = rows["QB:den"].mean, rows["WR:kc"].mean
    apply_vegas_scaling(rows, lines)
    assert rows["QB:den"].mean < before_den and rows["WR:kc"].mean > before_kc and rows["K:kc"].mean == 9  # K untouched by this step


def test_odds_helpers():
    assert abs(_implied(-110) - 0.5238) < 1e-3 and abs(_implied(150) - 0.4) < 1e-6
    assert abs(_ppf(0.5)) < 1e-6 and _ppf(0.6) > 0 > _ppf(0.4)
    mp = market_points("WR", {"player_receptions": {"mean": 6.0}, "player_reception_yds": {"mean": 80.0}, "player_anytime_td": {"exp_td": 0.5}})
    assert abs(mp["points"] - (6 + 8 + 3)) < 1e-6 and "rec_td" in mp["covered"]


def test_kalshi_ladder():
    st = ladder_stats([(40.5, 0.9), (43.5, 0.7), (46.5, 0.45), (49.5, 0.25), (52.5, 0.1)])
    assert 45 < st["median"] < 47 and 45 < st["mean"] < 48
    assert ladder_stats([(1, None)]) is None
