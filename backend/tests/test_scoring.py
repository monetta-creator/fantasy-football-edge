from ffedge.scoring import score, pa_buckets_from_mean, expected_pa_points_per_game


def test_qb_example():
    # 300 pass yds, 2 pass TD, 1 INT = 12 + 12 - 1 = 23.0
    assert score({"pass_yd": 300, "pass_td": 2, "pass_int": 1}) == 23.0


def test_wr_example():
    # 8 rec, 100 yds, 1 TD = 8 + 10 + 6 = 24.0
    assert score({"rec": 8, "rec_yd": 100, "rec_td": 1}) == 24.0


def test_dst_example():
    # 0 points allowed, 3 sacks, 1 INT = 10 + 3 + 2 = 15.0
    assert score({"dst_pa_0": 1, "dst_sack": 3, "dst_int": 1}) == 15.0


def test_rb_full_line():
    # 100 rush yds, 1 rush TD, 5 rec, 40 rec yds, 1 fumble lost = 10+6+5+4-2 = 23
    assert score({"rush_yd": 100, "rush_td": 1, "rec": 5, "rec_yd": 40, "fum_lost": 1}) == 23.0


def test_kicker():
    # 2 FG 30-39 (6), 1 FG 40-49 (4), 1 FG 50+ (5), 3 XP (3) = 18
    assert score({"fg_30_39": 2, "fg_40_49": 1, "fg_50p": 1, "xp_made": 3}) == 18.0


def test_dst_negative_bucket():
    # 35+ allowed (-4), 2 sacks (2), 1 fumble rec (2) = 0
    assert score({"dst_pa_35p": 1, "dst_sack": 2, "dst_fum_rec": 1}) == 0.0


def test_two_point_and_return():
    assert score({"pass_2pt": 1, "rush_2pt": 1, "rec_2pt": 1, "ret_td": 1}) == 12.0


def test_unknown_keys_ignored():
    assert score({"pass_yd": 25, "targets": 99, "adp_ppr": 3}) == 1.0


def test_pa_buckets_sum_to_games():
    b = pa_buckets_from_mean(21.0, 17)
    assert abs(sum(b.values()) - 17) < 1e-6


def test_pa_expected_points_monotone():
    assert expected_pa_points_per_game(10) > expected_pa_points_per_game(20) > expected_pa_points_per_game(30)
