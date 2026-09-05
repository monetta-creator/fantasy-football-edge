from ffedge.weekly import canonical_stats
from ffedge.scoring import score


def test_kicker_50plus_is_remainder():
    st = canonical_stats("K", {"fgm": 1.9, "fgm_20_29": 0.4, "fgm_30_39": 0.5, "fgm_40_49": 0.6, "xpm": 2.0})
    assert abs(st["fg_50p"] - 0.4) < 1e-6
    # 0.4*3 + 0.5*3 + 0.6*4 + 0.4*5 + 2 = 9.1
    assert abs(score(st) - 9.1) < 1e-6


def test_dst_canonical():
    st = canonical_stats("DEF", {"sack": 3, "int": 1, "fum_rec": 1, "def_td": 0.5, "safe": 0, "blk_kick": 0, "st_td": 0.1, "def_kr_td": 0.05, "def_pr_td": 0.05})
    assert st["dst_sack"] == 3 and st["dst_int"] == 1 and st["dst_td"] == 0.5 and abs(st["dst_ret_td"] - 0.1) < 1e-9


def test_offense_passthrough():
    st = canonical_stats("QB", {"pass_yd": 250, "pass_td": 2, "pass_int": 1, "rush_yd": 20, "fum_lost": 0.1, "pr_td": 0})
    assert score(st) == 10 + 12 - 1 + 2 - 0.2
