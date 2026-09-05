from ffedge import config
from ffedge.decide import N_OPTIONS, decide
from ffedge.players import Player


def _player(pid, name, pos, pts, vorp, repl, srcs, injury=None, bye=8):
    p = Player(id=pid, name=name, pos=pos, team="XX", stats={"rec": 100.0}, pts=pts, games=17.0, ppg=round(pts / 17, 2), adp=5.0, adp_sigma=1.8,
               adp_sources={}, proj_sources=srcs, proj_spread=round(max(srcs.values()) - min(srcs.values()), 1), yahoo_rank=4.0, yahoo_id=None,
               espn_id=None, sleeper_id=None, bye=bye, injury=injury or {})
    p.__dict__["vorp"] = vorp
    p.__dict__["repl_pts"] = repl
    return p


def _row(p, rank, roster, delta, gone=1.0, conditional=False, p_av=1.0, n_used=300):
    return {"rank": rank, "id": p.id, "name": p.name, "pos": p.pos, "team": p.team, "pts": p.pts, "vorp": p.vorp, "adp": p.adp, "yahoo_rank": p.yahoo_rank,
            "roster_score": roster, "roster_score_se": 1.0, "delta_vs_best": delta, "p_gone_by_next": gone, "p_available_at_decision": p_av,
            "conditional": conditional, "n_sims_used": n_used, "injury": p.injury, "mechanism": "Full PPR: 100 catches.", "bye": p.bye}


def _setup(conditional):
    q = {"code": "Q", "label": "Questionable", "type": "Groin", "return_date": "2026-09-10", "flag": False, "ir_eligible": False}
    a = _player("WR:a", "Alpha Alpha", "WR", 336.0, 198.0, 138.0, {"espn": 354.0, "sleeper": 312.0}, injury=q, bye=11)
    b = _player("RB:b", "Bravo Bravo", "RB", 349.0, 251.0, 97.0, {"espn": 366.0, "sleeper": 331.0}, bye=6)
    c = _player("WR:c", "Charlie Charlie", "WR", 324.0, 186.0, 138.0, {"espn": 330.0, "sleeper": 318.0})
    d = _player("RB:d", "Delta Delta", "RB", 300.0, 203.0, 97.0, {"espn": 300.0, "sleeper": 300.0})
    players = [a, b, c, d]
    rows = [_row(a, 1, 865.0, 0.0, conditional=conditional, p_av=0.54, n_used=162), _row(b, 2, 863.0, -2.0, conditional=conditional, p_av=0.75, n_used=225),
            _row(c, 3, 862.8, -2.2, gone=0.3, conditional=conditional, p_av=0.9, n_used=270), _row(d, 4, 846.0, -19.0, conditional=conditional, p_av=0.8, n_used=240)]
    rec = {"pick_no": 1 if conditional else 5, "decision_pick": 5, "is_me": not conditional, "next_pick": 20, "round": 1, "all_candidates": rows,
           "margin": 2.0, "confidence": "Low", "n_sims": 300, "lookahead": conditional,
           "unlikely_available": [{"id": "RB:z", "name": "Zulu Zulu", "pos": "RB", "adp": 1.4, "p_available_at_decision": 0.004}] if conditional else [],
           "scarcity": [{"pos": "WR", "expected_best_at_next": 257.0, "dropoff_to_next": 79.0}, {"pos": "RB", "expected_best_at_next": 258.0, "dropoff_to_next": 91.0},
                        {"pos": "QB", "expected_best_at_next": 412.0, "dropoff_to_next": 12.0}, {"pos": "TE", "expected_best_at_next": 245.0, "dropoff_to_next": 2.0}]}
    weeks = [{"week": i + 1, "pts": x} for i, x in enumerate([23.1, 27.6, 22.8, 36.0, 24.5, 4.8, 22.8, 17.4, 14.3, 16.7, 13.2, 35.7, 27.9, 46.5, 15.7, 26.0])]
    hist = {"players": {"WR:a": {"games": 16, "mean": 23.44, "sd": 9.88, "weeks": weeks}}}
    return rec, players, {p.id: p for p in players}, hist


def test_three_options_with_bull_and_bear_on_the_clock():
    rec, players, by_id, hist = _setup(conditional=False)
    d = decide(rec, [], by_id, players, hist)
    assert len(d["options"]) == N_OPTIONS == 3 and not d["lookahead"]
    a, b, c = d["options"]
    for o in (a, b, c):
        assert o["bull"].endswith(".") and o["bear"].endswith(".") and len(o["bull"].split(";")) <= 4
    assert "Questionable (groin), return date 09/10" in a["bear"]
    assert "Sleeper projects only 312" in a["bear"]
    assert "within simulation noise" in a["bear"]  # Low confidence edge
    assert "ESPN projects 354" in a["bull"] and "2025 ceiling: best week 46.5" in a["bull"]
    assert "highest vorp on the board" in b["bull"].lower() and "steepest cliff on the board" in b["bull"]
    assert "trails Alpha by 2.0" in b["bear"]
    assert "you could wait" in c["bear"]  # gone by next only 30%
    # A is compared with B, the others with A
    sim_a = next(r["text"] for r in a["reasons"] if r["kind"] == "simulation")
    sim_c = next(r["text"] for r in c["reasons"] if r["kind"] == "simulation")
    assert "vs Bravo Bravo" in sim_a and "vs Alpha Alpha" in sim_c
    assert not any("On the board at #5" in r["text"] for r in a["reasons"])
    assert [x["name"] for x in d["others"]] == ["Delta Delta"] and d["unlikely_available"] == []


def test_lookahead_marks_conditional_values_and_unlikely_candidates():
    rec, players, by_id, hist = _setup(conditional=True)
    d = decide(rec, [], by_id, players, hist)
    assert d["lookahead"]
    a = d["options"][0]
    avail = [r["text"] for r in a["reasons"] if r["kind"] == "availability"]
    assert any("On the board at #5 in 54%" in t for t in avail)
    sim_a = next(r["text"] for r in a["reasons"] if r["kind"] == "simulation")
    assert "across 162 simulated drafts in which he was still there" in sim_a
    assert d["unlikely_available"][0]["name"] == "Zulu Zulu"
