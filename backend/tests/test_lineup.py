from ffedge import lineup


def _p(i, pos, mean, sd=None):
    return {"id": f"{pos}:{i}", "pos": pos, "name": f"{pos}{i}", "mean": mean, "sd": sd if sd is not None else mean * 0.5}


ROSTER = [_p(1, "QB", 22), _p(2, "QB", 16), _p(1, "RB", 18), _p(2, "RB", 14), _p(3, "RB", 9), _p(1, "WR", 17), _p(2, "WR", 15), _p(3, "WR", 12), _p(4, "WR", 8),
          _p(1, "TE", 11), _p(2, "TE", 6), _p(1, "K", 8), _p(1, "DEF", 7), _p(4, "RB", 5), _p(5, "WR", 4)]


def test_best_by_mean_fills_all_slots_optimally():
    lu = lineup.best_by_mean(ROSTER)
    assert set(lu) == set(lineup.SLOT_KEYS) and len(lu) == 9
    assert {lu["WR1"]["id"], lu["WR2"]["id"]} == {"WR:1", "WR:2"}
    assert lu["QB"]["id"] == "QB:1" and lu["TE"]["id"] == "TE:1"
    starters = {p["id"] for p in lu.values()}
    # flex slots take RB2 (14) and WR3 (12); WR4 (8) and RB3 (9) sit
    assert "RB:2" in starters and "WR:3" in starters and "RB:3" not in starters


def test_win_probability_symmetry_and_variance_preference():
    opp = list(lineup.best_by_mean(ROSTER).values())
    ev = lineup.evaluate(opp, opp)
    assert 0.45 < ev["win_prob"] < 0.55
    # a much stronger opponent -> we should be an underdog, and the optimizer should run without error
    strong = [dict(p, mean=p["mean"] * 1.5) for p in opp]
    res = lineup.optimize(ROSTER, strong)
    assert res["posture"] == "underdog" and res["eval"]["win_prob"] < 0.35
    assert res["n_candidates"] >= 1 and set(res["lineup"]) == set(lineup.SLOT_KEYS)


def test_high_variance_helps_underdog():
    # same mean, different sd: underdog should prefer the high-sd option
    base = [_p(1, "QB", 20, 5), _p(1, "RB", 15, 5), _p(1, "WR", 15, 5), _p(2, "WR", 15, 5), _p(1, "TE", 10, 4), _p(2, "RB", 12, 3), _p(3, "WR", 12, 3), _p(1, "K", 8, 3), _p(1, "DEF", 7, 4)]
    low = dict(_p(9, "WR", 12, 2))
    high = dict(_p(8, "WR", 12, 9))
    opp = [dict(p, mean=p["mean"] * 1.4) for p in base]
    ev_low = lineup.evaluate([p for p in base if p["id"] != "WR:3"] + [low], opp)
    ev_high = lineup.evaluate([p for p in base if p["id"] != "WR:3"] + [high], opp)
    assert ev_high["win_prob"] > ev_low["win_prob"]
