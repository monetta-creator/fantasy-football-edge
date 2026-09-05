import numpy as np

from ffedge.vorp import POS_INDEX, league_allocation, waiver_replacement


def _pool():
    # synthetic: 40 QB, 80 RB, 100 WR, 40 TE, 20 K, 20 DEF with decaying points
    pos, pts = [], []
    for p, n, top, decay in [("QB", 40, 400, 6), ("RB", 80, 330, 4), ("WR", 100, 320, 3), ("TE", 40, 240, 5), ("K", 20, 170, 2), ("DEF", 20, 140, 2)]:
        for i in range(n):
            pos.append(POS_INDEX[p]); pts.append(top - decay * i)
    return np.array(pos), np.array(pts, dtype=float)


def test_allocation_fills_all_starter_slots():
    pos, pts = _pool()
    a = league_allocation(pos, pts, teams=12)
    s = a["starters"]
    assert s["QB"] == 12 and s["TE"] >= 12 and s["K"] == 12 and s["DEF"] == 12
    assert sum(s.values()) == 12 * 9
    assert s["RB"] + s["WR"] + s["TE"] == 12 * 6  # RB, WR, WR, TE, W/R, W/R/T
    assert s["WR"] >= 24 and s["RB"] >= 12


def test_last_starter_decreasing_in_rank():
    pos, pts = _pool()
    a = league_allocation(pos, pts, teams=12)
    # the last WR starter must score no more than the top WR
    assert a["last_starter_pts"]["WR"] <= 320


def test_waiver_replacement_below_top_and_ranked():
    pos, pts = _pool()
    n = len(pts)
    adp = np.argsort(np.argsort(-pts)).astype(float) + 1  # market drafts purely by points
    sigma = np.full(n, 6.0)
    w = waiver_replacement(pos, pts, adp, sigma, draft_len=144)
    for p in ("QB", "RB", "WR", "TE"):
        assert 0 < w[p]["pts"] < pts[pos == POS_INDEX[p]].max()
    # with 144 picks by points, ~18 QBs are gone; replacement rank must be near that
    assert 10 <= w["QB"]["rank"] <= 40
