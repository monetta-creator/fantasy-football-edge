import numpy as np

from ffedge import config
from ffedge.draft_sim import BENCH_WEIGHTS, DraftSim, lineup_value
from ffedge.vorp import Arrays, POS_INDEX


def _arrays():
    ids, names, pos, pts, adp = [], [], [], [], []
    k = 0
    for p, n, top, decay in [("QB", 45, 400, 6), ("RB", 80, 330, 4), ("WR", 90, 320, 3), ("TE", 35, 240, 5), ("K", 30, 170, 2), ("DEF", 30, 140, 2)]:
        for i in range(n):
            ids.append(f"{p}:{i}"); names.append(f"{p}{i}"); pos.append(p); pts.append(top - decay * i)
            k += 1
    pts = np.array(pts, dtype=float)
    pos_idx = np.array([POS_INDEX[p] for p in pos])
    # market ADP: by points but K/DEF pushed late
    order_pts = pts.copy()
    order_pts[(pos_idx == 4) | (pos_idx == 5)] -= 200
    adp = np.argsort(np.argsort(-order_pts)).astype(float) + 1
    sigma = 1 + 0.16 * adp
    repl = {"QB": 300, "RB": 150, "WR": 170, "TE": 150, "K": 160, "DEF": 130}
    vorp = pts - np.array([repl[p] for p in pos])
    n = len(ids)
    return Arrays(ids=ids, names=names, pos=pos, pos_idx=pos_idx, pts=pts, ppg=pts / 17, games=np.full(n, 17.0), adp=adp, sigma=sigma,
                  vorp=vorp, vols=vorp, ir_eligible=np.zeros(n, dtype=bool), stash=np.zeros(n), myval=vorp, index={i: j for j, i in enumerate(ids)})


def test_sim_respects_forced_pick_and_no_duplicates():
    a = _arrays()
    sim = DraftSim(a)
    forced = a.index["WR:0"]
    mine = config.my_picks()[0]
    r = sim.run([], forced={mine: forced}, n_sims=20, seed=1)
    picked = sim.last_picked[:, 1:]
    for s in range(20):
        row = picked[s]
        assert len(set(row.tolist())) == len(row)  # no duplicates
        assert row[mine - 1] == forced  # my first pick forced
    assert r.my_rosters.shape == (20, config.ROUNDS)


def test_my_roster_has_k_and_def_and_starters():
    a = _arrays()
    sim = DraftSim(a)
    r = sim.run([], forced={config.my_picks()[0]: a.index["RB:0"]}, n_sims=10, seed=2)
    for s in range(10):
        ps = [a.pos[i] for i in r.my_rosters[s]]
        assert "K" in ps and "DEF" in ps and "QB" in ps and "TE" in ps
        assert ps.count("QB") <= 2


def test_avail_at_next_reasonable():
    a = _arrays()
    sim = DraftSim(a)
    r = sim.run([], forced={config.my_picks()[0]: a.index["RB:0"]}, n_sims=50, seed=3)
    av = r.avail_at_next
    top = np.argsort(a.adp)[:10]
    assert av[top].mean() < 0.2  # top-10 ADP mostly gone by my second pick
    late = np.argsort(a.adp)[150:170]
    assert av[late].mean() > 0.8


def test_lineup_value_greedy_slots():
    pos = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "K", "DEF", "WR", "RB"]
    val = [50, 40, 30, 45, 35, 25, 20, 5, 3, 10, 8]
    score, assign = lineup_value(pos, val)
    slots = {a["slot"] for a in assign}
    assert {"QB", "RB", "WR", "TE", "K", "DEF", "W/R", "W/R/T"} <= slots
    # 9 starters: QB50 RB40 WR45 WR35 TE20 K5 DEF3 + flex RB30 + flex WR25 = 253, bench 10 and 8 at depth weights
    assert abs(score - (253 + BENCH_WEIGHTS[0] * 10 + BENCH_WEIGHTS[1] * 8)) < 1e-6
